# AI Telegram Companion Bot

A production-ready Telegram bot featuring AI-powered conversations with customizable personas, powered by OpenRouter LLM and Runpod image generation. Mirrors the Sexsplicit AI pipeline architecture.

## 🌟 Features

- **Multiple AI Personas**: Choose from preset personalities or create your own
- **Smart Conversations**: Context-aware AI responses with emotional continuity
- **Image Generation**: AI-generated images via Runpod with webhook callbacks
- **Rate Limiting**: Redis-based rate limiting for text and images
- **Safety Filters**: Content safety checks for user messages
- **Typing Indicators**: Non-blocking typing/upload_photo actions
- **State Management**: Conversation state tracking (location, emotions, relationship progression)
- **Production Ready**: Webhook-based, idempotent callbacks, comprehensive error handling

## 📋 Tech Stack

- **Bot Framework**: aiogram 3.x (async Telegram bot)
- **Web Server**: FastAPI + Uvicorn
- **Database**: PostgreSQL (Railway) + SQLAlchemy + Alembic
- **Cache**: Redis (Railway) for rate limiting
- **LLM**: OpenRouter (Claude 3.5 Sonnet)
- **Images**: Runpod SDXL with webhook callbacks
- **Deployment**: Railway (Docker)

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL database
- Redis instance
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- OpenRouter API Key
- Runpod API Key

### Local Development

1. **Clone the repository**

```bash
cd telegram-bot
```

2. **Install dependencies**

```bash
pip install -r requirements.txt
```

3. **Set environment variables**

Create `.env` file:

```env
BOT_TOKEN=your_telegram_bot_token
WEBHOOK_SECRET=random_secret_string
PUBLIC_BASE_URL=https://your-app.railway.app

DATABASE_URL=postgresql://user:pass@host:5432/dbname
REDIS_URL=redis://host:6379

OPENROUTER_API_KEY=your_openrouter_key
RUNPOD_API_KEY_POD=your_runpod_key
RUNPOD_ENDPOINT=https://aa9yxd4ap6p47w-8000.proxy.runpod.net/run

IMAGE_CALLBACK_SECRET=another_random_secret

ENV=development
LOG_LEVEL=INFO

# Optional: Feature flags for local testing
ENABLE_BOT=False        # Disable bot to prevent dual responses
ENABLE_FOLLOWUPS=False  # Disable auto follow-up messages
ENABLE_IMAGES_IN_FOLLOWUP=False  # Disable images in auto follow-ups
```

> **💡 Tip for Local Development**: When testing APIs (analytics, miniapp) locally while your production bot is running, set `ENABLE_BOT=False` to prevent your local instance from responding to user messages. This avoids users getting duplicate responses from both your server and local machine.

4. **Run database migrations**

```bash
alembic upgrade head
```

5. **Start the bot**

```bash
uvicorn app.main:app --reload --port 8080
```

6. **Set webhook (for production)**

```bash
curl -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{\"url\": \"${PUBLIC_BASE_URL}/webhook/${WEBHOOK_SECRET}\"}"
```

## 🏗️ Project Structure

```
telegram-bot/
├── app/
│   ├── main.py                      # FastAPI app + webhook endpoints
│   ├── settings.py                  # Configuration loader
│   ├── bot/
│   │   ├── loader.py                # Bot & Dispatcher initialization
│   │   ├── keyboards/
│   │   │   └── inline.py            # Inline keyboards
│   │   └── handlers/
│   │       ├── start.py             # /start + persona selection
│   │       ├── chat.py              # Text conversation handler
│   │       ├── image.py             # Image generation handler
│   │       └── settings.py          # Settings commands
│   ├── core/
│   │   ├── pipeline_adapter.py      # Sexsplicit pipeline mirror
│   │   ├── llm_openrouter.py        # OpenRouter LLM client
│   │   ├── img_runpod.py            # Runpod image client
│   │   ├── actions.py               # Typing indicators
│   │   ├── rate.py                  # Redis rate limiter
│   │   └── security.py              # HMAC verification
│   └── db/
│       ├── base.py                  # Database session
│       ├── models.py                # SQLAlchemy models
│       ├── crud.py                  # CRUD operations
│       └── migrations/              # Alembic migrations
├── config/
│   ├── app.yaml                     # App configuration
│   └── prompts.json                 # All prompts & personas
├── Dockerfile
├── railway.toml
├── requirements.txt
└── alembic.ini
```

## ⚙️ Configuration

### Environment Variables

#### Feature Flags

- **`ENABLE_BOT`** (default: `True`)  
  Set to `False` to disable the Telegram bot entirely. The FastAPI server will still run, allowing you to test analytics dashboard and miniapp APIs without the bot responding to messages. Useful for local development when production bot is running.

- **`ENABLE_FOLLOWUPS`** (default: `True`)  
  Set to `False` to disable automatic follow-up messages (30-minute and 24-hour re-engagement messages). Energy regeneration still runs.

- **`ENABLE_IMAGES_IN_FOLLOWUP`** (default: `False`)  
  Set to `True` to enable image generation during auto follow-up messages. Disabled by default to save resources and reduce costs, as follow-ups are frequent and images may not be necessary for re-engagement.

