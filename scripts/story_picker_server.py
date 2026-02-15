"""
Simple FastAPI server for the Story Image Picker.
- Serves HTML with embedded JSON data
- POST /api/generate — generate N images with a given prompt via RunPod + Cloudflare

Usage:
    python scripts/story_picker_server.py
"""
import asyncio
import base64
import json
import os
import random
import sys
import time

import httpx
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.settings import settings, load_configs, get_app_config
from app.core.cloudflare_upload import upload_to_cloudflare_tg

load_configs()

app = FastAPI()

POLL_INTERVAL = 2
POLL_TIMEOUT = 120
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_PATH = os.path.join(SCRIPT_DIR, "story_regen_results.json")
ROUND1_SELECTED_PATH = os.path.join(SCRIPT_DIR, "story_selected_round1.json")
ROUND2_PROMPTS_PATH = os.path.join(os.path.dirname(SCRIPT_DIR), "config", "story_round2_prompts.json")


def _normalize_cf_url(url: str) -> str:
    if not url:
        return url
    if url.endswith("/admin"):
        return url[:-6] + "/public"
    return url


def _enforce_closeup_pov(prompt: str) -> str:
    p = (prompt or "").strip()
    if not p:
        return "close-up shot, POV perspective"

    p_lower = p.lower()
    if "close-up shot" not in p_lower:
        if "medium shot" in p_lower:
            idx = p_lower.index("medium shot")
            p = p[:idx] + "close-up shot" + p[idx + len("medium shot"):]
        else:
            p = f"close-up shot, {p}"
        p_lower = p.lower()

    if "pov perspective" not in p_lower and "pov style" not in p_lower:
        idx = p_lower.find("close-up shot")
        if idx >= 0:
            insert_at = idx + len("close-up shot")
            p = p[:insert_at] + ", POV perspective" + p[insert_at:]
        else:
            p = f"POV perspective, {p}"

    return p


def _load_round2_data() -> list[dict]:
    with open(RESULTS_PATH, "r", encoding="utf-8") as f:
        all_stories = json.load(f)

    selected_ids = set()
    if os.path.exists(ROUND1_SELECTED_PATH):
        with open(ROUND1_SELECTED_PATH, "r", encoding="utf-8") as f:
            selected_ids = set(json.load(f).keys())

    prompts_map = {}
    if os.path.exists(ROUND2_PROMPTS_PATH):
        with open(ROUND2_PROMPTS_PATH, "r", encoding="utf-8") as f:
            prompts_map = json.load(f)

    remaining = []
    for story in all_stories:
        story_id = story.get("id")
        if story_id in selected_ids:
            continue

        old_prompt = story.get("image_prompt", "")

        remaining.append({
            "id": story_id,
            "name": story.get("name"),
            "persona_name": story.get("persona_name"),
            "old_image_url": _normalize_cf_url(story.get("old_image_url")),
            "old_prompt": old_prompt,
            "round2_prompt": prompts_map.get(story_id, _enforce_closeup_pov(old_prompt)),
            "new_image_urls": [u for u in story.get("new_image_urls", []) if u],
        })
    return remaining


def _get_base_url() -> str:
    endpoint = settings.RUNPOD_ENDPOINT
    if endpoint.endswith("/run"):
        return endpoint[:-4]
    return endpoint.rstrip("/")


