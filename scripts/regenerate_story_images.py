"""
Regenerate story cover images for all PersonaHistoryStart records.

For each story with an image_prompt, generates 5 new images via RunPod /runsync,
uploads them to Cloudflare, and saves results to story_regen_results.json.

Usage:
    python scripts/regenerate_story_images.py
"""
import asyncio
import base64
import json
import os
import random
import sys
import time

import httpx

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.settings import settings, load_configs, get_app_config
from app.core.cloudflare_upload import upload_to_cloudflare_tg

# Load configs before anything else
load_configs()

IMAGES_PER_STORY = 5
POLL_INTERVAL = 2  # seconds
POLL_TIMEOUT = 120  # seconds


def _get_base_url() -> str:
    """Get RunPod base URL (without /run suffix)."""
    endpoint = settings.RUNPOD_ENDPOINT
    if endpoint.endswith("/run"):
        return endpoint[:-4]
    return endpoint.rstrip("/")


async def submit_and_poll(prompt: str, negative_prompt: str, steps: int, seed: int) -> bytes:
    """Submit image job to RunPod via /run, poll /status until done, return image bytes."""
    base_url = _get_base_url()
    run_url = f"{base_url}/run"
    print(f"    RunPod URL: {run_url}")
    headers = {
        "Authorization": f"Bearer {settings.RUNPOD_API_KEY_POD}",
        "Content-Type": "application/json",
    }

    payload = {
        "input": {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "steps": steps,
            "seed": seed,
        }
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(run_url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    runpod_job_id = data.get("id")
    if not runpod_job_id:
        raise RuntimeError(f"No job ID in RunPod response: {data}")

    # Poll for completion
    status_url = f"{base_url}/status/{runpod_job_id}"
    start = time.time()
    while True:
        await asyncio.sleep(POLL_INTERVAL)
        elapsed = time.time() - start
        if elapsed > POLL_TIMEOUT:
            raise RuntimeError(f"RunPod job {runpod_job_id} timed out after {POLL_TIMEOUT}s")

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(status_url, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        status = data.get("status", "").upper()
        if status == "COMPLETED":
            break
        elif status in ("FAILED", "CANCELLED", "TIMED_OUT"):
            error = data.get("error", "Unknown error")
            raise RuntimeError(f"RunPod job {runpod_job_id} {status}: {error}")
        # else IN_QUEUE / IN_PROGRESS — keep polling

    output = data.get("output", {})
    images = output.get("images", [])
    if not images:
        raise RuntimeError(f"No images in RunPod output for job {runpod_job_id}")

    first = images[0]
    if isinstance(first, dict) and first.get("type") == "base64":
        return base64.b64decode(first["data"])
    elif isinstance(first, str):
        # URL — download it
        async with httpx.AsyncClient(timeout=30) as client:
            dl = await client.get(first)
            dl.raise_for_status()
            return dl.content
    else:
        raise RuntimeError(f"Unknown image format in output: {type(first)}")


async def generate_and_upload(story_id: str, prompt: str, negative_prompt: str, steps: int, index: int) -> str | None:
    """Generate one image and upload to Cloudflare. Returns CF URL or None."""
    seed = random.randint(1, 2147483647)
    try:
        print(f"    [img {index+1}/{IMAGES_PER_STORY}] Generating (seed={seed})...")
        image_bytes = await submit_and_poll(prompt, negative_prompt, steps, seed)
        print(f"    [img {index+1}/{IMAGES_PER_STORY}] Got {len(image_bytes)} bytes, uploading to Cloudflare...")

        filename = f"regen_{story_id}_{index}_{seed}.png"
        cf_result = await upload_to_cloudflare_tg(image_bytes, filename)

        if cf_result.success:
            print(f"    [img {index+1}/{IMAGES_PER_STORY}] ✅ {cf_result.image_url}")
            return cf_result.image_url
        else:
            print(f"    [img {index+1}/{IMAGES_PER_STORY}] ❌ CF upload failed: {cf_result.error}")
            return None
    except Exception as e:
        print(f"    [img {index+1}/{IMAGES_PER_STORY}] ❌ Error: {e}")
        return None


async def main():
    from app.db.base import get_db
    from app.db.models import PersonaHistoryStart
    from sqlalchemy import text

    # 1. Fetch all stories with image_prompt
    print("📦 Fetching stories from database...")
    with get_db() as db:
        stories = (
            db.query(PersonaHistoryStart)
            .filter(PersonaHistoryStart.image_prompt.isnot(None))
            .filter(PersonaHistoryStart.image_prompt != "")
            .all()
        )

        # Get persona names via raw SQL to avoid model column mismatch
        persona_names = {}
        rows = db.execute(text("SELECT id, name FROM personas")).fetchall()
        for row in rows:
            persona_names[str(row[0])] = row[1]

        story_data = []
        for s in stories:
            story_data.append({
                "id": str(s.id),
                "name": s.name or "Untitled",
                "persona_name": persona_names.get(str(s.persona_id), "Unknown"),
                "old_image_url": s.image_url,
                "image_prompt": s.image_prompt,
            })

    print(f"Found {len(story_data)} stories with image_prompt\n")

    if not story_data:
        print("Nothing to do.")
        return

    config = get_app_config()
    negative_prompt = config["image"]["negative_prompt"]
    steps = config["image"]["steps"]

    # 2. Generate images for each story
    results = []
    for idx, story in enumerate(story_data):
        print(f"[{idx+1}/{len(story_data)}] {story['persona_name']} / {story['name']}")
        print(f"  Prompt: {story['image_prompt'][:100]}...")

        new_urls = []
        for i in range(IMAGES_PER_STORY):
            url = await generate_and_upload(story["id"], story["image_prompt"], negative_prompt, steps, i)
            new_urls.append(url)

        results.append({
            **story,
            "new_image_urls": new_urls,
        })
        print(f"  → {sum(1 for u in new_urls if u)}/{IMAGES_PER_STORY} images generated\n")

    # 3. Save results
    out_path = os.path.join(os.path.dirname(__file__), "story_regen_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    total_ok = sum(1 for r in results for u in r["new_image_urls"] if u)
    total_expected = len(results) * IMAGES_PER_STORY
    print(f"🎉 Done! {total_ok}/{total_expected} images generated successfully.")
    print(f"📄 Results saved to {out_path}")


if __name__ == "__main__":
    print("=" * 60)
    print("Story Image Regeneration")
    print("=" * 60 + "\n")
    asyncio.run(main())
