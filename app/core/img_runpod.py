"""
Runpod Image Generation Client
"""
import httpx
from uuid import UUID
from app.settings import settings, get_app_config
from app.core.security import generate_hmac_signature


async def submit_image_job(
    job_id: UUID,
    prompt: str,
    negative_prompt: str,
    seed: int = None
) -> dict:
    """
    Submit image generation job to Runpod
    
    Args:
        job_id: UUID of the image job (from database)
        prompt: Positive prompt for image generation
        negative_prompt: Negative prompt
        seed: Random seed (optional)
    
    Returns:
        Runpod API response
    """
    config = get_app_config()
    img_config = config["image"]
    
    # Build webhook URL with HMAC signature
    webhook_base = f"{settings.public_url}/image/callback"
    job_id_str = str(job_id)
    
    # Generate HMAC signature for webhook security
    signature = generate_hmac_signature(job_id_str)
    webhook_url = f"{webhook_base}?job_id={job_id_str}&sig={signature}"
    
    # Build Runpod request payload
    payload = {
        "input": {
            "job_id": job_id_str,
            "webhook_url": webhook_url,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "width": img_config["width"],
            "height": img_config["height"],
            "steps": img_config["steps"],
            "cfg_scale": img_config["cfg_scale"],
            "sampler_name": img_config["sampler_name"],
            "scheduler": img_config["scheduler"],
            "seed": seed or -1  # -1 = random
        }
    }
    
    headers = {
        "Authorization": f"Bearer {settings.RUNPOD_API_KEY_POD}",
        "Content-Type": "application/json"
    }
    
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                settings.RUNPOD_ENDPOINT,
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            
            return response.json()
    
    except httpx.HTTPStatusError as e:
        raise Exception(f"Runpod API error: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        raise Exception(f"Runpod submission failed: {str(e)}")


async def dispatch_image_generation(
    job_id: UUID,
    prompt: str,
    negative_prompt: str,
    tg_chat_id: int
) -> bool:
    """
    Dispatch image generation to RunPod (used by pipeline)
    
    Returns:
        True if dispatched successfully, False otherwise
    """
    try:
        print(f"[RUNPOD] Dispatching job {job_id}")
        result = await submit_image_job(
            job_id=job_id,
            prompt=prompt,
            negative_prompt=negative_prompt
        )
        print(f"[RUNPOD] Job dispatched: {result}")
        return True
    except Exception as e:
        print(f"[RUNPOD] ❌ Dispatch failed: {e}")
        return False