async def submit_and_poll(prompt: str, negative_prompt: str, steps: int, seed: int) -> bytes:
    base_url = _get_base_url()
    run_url = f"{base_url}/run"
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

    job_id = data.get("id")
    if not job_id:
        raise RuntimeError(f"No job ID: {data}")

    status_url = f"{base_url}/status/{job_id}"
    start = time.time()
    while True:
        await asyncio.sleep(POLL_INTERVAL)
        if time.time() - start > POLL_TIMEOUT:
            raise RuntimeError(f"Timeout for job {job_id}")
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(status_url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        status = data.get("status", "").upper()
        if status == "COMPLETED":
            break
        elif status in ("FAILED", "CANCELLED", "TIMED_OUT"):
            raise RuntimeError(f"Job {job_id} {status}: {data.get('error')}")

    images = data.get("output", {}).get("images", [])
    if not images:
        raise RuntimeError(f"No images for job {job_id}")
    first = images[0]
    if isinstance(first, dict) and first.get("type") == "base64":
        return base64.b64decode(first["data"])
    elif isinstance(first, str):
        async with httpx.AsyncClient(timeout=30) as client:
            dl = await client.get(first)
            dl.raise_for_status()
            return dl.content
    raise RuntimeError(f"Unknown image format: {type(first)}")


class GenerateRequest(BaseModel):
    prompt: str
    count: int = 1  # 1–5


@app.post("/api/generate")
async def api_generate(req: GenerateRequest):
    config = get_app_config()
    negative_prompt = config["image"]["negative_prompt"]
    steps = config["image"]["steps"]
    count = max(1, min(5, req.count))

    urls = []
    for i in range(count):
        seed = random.randint(1, 2147483647)
        try:
            print(f"  [gen {i+1}/{count}] seed={seed}...")
            img_bytes = await submit_and_poll(req.prompt, negative_prompt, steps, seed)
            filename = f"picker_{seed}.png"
            cf = await upload_to_cloudflare_tg(img_bytes, filename)
            if cf.success:
                print(f"  [gen {i+1}/{count}] ✅ {cf.image_url}")
                urls.append(cf.image_url)
            else:
                print(f"  [gen {i+1}/{count}] ❌ CF: {cf.error}")
                urls.append(None)
        except Exception as e:
            print(f"  [gen {i+1}/{count}] ❌ {e}")
            urls.append(None)
    return {"urls": urls}


@app.get("/", response_class=HTMLResponse)
async def index():
    # Load results JSON
    with open(RESULTS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Fix /admin -> /public in old_image_url
    for story in data:
        url = story.get("old_image_url", "")
        if url and url.endswith("/admin"):
            story["old_image_url"] = url[:-6] + "/public"

    json_str = json.dumps(data, ensure_ascii=False)
    return HTML_TEMPLATE.replace("__STORY_DATA__", json_str)


@app.get("/round2", response_class=HTMLResponse)
async def round2_page():
    data = _load_round2_data()
    json_str = json.dumps(data, ensure_ascii=False)
    return HTML_TEMPLATE_ROUND2.replace("__ROUND2_STORY_DATA__", json_str)


@app.get("/api/round2/remaining")
async def round2_remaining():
    return {"stories": _load_round2_data()}


@app.post("/api/save")
async def api_save(body: dict):
    """Save updated results back to JSON file."""
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(body.get("data", []), f, indent=2, ensure_ascii=False)
    return {"ok": True}


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Story Image Picker</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #1a1a2e; color: #e0e0e0; padding: 20px; }
  h1 { text-align: center; margin-bottom: 24px; color: #fff; }

  .story-card { background: #16213e; border-radius: 12px; padding: 20px; margin-bottom: 24px; }
  .story-header { margin-bottom: 12px; display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
  .story-header h2 { font-size: 18px; color: #4a6cf7; }
  .story-header .persona { font-size: 13px; color: #888; }
  .story-header .prompt-toggle { font-size: 11px; color: #666; cursor: pointer; text-decoration: underline; }
  .prompt-box { font-size: 11px; color: #999; margin: 8px 0; word-break: break-all; display: none; background: #0f3460; padding: 8px; border-radius: 6px; }
  .prompt-box.visible { display: block; }

  .images-row { display: flex; gap: 12px; align-items: flex-start; flex-wrap: wrap; }
  .old-image-col { flex-shrink: 0; }
  .old-image-col .label { font-size: 12px; color: #888; margin-bottom: 4px; text-align: center; }
  .new-images-col { display: flex; gap: 10px; flex-wrap: wrap; flex: 1; }

  .img-card { display: flex; flex-direction: column; align-items: center; }
  .img-card img { border-radius: 8px; cursor: pointer; object-fit: cover; background: #0f3460; }
  .img-card img.old { width: 300px; height: auto; }
  .img-card img.new { width: 180px; height: auto; }
  .select-btn { margin-top: 6px; padding: 4px 16px; border-radius: 6px; border: 2px solid #4a6cf7; background: transparent; color: #4a6cf7; cursor: pointer; font-size: 12px; transition: all 0.2s; }
  .select-btn:hover { background: #4a6cf720; }
  .select-btn.selected { background: #4a6cf7; color: #fff; }

  /* Regen section */
  .regen-section { margin-top: 12px; padding-top: 12px; border-top: 1px solid #0f3460; }
  .regen-btn { background: #e67e22; color: #fff; border: none; padding: 6px 16px; border-radius: 6px; cursor: pointer; font-size: 12px; }
  .regen-btn:hover { background: #d35400; }
  .regen-panel { display: none; margin-top: 10px; }
  .regen-panel.visible { display: block; }
  .regen-panel textarea { width: 100%; height: 100px; background: #0f3460; color: #e0e0e0; border: 1px solid #4a6cf7; border-radius: 6px; padding: 8px; font-size: 12px; resize: vertical; font-family: inherit; }
  .regen-controls { display: flex; gap: 10px; align-items: center; margin-top: 8px; }
  .regen-controls label { font-size: 12px; color: #888; }
  .regen-controls select { background: #0f3460; color: #e0e0e0; border: 1px solid #4a6cf7; border-radius: 4px; padding: 4px 8px; font-size: 12px; }
  .regen-go { background: #27ae60; color: #fff; border: none; padding: 6px 20px; border-radius: 6px; cursor: pointer; font-size: 12px; }
  .regen-go:hover { background: #219a52; }
  .regen-go:disabled { background: #555; cursor: not-allowed; }
  .regen-status { font-size: 11px; color: #888; margin-left: 10px; }
  .regen-results { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 10px; }

  /* Modal */
  .modal-overlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.85); z-index: 1000; justify-content: center; align-items: center; }
  .modal-overlay.active { display: flex; }
  .modal-overlay img { max-width: 95vw; max-height: 95vh; border-radius: 8px; }

  /* JSON output */
  .json-output { background: #0f3460; border-radius: 12px; padding: 20px; margin-top: 32px; position: relative; }
  .json-output h3 { margin-bottom: 12px; color: #4a6cf7; }
  .json-output pre { background: #1a1a2e; padding: 16px; border-radius: 8px; overflow-x: auto; font-size: 13px; color: #e0e0e0; min-height: 60px; white-space: pre-wrap; word-break: break-all; }
  .copy-btn { position: absolute; top: 16px; right: 16px; background: #4a6cf7; color: #fff; border: none; padding: 6px 16px; border-radius: 6px; cursor: pointer; font-size: 12px; }
  .copy-btn:hover { background: #3a5ce5; }
  .no-img { width: 300px; height: 200px; background: #0f3460; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: #666; }
</style>
</head>
<body>

<h1>Story Image Picker</h1>
<div id="container"></div>

<div class="json-output">
  <h3>Selection JSON</h3>
  <button class="copy-btn" onclick="copyJson()">Copy</button>
  <pre id="jsonOutput">{}</pre>
</div>

<div class="modal-overlay" id="modal" onclick="closeModal()">
  <img id="modalImg" src="" alt="Full size">
</div>

<script>
const data = __STORY_DATA__;
const selections = {};

function render() {
  const c = document.getElementById('container');
  c.innerHTML = '';
  data.forEach((story, si) => {
    const card = document.createElement('div');
    card.className = 'story-card';
    card.id = 'card-' + si;

    // Header
    const hdr = document.createElement('div');
    hdr.className = 'story-header';
    hdr.innerHTML = `<h2>${esc(story.name)}</h2><span class="persona">${esc(story.persona_name)}</span><span class="prompt-toggle" onclick="togglePrompt(${si})">show prompt</span>`;
    card.appendChild(hdr);

    // Prompt box
    const pb = document.createElement('div');
    pb.className = 'prompt-box';
    pb.id = 'prompt-' + si;
    pb.textContent = story.image_prompt || '';
    card.appendChild(pb);

    // Images row
    const row = document.createElement('div');
    row.className = 'images-row';

    // Old image
    const oldCol = document.createElement('div');
    oldCol.className = 'old-image-col';
    oldCol.innerHTML = '<div class="label">Current</div>';
    const oldCard = document.createElement('div');
    oldCard.className = 'img-card';
    if (story.old_image_url) {
      const img = document.createElement('img');
      img.className = 'old';
      img.src = story.old_image_url;
      img.loading = 'lazy';
      img.onclick = () => openModal(story.old_image_url);
      oldCard.appendChild(img);
    } else {
      oldCard.innerHTML = '<div class="no-img">No image</div>';
    }
    oldCol.appendChild(oldCard);
    row.appendChild(oldCol);

    // New images
    const newCol = document.createElement('div');
    newCol.className = 'new-images-col';
    const allUrls = story.new_image_urls || [];
    allUrls.forEach((url) => {
      if (!url) return;
      const nc = document.createElement('div');
      nc.className = 'img-card';
      const isSel = selections[story.id] === url;
      const img = document.createElement('img');
      img.className = 'new';
      img.src = url;
      img.loading = 'lazy';
      img.onclick = () => openModal(url);
      nc.appendChild(img);
      const btn = document.createElement('button');
      btn.className = 'select-btn' + (isSel ? ' selected' : '');
      btn.textContent = isSel ? '✓ Selected' : 'Select';
      btn.onclick = () => doSelect(story.id, url, si);
      nc.appendChild(btn);
      newCol.appendChild(nc);
    });
    row.appendChild(newCol);
    card.appendChild(row);

    // Regen section
    const regen = document.createElement('div');
    regen.className = 'regen-section';
    regen.innerHTML = `
      <button class="regen-btn" onclick="toggleRegen(${si})">🔄 Regenerate with edited prompt</button>
      <div class="regen-panel" id="regen-panel-${si}">
        <textarea id="regen-prompt-${si}">${esc(story.image_prompt || '')}</textarea>
        <div class="regen-controls">
          <label>Images:</label>
          <select id="regen-count-${si}">${[1,2,3,4,5].map(n => `<option value="${n}"${n===3?' selected':''}>${n}</option>`).join('')}</select>
          <button class="regen-go" id="regen-go-${si}" onclick="doRegen(${si})">Generate</button>
          <span class="regen-status" id="regen-status-${si}"></span>
        </div>
        <div class="regen-results" id="regen-results-${si}"></div>
      </div>
    `;
    card.appendChild(regen);

    c.appendChild(card);
  });
  updateJson();
}

function togglePrompt(si) {
  document.getElementById('prompt-' + si).classList.toggle('visible');
}

function toggleRegen(si) {
  document.getElementById('regen-panel-' + si).classList.toggle('visible');
}

async function doRegen(si) {
  const prompt = document.getElementById('regen-prompt-' + si).value.trim();
  const count = parseInt(document.getElementById('regen-count-' + si).value);
  const btn = document.getElementById('regen-go-' + si);
  const status = document.getElementById('regen-status-' + si);
  const results = document.getElementById('regen-results-' + si);

  if (!prompt) { alert('Prompt is empty'); return; }

  btn.disabled = true;
  status.textContent = 'Generating...';
  results.innerHTML = '';

  try {
    const resp = await fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt, count })
    });
    const json = await resp.json();
    const urls = (json.urls || []).filter(u => u);

    if (!urls.length) {
      status.textContent = '❌ No images generated';
      btn.disabled = false;
      return;
    }

    // Add to story data
    data[si].new_image_urls = [...(data[si].new_image_urls || []), ...urls];

    // Show new images with select buttons
    urls.forEach(url => {
      const nc = document.createElement('div');
      nc.className = 'img-card';
      const img = document.createElement('img');
      img.className = 'new';
      img.src = url;
      img.onclick = () => openModal(url);
      nc.appendChild(img);
      const sbtn = document.createElement('button');
      sbtn.className = 'select-btn';
      sbtn.textContent = 'Select';
      sbtn.onclick = () => doSelect(data[si].id, url, si);
      nc.appendChild(sbtn);
      results.appendChild(nc);
    });

    status.textContent = `✅ ${urls.length} image(s) generated`;

    // Also add to the main images row
    const mainNewCol = document.querySelector('#card-' + si + ' .new-images-col');
    if (mainNewCol) {
      urls.forEach(url => {
        const nc = document.createElement('div');
        nc.className = 'img-card';
        const img = document.createElement('img');
        img.className = 'new';
        img.src = url;
        img.onclick = () => openModal(url);
        nc.appendChild(img);
        const sbtn = document.createElement('button');
        sbtn.className = 'select-btn';
        sbtn.textContent = 'Select';
        sbtn.onclick = () => doSelect(data[si].id, url, si);
        nc.appendChild(sbtn);
        mainNewCol.appendChild(nc);
      });
    }
  } catch (e) {
    status.textContent = '❌ Error: ' + e.message;
  }
  btn.disabled = false;
}

function doSelect(storyId, url, si) {
  if (selections[storyId] === url) {
    delete selections[storyId];
  } else {
    selections[storyId] = url;
  }
  // Update all select buttons in this card
  const card = document.getElementById('card-' + si);
  card.querySelectorAll('.select-btn').forEach(b => {
    const imgEl = b.previousElementSibling;
    if (!imgEl || !imgEl.src) return;
    if (selections[storyId] === imgEl.src) {
      b.className = 'select-btn selected';
      b.textContent = '✓ Selected';
    } else {
      b.className = 'select-btn';
      b.textContent = 'Select';
    }
  });
  updateJson();
}

function updateJson() {
  document.getElementById('jsonOutput').textContent = JSON.stringify(selections, null, 2);
}

function copyJson() {
  navigator.clipboard.writeText(JSON.stringify(selections, null, 2)).then(() => {
    const btn = document.querySelector('.copy-btn');
    btn.textContent = 'Copied!';
    setTimeout(() => btn.textContent = 'Copy', 1500);
  });
}

function openModal(url) {
  document.getElementById('modalImg').src = url;
  document.getElementById('modal').classList.add('active');
}
function closeModal() {
  document.getElementById('modal').classList.remove('active');
  document.getElementById('modalImg').src = '';
}
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

function esc(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

render();
</script>
</body>
</html>"""


HTML_TEMPLATE_ROUND2 = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Story Image Picker - Round 2</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #151825; color: #e8ebf3; padding: 20px; }
  h1 { text-align: center; margin-bottom: 6px; color: #fff; }
  .sub { text-align: center; color: #90a2c5; margin-bottom: 24px; font-size: 13px; }

  .story-card { background: #1d2437; border-radius: 14px; padding: 18px; margin-bottom: 18px; border: 1px solid #2d3954; }
  .story-header { margin-bottom: 10px; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
  .story-header h2 { font-size: 18px; color: #6fb2ff; }
  .story-header .persona { font-size: 13px; color: #8d9db8; }

  .images-row { display: flex; gap: 12px; align-items: flex-start; flex-wrap: wrap; }
  .old-image-col { flex-shrink: 0; }
  .old-image-col .label { font-size: 12px; color: #8d9db8; margin-bottom: 4px; text-align: center; }
  .new-images-col { display: flex; gap: 10px; flex-wrap: wrap; flex: 1; }

  .img-card { display: flex; flex-direction: column; align-items: center; }
  .img-card img { border-radius: 8px; cursor: pointer; object-fit: cover; background: #101b2f; }
  .img-card img.old { width: 300px; height: auto; }
  .img-card img.new { width: 180px; height: auto; }
  .select-btn { margin-top: 6px; padding: 4px 14px; border-radius: 6px; border: 2px solid #6fb2ff; background: transparent; color: #6fb2ff; cursor: pointer; font-size: 12px; transition: all 0.2s; }
  .select-btn.selected { background: #6fb2ff; color: #0d1628; }

  .prompt-editor { margin-top: 12px; background: #121c31; border: 1px solid #2d3954; border-radius: 10px; padding: 10px; }
  .prompt-editor label { display: block; font-size: 12px; color: #9fb0cf; margin-bottom: 6px; }
  .prompt-editor textarea { width: 100%; height: 110px; background: #0e1628; color: #e8ebf3; border: 1px solid #41557d; border-radius: 6px; padding: 8px; font-size: 12px; resize: vertical; font-family: inherit; }
  .old-prompt { margin-top: 8px; font-size: 11px; color: #97a6c1; }
  .old-prompt summary { cursor: pointer; color: #7f96bd; }
  .old-prompt pre { margin-top: 5px; white-space: pre-wrap; word-break: break-word; background: #0c1424; border-radius: 6px; padding: 8px; }

  .regen-controls { display: flex; gap: 10px; align-items: center; margin-top: 8px; flex-wrap: wrap; }
  .regen-controls select { background: #0e1628; color: #e8ebf3; border: 1px solid #41557d; border-radius: 6px; padding: 5px 8px; }
  .regen-go { background: #2dbb7f; color: #fff; border: none; padding: 6px 16px; border-radius: 6px; cursor: pointer; font-size: 12px; }
  .regen-go:disabled { opacity: 0.6; cursor: not-allowed; }
  .regen-status { font-size: 11px; color: #90a2c5; }

  .modal-overlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.85); z-index: 1000; justify-content: center; align-items: center; }
  .modal-overlay.active { display: flex; }
  .modal-overlay img { max-width: 95vw; max-height: 95vh; border-radius: 8px; }

  .json-output { background: #101b30; border-radius: 12px; padding: 18px; margin-top: 24px; position: relative; border: 1px solid #2d3954; }
  .json-output h3 { margin-bottom: 10px; color: #6fb2ff; }
  .json-output pre { background: #0b1221; padding: 12px; border-radius: 8px; overflow-x: auto; font-size: 12px; min-height: 80px; white-space: pre-wrap; word-break: break-all; }
  .copy-btn { position: absolute; top: 14px; right: 14px; background: #6fb2ff; color: #0d1628; border: none; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 12px; }
  .no-img { width: 300px; height: 200px; background: #101b2f; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: #667a9e; }
</style>
</head>
<body>

<h1>Story Image Picker — Round 2</h1>
<div class="sub">Only remaining stories. Final JSON includes <code>new_prompt</code> + <code>new_image_url</code>.</div>
<div id="container"></div>

<div class="json-output">
  <h3>Round 2 Selection JSON</h3>
  <button class="copy-btn" onclick="copyJson()">Copy</button>
  <pre id="jsonOutput">{}</pre>
</div>

<div class="modal-overlay" id="modal" onclick="closeModal()">
  <img id="modalImg" src="" alt="Full size">
</div>

<script>
const data = __ROUND2_STORY_DATA__;
const selections = {}; // storyId -> { new_prompt, new_image_url }
const promptDrafts = {};

function render() {
  const c = document.getElementById('container');
  c.innerHTML = '';

  data.forEach((story, si) => {
    const card = document.createElement('div');
    card.className = 'story-card';
    card.id = 'card-' + si;

    const hdr = document.createElement('div');
    hdr.className = 'story-header';
    hdr.innerHTML = `<h2>${esc(story.name || 'Untitled')}</h2><span class="persona">${esc(story.persona_name || '')}</span>`;
    card.appendChild(hdr);

    const row = document.createElement('div');
    row.className = 'images-row';

    const oldCol = document.createElement('div');
    oldCol.className = 'old-image-col';
    oldCol.innerHTML = '<div class="label">Current</div>';
    const oldCard = document.createElement('div');
    oldCard.className = 'img-card';
    if (story.old_image_url) {
      const img = document.createElement('img');
      img.className = 'old';
      img.src = story.old_image_url;
      img.loading = 'lazy';
      img.onclick = () => openModal(story.old_image_url);
      oldCard.appendChild(img);
    } else {
      oldCard.innerHTML = '<div class="no-img">No image</div>';
    }
    oldCol.appendChild(oldCard);
    row.appendChild(oldCol);

    const newCol = document.createElement('div');
    newCol.className = 'new-images-col';
    newCol.id = 'candidates-' + si;
    row.appendChild(newCol);
    card.appendChild(row);

    const editor = document.createElement('div');
    editor.className = 'prompt-editor';
    editor.innerHTML = `
      <label>Round 2 prompt</label>
      <textarea id="prompt-${si}"></textarea>
      <div class="regen-controls">
        <span style="font-size:12px;color:#9fb0cf;">Generate</span>
        <select id="count-${si}">${[1,2,3,4,5].map(n => `<option value="${n}"${n===3?' selected':''}>${n}</option>`).join('')}</select>
        <button class="regen-go" id="regen-${si}" onclick="doRegen(${si})">Generate</button>
        <span class="regen-status" id="status-${si}"></span>
      </div>
      <details class="old-prompt"><summary>Show old prompt</summary><pre>${esc(story.old_prompt || '')}</pre></details>
    `;
    card.appendChild(editor);

    c.appendChild(card);

    const initialPrompt = promptDrafts[story.id] || story.round2_prompt || '';
    const ta = document.getElementById(`prompt-${si}`);
    ta.value = initialPrompt;
    ta.addEventListener('input', () => {
      promptDrafts[story.id] = ta.value;
      if (selections[story.id]) {
        selections[story.id].new_prompt = ta.value.trim();
        updateJson();
      }
    });

    renderCandidates(si);
  });

  updateJson();
}

function renderCandidates(si) {
  const story = data[si];
  const container = document.getElementById('candidates-' + si);
  container.innerHTML = '';
  (story.new_image_urls || []).forEach((url) => {
    if (!url) return;
    const card = document.createElement('div');
    card.className = 'img-card';

    const img = document.createElement('img');
    img.className = 'new';
    img.src = url;
    img.loading = 'lazy';
    img.onclick = () => openModal(url);
    card.appendChild(img);

    const btn = document.createElement('button');
    const selected = selections[story.id] && selections[story.id].new_image_url === url;
    btn.className = 'select-btn' + (selected ? ' selected' : '');
    btn.textContent = selected ? '✓ Selected' : 'Select';
    btn.onclick = () => selectImage(si, url);
    card.appendChild(btn);

    container.appendChild(card);
  });
}

function selectImage(si, url) {
  const story = data[si];
  const prompt = (document.getElementById('prompt-' + si).value || '').trim();
  selections[story.id] = {
    new_prompt: prompt,
    new_image_url: url,
  };
  renderCandidates(si);
  updateJson();
}

async function doRegen(si) {
  const story = data[si];
  const prompt = (document.getElementById('prompt-' + si).value || '').trim();
  const count = parseInt(document.getElementById('count-' + si).value, 10);
  const btn = document.getElementById('regen-' + si);
  const status = document.getElementById('status-' + si);

  if (!prompt) {
    alert('Prompt is empty');
    return;
  }

  promptDrafts[story.id] = prompt;
  btn.disabled = true;
  status.textContent = 'Generating...';

  try {
    const resp = await fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt, count }),
    });
    const json = await resp.json();
    const urls = (json.urls || []).filter(Boolean);

    if (!urls.length) {
      status.textContent = 'No images generated';
      btn.disabled = false;
      return;
    }

    story.new_image_urls = [...(story.new_image_urls || []), ...urls];
    renderCandidates(si);
    status.textContent = `Generated ${urls.length}`;
  } catch (e) {
    status.textContent = 'Error: ' + e.message;
  }
  btn.disabled = false;
}

function updateJson() {
  document.getElementById('jsonOutput').textContent = JSON.stringify(selections, null, 2);
}

function copyJson() {
  navigator.clipboard.writeText(JSON.stringify(selections, null, 2)).then(() => {
    const btn = document.querySelector('.copy-btn');
    btn.textContent = 'Copied!';
    setTimeout(() => btn.textContent = 'Copy', 1500);
  });
}

function openModal(url) {
  document.getElementById('modalImg').src = url;
  document.getElementById('modal').classList.add('active');
}

function closeModal() {
  document.getElementById('modal').classList.remove('active');
  document.getElementById('modalImg').src = '';
}

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeModal();
});

function esc(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

render();
</script>
</body>
</html>"""


if __name__ == "__main__":
    print("=" * 50)
    print("Story Image Picker Server")
    print(f"Open http://localhost:8899")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8899)