- **`FOLLOWUP_TEST_USERS`** (default: `None`)  
  Comma-separated list of Telegram user IDs to restrict followups to (e.g., `"123456,789012"`). When set, only these users will receive automatic follow-up messages. Useful for testing followups in development/staging without affecting all users. Leave unset in production to enable followups for all users.

### app.yaml

All non-prompt settings (model params, limits, image settings):

```yaml
llm:
  model: openrouter/anthropic/claude-3.5-sonnet
  temperature: 0.7
  max_tokens: 512

image:
  width: 832
  height: 1216
  steps: 32
  cfg_scale: 5.5

limits:
  text_per_min: 20
  image_per_min: 5
  max_history_messages: 12
```

### prompts.json

All prompts, personas, and text blocks:

```json
{
  "system": {
    "default": "You are {{persona_name}}...",
    "safety_guard": "REFUSE any content involving..."
  },
  "personas": [
    {
      "key": "sweet_girlfriend",
      "name": "Mia",
      "system_prompt": "You are Mia, warm and playful...",
      "style": {"temperature": 0.8},
      "appearance": {...}
    }
  ]
}
```

## 🎯 Pipeline Architecture

The bot replicates the Sexsplicit AI pipeline with these components:

### 1. **State Resolver** (Brain 1)

- Tracks conversation state (emotions, location, clothing, relationship stage)
- Updates state based on user/AI interactions
- Fallback to previous valid state if update fails

### 2. **Dialogue Specialist** (Brain 2)

- Generates natural AI responses
- Context-aware with recent message history
- Persona-specific temperature and tone

### 3. **Image Pipeline** (Brain 3 + Runpod)

- Prompt engineering with SDXL tags
- Dynamic negative prompts with scene context detection
- Webhook callback for async image delivery
- HMAC signature verification for security

## 🤖 Bot Commands

- `/start` - Start the bot and choose an AI girl
- `/girls` - Browse and switch personas
- `/image` - Generate an image with your current girl
- `/reset` - Clear conversation history
- `/settings` - Adjust preferences
- `/help` - Show help message

## 📦 Deployment to Railway

1. **Connect GitHub repository** to Railway

2. **Add PostgreSQL** and **Redis** services

3. **Set environment variables** in Railway dashboard:

   - All variables from `.env` file
   - `PORT` is auto-set by Railway

4. **Deploy**:

```bash
git push origin main
```

5. **Run migrations** (one-time):

```bash
railway run alembic upgrade head
```

6. **Set Telegram webhook**:

```bash
curl -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
  -d "url=${PUBLIC_BASE_URL}/webhook/${WEBHOOK_SECRET}"
```

## 🔒 Security

- **Webhook Secret**: Telegram webhook path protected by secret token
- **HMAC Signatures**: Image callbacks verified with HMAC-SHA256
- **Rate Limiting**: Redis-based sliding window rate limits
- **Safety Filters**: Content filtering for prohibited topics
- **SQL Injection**: Parameterized queries via SQLAlchemy

## 🧪 Testing

### Test Webhook Locally (ngrok)

```bash
# Start ngrok
ngrok http 8080

# Set webhook to ngrok URL
curl -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
  -d "url=https://your-ngrok-url.ngrok.io/webhook/${WEBHOOK_SECRET}"

  curl -X POST "https://api.telegram.org/bot8266552305:AAHqT32CMUyH7ahgPe1kGK06RxwNEnjlIA8/setWebhook" \
  -d "url=https://984e5f4a7c0c.ngrok-free.app/webhook/m1RJyAvMKf8Vgyf_DLe7vcqP22wj2z5XecJV5zxVQqg"
```

### Test Image Callback

```bash
curl -X POST "http://localhost:8080/image/callback?job_id=test-uuid&sig=valid_hmac" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "COMPLETED",
    "output": {
      "images": ["https://example.com/image.jpg"]
    }
  }'
```

## 📊 Monitoring

- **Health Check**: `GET /health`
- **Logs**: Check Railway logs for `[CHAT]`, `[IMAGE]`, `[WEBHOOK]` tags
- **Database**: Monitor active chats and image jobs

## 🛠️ Development

### Add New Persona

1. Edit `config/prompts.json`:

```json
{
  "key": "new_persona",
  "name": "Name",
  "system_prompt": "...",
  "appearance": {...}
}
```

2. Restart bot to seed new persona to database

### Customize Pipeline Logic

Edit `app/core/pipeline_adapter.py` to modify:

- State update logic
- Prompt assembly
- Image prompt engineering
- Safety filters

## 📝 API Reference

### Telegram Webhook

```
POST /webhook/{WEBHOOK_SECRET}
Body: Telegram Update JSON
```

### Image Callback

```
POST /image/callback?job_id={UUID}&sig={HMAC}
Body: {
  "status": "COMPLETED|FAILED|IN_PROGRESS",
  "output": {"images": ["url"]},
  "error": "optional"
}
```

## 🤝 Contributing

This is a private implementation. For changes, contact the repository owner.

## 📄 License

Proprietary - All Rights Reserved

## 🙏 Acknowledgments

- Pipeline architecture based on Sexsplicit AI platform
- Powered by OpenRouter (Anthropic Claude)
- Image generation by Runpod SDXL

---

**Built with ❤️ for immersive AI companionship**
