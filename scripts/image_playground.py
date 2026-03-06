"""
Simple image generation playground server.
Run: python scripts/image_playground.py
Opens http://localhost:8899 with prompt input + image grid.
"""
import os
import json
import random
import base64
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import httpx
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import uvicorn

RUNPOD_API_KEY = os.environ["RUNPOD_API_KEY_POD"]
RUNPOD_ENDPOINT = os.environ["RUNPOD_ENDPOINT"]
RUNSYNC_ENDPOINT = RUNPOD_ENDPOINT.replace("/run", "/runsync")

QUALITY_PROMPT = "masterpiece, best quality, absurdres, newest, highres, ultra detailed, sharp focus, detailed face, detailed eyes, eye_focus, looking_at_viewer, eye_contact, skin texture, depth of field"
NEGATIVE_PROMPT = "lowres, (bad), worst quality, bad quality, bad anatomy, bad hands, extra digits, fewer digits, multiple views, extra, missing, text, error, jpeg artifacts, watermark, unfinished, displeasing, oldest, signature, username, scan, comic, greyscale, monochrome, blurry, blur, out of focus, motion blur, distant shot, far away, wide shot, long shot, full body, bad eyes, blurry eyes, asymmetrical eyes, deformed eyes, cross-eyed, lazy eye, 1boy, male_focus"
STEPS = 25

