# Verbose Logging Implementation

## Summary

Added environment-based verbose logging that provides comprehensive debugging information for local development while keeping production logs minimal for Railway.

## Changes Made

### 1. New Logging Utility (`app/core/logging_utils.py`)

Created a centralized logging utility with three functions:

- `is_development()` - Checks if `ENVIRONMENT` env var is set to `development`, `dev`, or `local`
- `log_verbose()` - Logs only in development mode
- `log_always()` - Logs in all environments

### 2. Updated Files with Verbose Logging

#### `app/core/llm_openrouter.py`

- Full LLM request details (model, temperature, max tokens)
- Complete message history (system, user, assistant)
- Response previews
- Only basic info shown in production

#### `app/core/img_runpod.py`

- Full positive and negative prompts (in development)
- Prompt length and previews
- Detailed error tracebacks in development
- RunPod API response details

#### `app/core/multi_brain_pipeline.py`

- Detailed pipeline stage execution
- State transition details (relationship, emotions, location)
- Dialogue generation context
- Image plan breakdown (composition, action, clothing tags)
- Full prompt previews for image generation
- Processing lock status
- Database save operations
- Error tracebacks in development

#### `app/bot/handlers/chat.py`

- Message reception details (user ID, text preview)
- Rate limit checks
- Chat lookup and persona information
- Message batching status
- Timeout detection
- Unprocessed message counts
- Pipeline call status

### 3. Environment Configuration

Updated `sample.env` with:

```bash
# Logging Mode (for local development)
# Set to "development", "dev", or "local" for verbose logging
# Set to "production" or omit for minimal logging (Railway-friendly)
ENVIRONMENT=production
```

### 4. Documentation

Created `LOCAL_DEVELOPMENT.md` with:

- How to enable verbose logging
- Example log outputs
- Testing instructions
- Tips for adding custom debug logs

## Usage

### For Local Development:

```bash
# In .env file
ENVIRONMENT=development
```

### For Production (Railway):

```bash
# In .env file
ENVIRONMENT=production
# Or omit entirely
```

## Benefits

✅ **Development:**

- See full prompts sent to LLMs
- Debug image generation with full positive/negative prompts
- Track message batching behavior
- Understand pipeline execution flow
- Full error stack traces

✅ **Production:**

- Minimal, clean logs
- Railway-friendly (no massive log output)
- Essential information only
- Lower costs

✅ **Code Quality:**

- Easy to add conditional debugging
- Consistent logging format across modules
- No need to comment/uncomment debug code
- Clean separation of concerns

## Log Prefixes

- `[LLM]` - OpenRouter API calls
- `[PIPELINE]` - Multi-brain pipeline orchestration
- `[IMAGE-BG]` - Background image generation
- `[RUNPOD]` - RunPod API calls
- `[CHAT]` - Message handler
- `[STATE-RESOLVER]` - Brain 1 (state resolution)
- `[DIALOGUE]` - Brain 2 (dialogue generation)
- `[IMAGE-PLAN]` - Brain 3 (image planning)

## Example: Development vs Production

### Development Mode (`ENVIRONMENT=development`):

```
[CHAT] 📨 Message from user 12345
[CHAT]    Text (15 chars): Hey, how are you?
[CHAT] ✅ Rate limit passed (3 messages)
[CHAT] 👤 Getting/creating user 12345
[CHAT] 💬 Getting active chat for TG chat 67890
[CHAT] 💬 Chat abc-123
[CHAT]    Persona: persona-456
[CHAT] 🔍 Checking for existing unprocessed messages
[CHAT] 📊 Found 0 existing unprocessed message(s)
[CHAT] 💾 Saving current message as unprocessed
[CHAT] 📦 Prepared 1 message(s) for processing
[CHAT] 🚀 Processing 1 message(s)
[CHAT] 📝 Batched text: Hey, how are you?
[CHAT] 🧠 Calling multi-brain pipeline...
[PIPELINE] ✅ Data fetched: 5 msgs, persona=Luna
[PIPELINE]    History: 5 messages
[PIPELINE]    Previous state: Found
[PIPELINE] 🧠 Brain 1: Resolving state...
[LLM] 🤖 Calling x-ai/grok-3-mini:nitro (temp=0.3, max_tokens=500)
[LLM] 📊 Full request details:
[LLM]    Model: x-ai/grok-3-mini:nitro
[LLM]    Temperature: 0.3
[LLM]    Max tokens: 500
[LLM] 💬 Messages (2 total):
[LLM]   [1] SYSTEM:
[LLM]       You are an AI conversation state tracker...
[LLM]   [2] USER:
[LLM]       Last user message: Hey, how are you?
[LLM] ✅ Response received (234 chars)
[LLM] 📝 Response preview: {"rel":{"relationshipStage":"friend"...
```

### Production Mode (`ENVIRONMENT=production`):

```
[CHAT] 📨 Message from user 12345
[CHAT] 💬 Chat abc-123
[CHAT] 🚀 Processing 1 message(s)
[PIPELINE] ✅ Data fetched: 5 msgs, persona=Luna
[PIPELINE] 🧠 Brain 1: Resolving state...
[LLM] 🤖 Calling x-ai/grok-3-mini:nitro (temp=0.3, max_tokens=500)
[LLM] ✅ Response received (234 chars)
[PIPELINE] ✅ Brain 1: State resolved (friend, cozy bedroom)
[PIPELINE] 🧠 Brain 2: Generating dialogue...
[LLM] 🤖 Calling meta-llama/llama-3.3-70b-instruct (temp=0.8, max_tokens=512)
[LLM] ✅ Response received (156 chars)
[PIPELINE] ✅ Brain 2: Dialogue generated (156 chars)
[PIPELINE] ✅ Response sent to user
[PIPELINE] 🎨 Starting background image generation...
[IMAGE-BG] 🎨 Starting image generation for chat abc-123
[IMAGE-BG] 🧠 Brain 3: Generating image plan...
[IMAGE-BG] ✅ Prompts assembled (pos: 456 chars, neg: 123 chars)
[RUNPOD] 🚀 Dispatching job job-789
[RUNPOD] ✅ Job dispatched successfully
[IMAGE-BG] ✅ Image generation task complete
```

## Implementation Details

The verbose logging is implemented using a simple conditional check:

```python
from app.core.logging_utils import log_verbose, log_always

# Always shown (production and development)
log_always(f"[MODULE] Important event")

# Only shown in development
log_verbose(f"[MODULE] Detailed debug info")
```

The `ENVIRONMENT` variable is checked once per function call, so there's minimal performance overhead.

