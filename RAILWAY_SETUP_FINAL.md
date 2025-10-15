# Railway Setup - Final Configuration

## ✅ What's Configured

### Database: Railway PostgreSQL
- **Host**: `your_railway_host:port`
- **Database**: `railway`
- **User**: `postgres`
- **Password**: `your_railway_db_password`

**Connection String** (already in `sample.env`):
```
postgresql://postgres:your_password@your_host:port/railway
```

✅ **Separate from your main app** - independent database for Telegram bot only

---

## 🚀 Quick Deploy (3 Steps)

### Step 1: Setup Database

```bash
# Run migrations (creates tables)
alembic upgrade head

# Seed personas (adds Mia, Rei, Scarlett, Luna)
python seed_db.py
```

**Expected output:**
```
🌱 Starting database seeding...

📝 Creating 4 preset personas...
  ✓ Created: Mia (sweet_girlfriend)
  ✓ Created: Rei (tsundere)
  ✓ Created: Scarlett (seductive)
  ✓ Created: Luna (shy_romantic)

✅ Successfully seeded 4 preset personas!
🎉 Database seeding complete!
```

---

### Step 2: Deploy to Railway

```bash
# Push to Railway
git init
git add .
git commit -m "Initial commit"

# Deploy (Railway auto-detects Dockerfile)
railway up
```

**Railway Environment Variables** (set in dashboard):
```env
BOT_TOKEN=your_telegram_bot_token_here
WEBHOOK_SECRET=your_webhook_secret_here
PUBLIC_BASE_URL=https://your-app-name.up.railway.app
DATABASE_URL=postgresql://postgres:your_password@your_host:port/railway
REDIS_URL=redis://default:your_redis_password@your_redis_host:6379
OPENROUTER_API_KEY=your_openrouter_api_key_here
RUNPOD_API_KEY_POD=your_runpod_api_key_here
IMAGE_CALLBACK_SECRET=your_callback_secret_here
ENV=production
LOG_LEVEL=INFO
```

---

### Step 3: Set Telegram Webhook

```bash
# After Railway deployment completes
python scripts/manage.py set-webhook https://your-app-name.up.railway.app
```

Or manually:
```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -d "url=https://your-app-name.up.railway.app/webhook/<YOUR_WEBHOOK_SECRET>"
```

---

## ✅ Verify Everything Works

### 1. Check Database

```bash
railway run python -c "from app.db.base import engine; engine.connect(); print('✅ DB connected')"
```

### 2. Check Personas

```bash
python scripts/manage.py list-personas
```

Should show 4 personas: Mia, Rei, Scarlett, Luna

### 3. Test Bot

Open Telegram → search `@sexsplicit_bot` → send `/start`

You should see:
- Welcome message
- 4 persona buttons
- "Create Your Own Girl" button

### 4. Test Chat

- Select a persona (e.g., Mia)
- Send a message
- Bot should respond with your new prompts

### 5. Test Image

- Send `/image`
- Choose prompt type
- Image should generate via Runpod

---

## 🔍 What Changed from Original Plan

| Original Plan | Final Implementation |
|---------------|---------------------|
| Use Neon database from main app | ✅ Use **separate Railway PostgreSQL** |
| Auto-seed on startup | ✅ Manual seed via `python seed_db.py` |
| Local database testing | ✅ **Railway-only** (no local setup) |

---

## 📊 Architecture

```
Telegram User
    ↓
[Telegram API]
    ↓
[Railway App] (FastAPI webhook)
    ↓
├── [Railway PostgreSQL] (bot data)
│   ├── users
│   ├── personas (Mia, Rei, Scarlett, Luna)
│   ├── chats
│   ├── messages
│   └── image_jobs
│
├── [Upstash Redis] (rate limiting) - SHARED with main app
│
├── [OpenRouter] (LLM)
│   ├── Llama 3.3 70B (chat)
│   ├── Grok 3 Mini (state)
│   └── Kimi K2 (image tags)
│
└── [Runpod] (image generation)
```

---

## 🛠️ Maintenance Commands

### Re-seed Database

```bash
# Delete existing personas first (optional)
railway run psql $DATABASE_URL -c "DELETE FROM personas WHERE is_preset = true;"

# Re-seed
python seed_db.py
```

### Check Database Stats

```bash
railway run psql $DATABASE_URL -c "SELECT COUNT(*) as users FROM users;"
railway run psql $DATABASE_URL -c "SELECT COUNT(*) as chats FROM chats;"
railway run psql $DATABASE_URL -c "SELECT COUNT(*) as messages FROM messages;"
```

### View Logs

```bash
railway logs --follow
```

### Update Environment Variables

```bash
railway variables set KEY=VALUE
```

---

## 🔐 Security Notes

- ✅ Railway PostgreSQL credentials are in `sample.env` (don't commit to public repo)
- ✅ Webhook secret `Q3wgbkzLsH` protects Telegram webhook
- ✅ Image callback secret (same) protects Runpod callbacks
- ✅ Bot token is private to your account

---

## 📝 Files Modified for Railway Setup

| File | Change |
|------|--------|
| `sample.env` | Updated DATABASE_URL to Railway PostgreSQL |
| `app/main.py` | Removed auto-seeding from startup |
| `seed_db.py` | Created standalone seeding script |
| `DATABASE_SETUP.md` | Updated to Railway-only guide |
| `QUICKSTART.md` | Updated deploy steps for Railway |
| `CHANGES_SUMMARY.md` | Updated database info |

---

## ✅ Checklist

Before going live:

- [ ] Railway PostgreSQL service created
- [ ] `alembic upgrade head` completed successfully
- [ ] `python seed_db.py` completed (4 personas created)
- [ ] Railway app deployed
- [ ] Environment variables set in Railway dashboard
- [ ] Telegram webhook set
- [ ] Tested `/start` command
- [ ] Tested chatting with a persona
- [ ] Tested `/image` command

---

## 🎉 You're Ready!

Your Telegram bot is configured with:
- ✅ Separate Railway PostgreSQL database
- ✅ Llama 3.3 70B for conversations
- ✅ Your exact prompts (RelationshipRules, LanguageRules, etc.)
- ✅ No safety filtering
- ✅ Runpod image generation
- ✅ Upstash Redis (shared with main app)

**Deploy to Railway and test!** 🚀

