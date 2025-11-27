# Face Character Creation Feature - Implementation Guide

## Overview

This feature allows users to upload a photo and generate an anime-style character with the exact same face preserved across all generated images. The system uses **IP-Adapter-FaceID** with InsightFace embeddings for face consistency.

## Architecture

### Face Consistency Method: IP-Adapter-FaceID

We use **IP-Adapter-FaceID** because:
- Best for anime/stylized output (vs InstantID which is better for photorealism)
- Fast inference (~5-10% faster than alternatives)
- Proven track record for SDXL anime workflows
- Easier to tune with intuitive weight parameters

### Data Flow

1. **User uploads photo** (Telegram Mini App)
2. **Backend extracts face embeddings** (InsightFace Buffalo_L model, 512-dim)
3. **Photo uploaded to Cloudflare** (30-day retention)
4. **Persona created** with embeddings stored in database
5. **Image generation** passes embeddings to Runpod/ComfyUI
6. **ComfyUI applies IP-Adapter-FaceID** during generation
7. **Photos auto-deleted after 30 days** (embeddings kept forever)

## Backend Implementation

### 1. Face Embedding Service (`app/core/face_embedding_service.py`)

Uses InsightFace to extract 512-dimensional face embeddings:

```python
async def extract_face_embeddings(image_bytes: bytes) -> List[float]:
    # Validates photo (format, size, face detection)
    # Extracts 512-dim embedding using InsightFace Buffalo_L
    # Returns embedding array
```

**Key validations:**
- Image format: JPEG/PNG
- Max size: 5MB
- Min dimensions: 200x200px
- Exactly 1 face detected
- Face minimum size: 15% of image

### 2. Face Persona Storage

Face data stored in `Persona.ext` (JSONB field):

```python
{
  "is_face_based": True,
  "face_embeddings": [512 floats],  # Permanent
  "face_photo_url": "https://cloudflare...",  # 30-day retention
  "face_photo_uploaded_at": "2025-01-15T...",
  "body_type": "athletic"
}
```

### 3. Image Generation Integration

Face embeddings automatically passed to Runpod:

```python
# app/core/img_runpod.py
payload = {
    "input": {
        "prompt": "...",
        "negative_prompt": "...",
        "face_embeddings": [512 floats],  # Only if face-based persona
        "face_weight": 0.8  # Tunable (0.0-1.0)
    }
}
```

### 4. Photo Cleanup Job

Automatic cleanup runs daily:

```python
# app/core/photo_cleanup_job.py
# - Finds personas with photos >30 days old
# - Deletes from Cloudflare
# - Removes photo_url from database
# - Keeps embeddings intact
```

## Runpod ComfyUI Workflow Setup

### Required Nodes

