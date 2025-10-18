# Local Development Guide

## Verbose Logging for Local Testing

This project includes comprehensive verbose logging that can be enabled for local development and testing. The verbose logs include:

- **Full LLM prompts** (system, user, assistant messages)
- **Complete image generation prompts** (positive and negative)
- **Detailed pipeline execution steps**
- **Message batching details**
- **State transitions**
- **Error stack traces**

### How to Enable Verbose Logging

Set the `ENVIRONMENT` variable in your `.env` file:

```bash
ENVIRONMENT=development
```

Valid values for verbose mode:

- `development`
- `dev`
- `local`

For production (minimal logging):

- `production` (default)
- Or omit the variable entirely

### What You'll See in Development Mode

#### LLM Calls

```
[LLM] 🤖 Calling meta-llama/llama-3.3-70b-instruct (temp=0.8, max_tokens=512)
[LLM] 📊 Full request details:
[LLM]    Model: meta-llama/llama-3.3-70b-instruct
[LLM]    Temperature: 0.8
[LLM]    Max tokens: 512
[LLM] 💬 Messages (3 total):
[LLM]   [1] SYSTEM:
[LLM]       You are a helpful AI assistant...
[LLM]   [2] USER:
[LLM]       Hello, how are you?
[LLM] ✅ Response received (234 chars)
[LLM] 📝 Response preview: I'm doing great! How can I help you today?...
```

#### Image Generation

```
[IMAGE-BG] 🎨 Starting image generation for chat abc-123
[IMAGE-BG]    Chat ID: abc-123
[IMAGE-BG]    User ID: 12345
[IMAGE-BG]    Persona: Luna
[IMAGE-BG] 🧠 Brain 3: Generating image plan...
[IMAGE-BG] ✅ Image plan generated
[IMAGE-BG]    Composition tags: 5
[IMAGE-BG]    Action tags: 3
[IMAGE-BG]    Clothing tags: 2
[IMAGE-BG] ✅ Prompts assembled (pos: 456 chars, neg: 123 chars)
[IMAGE-BG]    Positive preview: 1girl, beautiful woman, red dress, smiling...
[IMAGE-BG]    Negative preview: ugly, deformed, blurry...
```

#### Pipeline Execution

```
[PIPELINE] ✅ Data fetched: 10 msgs, persona=Luna
[PIPELINE]    History: 10 messages
[PIPELINE]    Previous state: Found
[PIPELINE] 🧠 Brain 1: Resolving state...
[PIPELINE]    Input: 10 history messages + user message
[PIPELINE] ✅ Brain 1: State resolved (friend, cozy bedroom)
[PIPELINE]    Relationship: friend
[PIPELINE]    Emotions: happy, curious
[PIPELINE]    Location: cozy bedroom
[PIPELINE] 🧠 Brain 2: Generating dialogue...
[PIPELINE]    For message: Hey, how's it going?...
[PIPELINE] ✅ Brain 2: Dialogue generated (234 chars)
[PIPELINE]    Preview: Hey! I'm doing great! Just relaxing here. How about you?...
```

### Production Mode (Railway)

In production, logs are minimal and Railway-friendly:

```
[CHAT] 📨 Message from user 12345
[CHAT] 💬 Chat abc-123
[CHAT] 🚀 Processing 1 message(s)
[LLM] 🤖 Calling meta-llama/llama-3.3-70b-instruct (temp=0.8, max_tokens=512)
[LLM] ✅ Response received (234 chars)
[PIPELINE] 🧠 Brain 1: Resolving state...
[PIPELINE] ✅ Brain 1: State resolved (friend, cozy bedroom)
[PIPELINE] 🧠 Brain 2: Generating dialogue...
[PIPELINE] ✅ Brain 2: Dialogue generated (234 chars)
[PIPELINE] ✅ Response sent to user
[IMAGE-BG] 🎨 Starting image generation for chat abc-123
[IMAGE-BG] ✅ Image generation task complete
```

### Testing Locally

1. **Create `.env` file from `sample.env`:**

   ```bash
   cp sample.env .env
   ```

2. **Enable development mode:**

   ```bash
   # Edit .env
   ENVIRONMENT=development
   ```

3. **Run the bot:**

   ```bash
   uvicorn app.main:app --reload --port 8080
   ```

4. **Test with Telegram:**
   - Use ngrok or similar to expose your local server
   - Update `PUBLIC_BASE_URL` in `.env` to your ngrok URL
   - Send messages to your bot and watch the detailed logs

### Tips

- **Full prompts can be very long** - verbose logging is designed for local development only
- **Railway has log size limits** - always use `ENVIRONMENT=production` on Railway
- **Search logs easily** - each component has a unique prefix (`[LLM]`, `[PIPELINE]`, `[CHAT]`, `[IMAGE-BG]`, `[RUNPOD]`)
- **Debug specific issues** - use `log_verbose()` to add your own debug statements that only show in development

### Adding Custom Debug Logs

```python
from app.core.logging_utils import log_verbose, log_always

# Always logged (both dev and prod)
log_always(f"[MY-MODULE] Important event happened")

# Only in development mode
log_verbose(f"[MY-MODULE] Debug info: {some_variable}")
log_verbose(f"[MY-MODULE]    Detail 1: {detail}")
log_verbose(f"[MY-MODULE]    Detail 2: {another_detail}")
```

### Environment Detection

The `is_development()` function checks the `ENVIRONMENT` variable:

```python
from app.core.logging_utils import is_development

if is_development():
    # Do something only in dev mode
    import traceback
    traceback.print_exc()
```