app = FastAPI()

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Image Playground</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0a0a0a; color: #e0e0e0; min-height: 100vh; }
  .container { max-width: 1200px; margin: 0 auto; padding: 24px; }
  h1 { text-align: center; margin-bottom: 24px; font-size: 1.5rem; color: #fff; }
  .input-row { display: flex; gap: 12px; margin-bottom: 16px; }
  .input-row input { flex: 1; padding: 12px 16px; border-radius: 8px; border: 1px solid #333; background: #1a1a1a; color: #fff; font-size: 1rem; outline: none; }
  .input-row input:focus { border-color: #646cff; }
  .input-row button { padding: 12px 24px; border-radius: 8px; border: none; background: #646cff; color: #fff; font-size: 1rem; cursor: pointer; white-space: nowrap; }
  .input-row button:hover { background: #535bf2; }
  .input-row button:disabled { background: #333; cursor: not-allowed; }
  .options { display: flex; gap: 16px; margin-bottom: 16px; align-items: center; flex-wrap: wrap; }
  .options label { font-size: 0.85rem; color: #aaa; }
  .options input[type=number] { width: 60px; padding: 6px 8px; border-radius: 6px; border: 1px solid #333; background: #1a1a1a; color: #fff; font-size: 0.85rem; }
  .status { text-align: center; margin-bottom: 16px; min-height: 24px; color: #888; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
  .card { background: #1a1a1a; border-radius: 10px; overflow: hidden; border: 1px solid #222; }
  .card img { width: 100%; display: block; }
  .card .meta { padding: 8px 12px; font-size: 0.8rem; color: #888; word-break: break-all; display: flex; justify-content: space-between; align-items: center; }
  .card .meta span { flex: 1; }
  .card .meta a { color: #646cff; text-decoration: none; font-size: 0.8rem; margin-left: 8px; cursor: pointer; }
  .card .meta a:hover { color: #535bf2; }
  .overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.9); z-index: 100; justify-content: center; align-items: center; cursor: zoom-out; }
  .overlay.active { display: flex; }
  .overlay img { max-width: 95vw; max-height: 95vh; border-radius: 8px; }
</style>
</head>
<body>
<div class="container">
  <h1>Image Playground</h1>
  <div class="input-row">
    <input type="text" id="prompt" placeholder="Enter your prompt..." autofocus />
    <button id="btn" onclick="generate()">Generate</button>
  </div>
  <div class="options">
    <label>Count: <input type="number" id="count" value="1" min="1" max="4"></label>
    <label>Steps: <input type="number" id="steps" value="25" min="1" max="50"></label>
    <label><input type="checkbox" id="prepend" checked> Prepend quality tags</label>
  </div>
  <div class="status" id="status"></div>
  <div class="grid" id="grid"></div>
</div>
<div class="overlay" id="overlay" onclick="this.classList.remove('active')"><img id="overlayImg" /></div>
<script>
const promptEl = document.getElementById('prompt');
const btn = document.getElementById('btn');
const status = document.getElementById('status');
const grid = document.getElementById('grid');

promptEl.addEventListener('keydown', e => { if (e.key === 'Enter') generate(); });

function expand(src) {
  document.getElementById('overlayImg').src = src;
  document.getElementById('overlay').classList.add('active');
}

function download(src, seed) {
  const a = document.createElement('a');
  a.href = src;
  a.download = 'image_' + seed + '.png';
  a.click();
}

async function generate() {
  const prompt = promptEl.value.trim();
  if (!prompt) return;
  const count = parseInt(document.getElementById('count').value) || 1;
  const steps = parseInt(document.getElementById('steps').value) || 25;
  const prepend = document.getElementById('prepend').checked;

  btn.disabled = true;
  status.textContent = 'Generating ' + count + ' image(s)...';

  const promises = [];
  for (let i = 0; i < count; i++) {
    promises.push(
      fetch('/api/generate', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ prompt, steps, prepend_quality: prepend })
      }).then(r => r.json())
    );
  }

  let done = 0;
  for (const p of promises) {
    try {
      const data = await p;
      done++;
      status.textContent = 'Done ' + done + '/' + count;
      if (data.image) {
        const card = document.createElement('div');
        card.className = 'card';
        const src = 'data:image/png;base64,' + data.image;
        const img = document.createElement('img');
        img.src = src;
        img.onclick = () => expand(src);
        const meta = document.createElement('div');
        meta.className = 'meta';
        const span = document.createElement('span');
        span.textContent = prompt + ' | seed: ' + data.seed;
        const dl = document.createElement('a');
        dl.textContent = 'download';
        dl.onclick = (e) => { e.stopPropagation(); download(src, data.seed); };
        meta.appendChild(span);
        meta.appendChild(dl);
        card.appendChild(img);
        card.appendChild(meta);
        grid.prepend(card);
      } else {
        status.textContent = 'Error: ' + (data.error || 'unknown');
      }
    } catch(e) {
      status.textContent = 'Error: ' + e.message;
    }
  }
  btn.disabled = false;
  if (done === count) status.textContent = 'Done! ' + count + ' image(s) generated.';
}
</script>
</body>
</html>"""


class GenerateRequest(BaseModel):
    prompt: str
    steps: int = STEPS
    prepend_quality: bool = True


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML_PAGE


@app.post("/api/generate")
async def generate(req: GenerateRequest):
    prompt = req.prompt
    if req.prepend_quality:
        prompt = f"{QUALITY_PROMPT}, {prompt}"

    seed = random.randint(0, 2147483647)

    payload = {
        "input": {
            "prompt": prompt,
            "negative_prompt": NEGATIVE_PROMPT,
            "steps": req.steps,
            "seed": seed,
        }
    }

    headers = {
        "Authorization": f"Bearer {RUNPOD_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(RUNSYNC_ENDPOINT, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        output = data.get("output", {})
        images = output.get("images", [])
        if images:
            first = images[0]
            if isinstance(first, dict) and first.get("type") == "base64":
                return {"image": first["data"], "seed": seed}
            elif isinstance(first, str):
                async with httpx.AsyncClient(timeout=30) as client:
                    img_resp = await client.get(first)
                    return {"image": base64.b64encode(img_resp.content).decode(), "seed": seed}

        return {"error": f"Unexpected response: {json.dumps(data)[:500]}", "seed": seed}

    except Exception as e:
        return JSONResponse({"error": str(e), "seed": seed}, status_code=500)


if __name__ == "__main__":
    print(f"RunPod endpoint: {RUNSYNC_ENDPOINT}")
    print("Starting playground at http://localhost:8899")
    uvicorn.run(app, host="0.0.0.0", port=8899)
