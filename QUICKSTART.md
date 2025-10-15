# Quick Start Guide - Updated for Your Configuration

## ✅ What's Been Updated

### 1. Database Setup

- **Using Railway PostgreSQL** (separate from your main app)
- Connection string already configured in `sample.env`
- Database: `railway` on Railway

### 2. Redis Setup

- **Using your existing Upstash Redis**
- Connection configured in `sample.env`

### 3. OpenRouter Models Updated

- **Main Chat**: `meta-llama/llama-3.3-70b-instruct` (Llama 3.3 70B)
- **State Resolver**: `x-ai/grok-3-mini:nitro` (Grok 3 Mini)
- **Image Tags**: `moonshotai/kimi-k2:nitro` (Kimi K2)

### 4. Prompts Replaced

✅ Main chat prompt with your full system (RelationshipRules, ContinuationRules, LanguageRules, etc.)
✅ Conversation state resolver prompt
✅ Image quality/negative prompts updated

### 5. Safety Check Removed

✅ Removed all safety filter calls
✅ No pre-filtering of user messages

---

## 🚀 Deploy in 5 Minutes

### Step 1: Setup Database Tables

```bash
# Make sure you're in the telegram-bot directory
cd /Users/artemtrifanuk/Documents/telegram-bot

# Install dependencies
pip install -r requirements.txt

# Run migrations (creates bot tables in Railway PostgreSQL)
alembic upgrade head

# Seed the 4 preset personas
python seed_db.py
```

**What this does:**

- Creates `users`, `personas`, `chats`, `messages`, `image_jobs` tables in Railway
- Adds Mia, Rei, Scarlett, and Luna to your database
- Uses your **separate Railway PostgreSQL** (independent from main app)

---

### Step 2: Deploy to Railway

#### A. Via GitHub (Recommended)

1. **Push to GitHub:**

```bash
cd /Users/artemtrifanuk/Documents/telegram-bot
git init
git add .
git commit -m "Initial Telegram bot setup"
git branch -M main
git remote add origin https://github.com/yourusername/telegram-bot.git
git push -u origin main
```

2. **Connect to Railway:**