1. **IP-Adapter-FaceID Node**
   - Download: [ComfyUI-IPAdapter-plus](https://github.com/cubiq/ComfyUI_IPAdapter_plus)
   - Install models:
     ```bash
     cd ComfyUI/models/ipadapter
     wget https://huggingface.co/h94/IP-Adapter-FaceID/resolve/main/ip-adapter-faceid_sdxl.bin
     ```

2. **InsightFace Model** (for face embedding input)
   ```bash
   cd ComfyUI/models/insightface
   # Model should match backend (Buffalo_L)
   wget https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip
   unzip buffalo_l.zip
   ```

### Workflow Configuration

1. **Add Input Node for Face Embeddings**
   ```json
   {
     "inputs": {
       "face_embeddings": "ARRAY",  # 512 floats
       "face_weight": "FLOAT"  # Default 0.8
     }
   }
   ```

2. **Connect IP-Adapter Node**
   - Input: Base SDXL model
   - Face embeddings: From input node
   - Weight: 0.7-0.9 (tunable)
   - Output: Conditioned model

3. **Face Weight Tuning**
   - `0.5-0.6`: Subtle face influence (more creative freedom)
   - `0.7-0.8`: **Recommended** balance
   - `0.9-1.0`: Maximum face similarity (may reduce quality)

### Example ComfyUI Workflow JSON

```json
{
  "nodes": {
    "1": {
      "class_type": "CheckpointLoaderSimple",
      "inputs": {
        "ckpt_name": "your_sdxl_model.safetensors"
      }
    },
    "2": {
      "class_type": "IPAdapterFaceID",
      "inputs": {
        "model": ["1", 0],
        "ipadapter": "ip-adapter-faceid_sdxl.bin",
        "face_embeds": ["INPUT_NODE", "face_embeddings"],
        "weight": ["INPUT_NODE", "face_weight"],
        "weight_type": "linear"
      }
    },
    "3": {
      "class_type": "KSampler",
      "inputs": {
        "model": ["2", 0],
        ...
      }
    }
  }
}
```

## Frontend Implementation

### Photo Upload Component (`miniapp/src/components/CreateFaceCharacter.jsx`)

Features:
- Photo upload (camera/gallery via Telegram Web App API)
- Client-side validation (format, size)
- Body type selector (slim, athletic, curvy, voluptuous)
- Character name input
- Real-time error handling

### Integration with Gallery

Special "Create Your Character" card shown first in persona gallery.

## API Endpoints

### Create Face Character

```http
POST /api/miniapp/create-face-character
Content-Type: application/json
X-Telegram-Init-Data: <telegram_web_app_data>

{
  "photo": "data:image/jpeg;base64,...",
  "character_name": "string",
  "body_type": "slim|athletic|curvy|voluptuous"
}

Response:
{
  "success": true,
  "persona_id": "uuid",
  "message": "Character created successfully"
}
```

### List Face Characters

```http
GET /api/miniapp/face-characters
X-Telegram-Init-Data: <telegram_web_app_data>

Response:
[
  {
    "id": "uuid",
    "name": "string",
    "body_type": "athletic",
    "face_photo_url": "https://...",
    "created_at": "2025-01-15T..."
  }
]
```

### Update Face Character

```http
PUT /api/miniapp/face-characters/{persona_id}
Content-Type: application/json

{
  "character_name": "New Name",  // optional
  "body_type": "curvy"  // optional
}
```

### Delete Face Character

```http
DELETE /api/miniapp/face-characters/{persona_id}
```

## Translation Keys

All UI text is localized in `config/ui_texts_*.yaml`:

```yaml
face_character:
  title: "Create Your Character"
  upload_photo: "Upload Photo"
  select_body: "Select Body Type"
  body_types:
    slim: "Slim"
    athletic: "Athletic"
    curvy: "Curvy"
    voluptuous: "Voluptuous"
  errors:
    no_face: "No face detected in photo"
    multiple_faces: "Multiple faces detected..."
    ...
```

## Troubleshooting

### No Face Detected

**Causes:**
- Poor lighting
- Face too small
- Face obscured
- Image quality too low

**Solutions:**
- Ask user to upload clearer photo
- Face should be at least 15% of image
- Good lighting and facing camera

### Face Not Consistent in Generated Images

**Causes:**
- Face weight too low
- Runpod workflow not configured correctly
- Face embeddings not being passed

**Solutions:**
1. Increase `face_weight` to 0.8-0.9
2. Verify Runpod payload includes `face_embeddings`
3. Check ComfyUI logs for IP-Adapter errors
4. Ensure InsightFace model matches (Buffalo_L)

### Cloudflare Upload Failures

**Causes:**
- API credentials not set
- Image too large
- Network issues

**Solutions:**
1. Check `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` in env
2. Validate image size on frontend (<5MB)
3. Implement retry logic (already in `cloudflare_upload.py`)

## Performance

- **Face embedding extraction:** ~500ms
- **Cloudflare upload:** ~300ms
- **Total character creation:** 2-3 seconds
- **Image generation:** Same as regular personas (no slowdown)
- **InsightFace model size:** ~300MB (cached in memory)

## Security

- **Authentication:** All API calls validated via Telegram Web App initData
- **Rate limiting:** 3 character creations per day per user (configurable)
- **Photo retention:** 30 days then auto-deleted (GDPR compliance)
- **Embeddings:** Never exposed in public APIs
- **Ownership:** Users can only manage their own face characters

## Database Schema

No schema changes required! Uses existing `Persona` table:

```sql
-- personas table (existing)
CREATE TABLE personas (
    id UUID PRIMARY KEY,
    owner_user_id BIGINT,  -- Set to user ID for private personas
    name VARCHAR(255),
    image_prompt TEXT,  -- Body type tags
    ext JSONB,  -- Stores face_embeddings, photo_url, etc.
    visibility VARCHAR(20) DEFAULT 'private',  -- Always 'private'
    ...
);
```

## Monitoring

Check logs for:
- `[FACE-EMBEDDING]` - Face extraction
- `[CREATE-FACE-CHARACTER]` - Character creation
- `[IMAGE-BG]` - Image generation with face
- `[PHOTO-CLEANUP]` - Daily cleanup job
- `[RUNPOD]` - Face embeddings in payload

## Future Improvements

1. **Multiple face photos** - Train custom LoRA from 10-20 photos
2. **Face angle variety** - Request multiple angles for better consistency
3. **Style transfer options** - Different anime styles (realistic, cartoon, etc.)
4. **Face editing** - Adjust facial features before generating
5. **Voice cloning** - Add voice to match the face (future feature)

## References

- [IP-Adapter-FaceID Paper](https://arxiv.org/abs/2311.15064)
- [InsightFace Documentation](https://github.com/deepinsight/insightface)
- [ComfyUI IP-Adapter Plus](https://github.com/cubiq/ComfyUI_IPAdapter_plus)
- [SDXL Model](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0)

---

**Last Updated:** January 2025
**Feature Status:** ✅ Production Ready (requires Runpod workflow setup)