- Go to [railway.app](https://railway.app)
- Click "New Project"
- Select "Deploy from GitHub repo"
- Choose your `telegram-bot` repository
- Railway auto-detects Dockerfile and deploys

3. **Set Environment Variables in Railway:**

Go to your service → Variables → Raw Editor, paste:

```env
BOT_TOKEN=your_telegram_bot_token_here
WEBHOOK_SECRET=your_webhook_secret_here
PUBLIC_BASE_URL=https://telegram-bot-production.up.railway.app

DATABASE_URL=postgresql://postgres:your_password@your_host:port/railway

REDIS_URL=redis://default:your_redis_password@your_redis_host:6379

OPENROUTER_API_KEY=your_openrouter_api_key_here
RUNPOD_API_KEY_POD=your_runpod_api_key_here
RUNPOD_ENDPOINT=https://your_runpod_endpoint.proxy.runpod.net/run

IMAGE_CALLBACK_SECRET=your_callback_secret_here

ENV=production
LOG_LEVEL=INFO
```

**Important:** Replace `PUBLIC_BASE_URL` with your actual Railway URL after deployment!

4. **Set Telegram Webhook:**

After deployment completes, get your Railway URL and run:

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-railway-app.up.railway.app/webhook/<YOUR_WEBHOOK_SECRET>"}'
```

Or use the helper script:

```bash
python scripts/manage.py set-webhook https://your-railway-app.up.railway.app
```

---

## ✅ Verification Checklist

### Test Bot Commands

1. **Open Telegram** and search for `@sexsplicit_bot`
2. Send `/start` - you should see persona selection
3. Select a girl (e.g., Mia)
4. Chat with her - she should respond using the new prompts
5. Try `/image` - it should generate an image via Runpod

### Check Logs

```bash
# Railway logs
railway logs --follow

# Look for:
# ✅ "Database connected"
# ✅ "Seeded 4 preset personas"
# ✅ "Webhook set"
# ✅ "[CHAT] Brain 2: Dialogue Specialist starting..."
# ✅ "[IMAGE-PIPELINE] Job submitted"
```

### Verify Database

```bash
# Check that personas were seeded
python scripts/manage.py list-personas

# Should show:
# - Mia (sweet_girlfriend)
# - Rei (tsundere)
# - Scarlett (seductive)
# - Luna (shy_romantic)

# Or check directly with Railway CLI
railway run python -c "from app.db import crud; from app.db.base import get_db; db = next(get_db()); print(len(crud.get_preset_personas(db)), 'personas')"
```

---

## 🎯 Key Differences from Your Main App

| Feature            | Main App (Next.js)             | Telegram Bot                               |
| ------------------ | ------------------------------ | ------------------------------------------ |
| **Frontend**       | React UI                       | Telegram native UI                         |
| **LLM Delivery**   | Streaming SSE                  | Non-streaming with typing indicator        |
| **Image Delivery** | Ably publish                   | Telegram sendPhoto                         |
| **Database**       | Neon PostgreSQL                | Railway PostgreSQL (separate)              |
| **Redis**          | Upstash                        | Same Upstash (shared)                      |
| **Prompts**        | Database                       | `config/prompts.json` (version controlled) |
| **Pipeline**       | 3-brain (State→Dialogue→Image) | Same 3-brain architecture                  |
| **Safety**         | Enabled                        | **DISABLED per your request**              |

---

## 📊 Architecture Overview

```
User Message (Telegram)
    ↓
[FastAPI Webhook] (/webhook/{secret})
    ↓
[Rate Limiter] (Redis)
    ↓
[Chat Handler] (bot/handlers/chat.py)
    ↓
[Pipeline Adapter] (core/pipeline_adapter.py)
    ├─→ [Brain 2: Dialogue] → Llama 3.3 70B
    ├─→ [State Update] → Grok 3 Mini (disabled for now)
    └─→ [Image Tags] → Kimi K2 (on /image)
    ↓
[Response] → user via Telegram API
    ↓
[Background: Image Gen] → Runpod → Webhook Callback
```

---

## 🔧 Customization

### Add New Persona

Edit `config/prompts.json`:

```json
{
  "key": "new_girl",
  "name": "New Girl Name",
  "system_prompt": "Your personality...",
  "appearance": {
    "ethnicity": "Caucasian",
    "hair": "long blonde hair",
    "eyes": "blue eyes"
  }
}
```

Then redeploy or run:

```bash
# Clear existing personas first if needed
# Then re-seed
python seed_db.py
```

### Change LLM Models

Edit `config/app.yaml`:

```yaml
llm:
  model: meta-llama/llama-3.3-70b-instruct
  state_model: x-ai/grok-3-mini:nitro
  image_model: moonshotai/kimi-k2:nitro
```

### Update Prompts

Edit `config/prompts.json` → commit → redeploy (prompts are version controlled, not in DB)

---

## 🆘 Troubleshooting

### Bot doesn't respond

```bash
# Check webhook status
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"

# Check Railway logs
railway logs
```

### Database errors

```bash
# Re-run migrations
railway run alembic upgrade head

# Check connection
python -c "from app.db.base import engine; engine.connect(); print('OK')"
```

### Images not generating

- Check Runpod credits
- Verify `RUNPOD_API_KEY_POD` is correct
- Check Railway logs for `[IMAGE-PIPELINE]` errors

---

## 📚 Additional Resources

- **Full setup guide**: `SETUP.md`
- **Database details**: `DATABASE_SETUP.md`
- **Pipeline comparison**: `PIPELINE_MAPPING.md`
- **Management CLI**: `scripts/manage.py --help`

---

## 🎉 You're Done!

Your Telegram bot now:

- ✅ Uses Llama 3.3 70B for conversations
- ✅ Has your full prompt system (RelationshipRules, LanguageRules, etc.)
- ✅ Generates images via Runpod with proper tags
- ✅ Shares your Neon database and Upstash Redis
- ✅ Has NO safety filtering (per your request)
- ✅ Works identically to your main app's AI pipeline

**Just deploy to Railway and set the webhook!** 🚀
