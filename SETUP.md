# Setup Guide

Complete step-by-step guide to get your AI Telegram bot running from scratch.

## 🎯 Prerequisites Checklist

- [ ] Python 3.11+ installed
- [ ] Git installed
- [ ] Railway account (or other cloud platform)
- [ ] Telegram account

## 📝 Step 1: Create Telegram Bot

1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Send `/newbot` command
3. Choose a name (e.g., "My AI Companion")
4. Choose a username (e.g., "my_ai_companion_bot")
5. Copy the bot token - you'll need this for `BOT_TOKEN`

## 🗄️ Step 2: Setup Database & Redis (Railway)

### Create Railway Project

1. Go to [railway.app](https://railway.app)
2. Sign up / Login with GitHub
3. Click "New Project"
4. Select "Deploy PostgreSQL"
5. Wait for deployment

### Get PostgreSQL Connection String

1. Click on your PostgreSQL service
2. Go to "Connect" tab
3. Copy "Postgres Connection URL" - this is your `DATABASE_URL`

### Add Redis

1. In same project, click "New"
2. Select "Deploy Redis"
3. Wait for deployment
4. Go to "Connect" tab
5. Copy "Redis Connection URL" - this is your `REDIS_URL`

## 🔑 Step 3: Get API Keys

### OpenRouter (LLM)

1. Go to [openrouter.ai](https://openrouter.ai)
2. Sign up / Login
3. Go to [Keys](https://openrouter.ai/keys)
4. Create a new API key
5. Copy it - this is your `OPENROUTER_API_KEY`
6. Add credits to your account

### Runpod (Image Generation)

1. Go to [runpod.io](https://runpod.io)
2. Sign up / Login
3. Go to Settings → API Keys
4. Create a new API key
5. Copy it - this is your `RUNPOD_API_KEY_POD`
6. Make sure you have your Runpod endpoint URL - this is `RUNPOD_ENDPOINT`

## 🚀 Step 4: Deploy to Railway

### Option A: Deploy via GitHub (Recommended)

1. Fork or clone this repository to your GitHub
2. In Railway, click "New" → "GitHub Repo"
3. Select your repository
4. Railway will auto-detect Dockerfile and deploy

### Option B: Deploy via Railway CLI

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Link to project
railway link

# Deploy
railway up
```

## ⚙️ Step 5: Configure Environment Variables

In Railway dashboard:

1. Click on your service
2. Go to "Variables" tab
3. Add all variables from `sample.env`:

```env
BOT_TOKEN=<from BotFather>
WEBHOOK_SECRET=<generate random string, e.g., use: openssl rand -hex 32>
PUBLIC_BASE_URL=<your Railway app URL, e.g., https://telegram-bot-production.up.railway.app>

DATABASE_URL=<from Railway PostgreSQL>
REDIS_URL=<from Railway Redis>

OPENROUTER_API_KEY=<from OpenRouter>
RUNPOD_API_KEY_POD=<from Runpod>
RUNPOD_ENDPOINT=https://aa9yxd4ap6p47w-8000.proxy.runpod.net/run

IMAGE_CALLBACK_SECRET=<generate another random string>

ENV=production
LOG_LEVEL=INFO
```

4. Click "Save"
5. Service will automatically redeploy

## 🔗 Step 6: Set Telegram Webhook

After deployment completes:

1. Get your app URL from Railway (e.g., `https://telegram-bot-production.up.railway.app`)
2. Run this command (replace variables):

```bash
curl -X POST "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{\"url\": \"<PUBLIC_BASE_URL>/webhook/<WEBHOOK_SECRET>\"}"
```

Example:

```bash
curl -X POST "https://api.telegram.org/bot123456:ABC-DEF.../setWebhook" \
  -H "Content-Type: application/json" \
  -d "{\"url\": \"https://telegram-bot-production.up.railway.app/webhook/my-secret-123\"}"
```

You should see:

```json
{ "ok": true, "result": true, "description": "Webhook was set" }
```

## ✅ Step 7: Test Your Bot

1. Open Telegram
2. Search for your bot username (e.g., @my_ai_companion_bot)
3. Send `/start`
4. You should see the welcome message with persona selection!
5. Try chatting with an AI girl
6. Try generating an image with `/image`

## 🐛 Troubleshooting

### Bot doesn't respond

1. **Check webhook status:**

```bash
curl "https://api.telegram.org/bot<BOT_TOKEN>/getWebhookInfo"
```

2. **Check Railway logs:**

   - Go to Railway dashboard
   - Click on your service
   - Go to "Deployments" → Latest deployment → "View Logs"
   - Look for errors

3. **Check database connection:**

```bash
railway run python -c "from app.db.base import engine; engine.connect()"
```

### Images not generating

1. **Check Runpod credits/availability**
2. **Verify image callback secret matches**
3. **Check Railway logs for `[IMAGE]` and `[IMAGE-CALLBACK]` tags**
4. **Manually test callback:**

```bash
curl -X POST "https://your-app.railway.app/image/callback?job_id=test&sig=<valid_sig>" \
  -d '{"status":"COMPLETED","output":{"images":["https://via.placeholder.com/832x1216"]}}'
```

### Rate limits hit immediately

1. Check Redis connection
2. Verify Redis is running in Railway
3. Check logs for Redis connection errors

### Database errors

1. **Run migrations:**

```bash
railway run alembic upgrade head
```

2. **Check DATABASE_URL format:**
   - Should start with `postgresql://` (not `postgres://`)
   - If Railway gives you `postgres://`, change it to `postgresql://`

## 🔄 Updating Your Bot

When you make changes:

### Via GitHub (if connected)

```bash
git add .
git commit -m "Update bot"
git push origin main
```

Railway will auto-deploy.

### Via Railway CLI

```bash
railway up
```

### Manual Redeploy

In Railway dashboard, click "Deploy" → "Redeploy"

## 📊 Monitoring

### Health Check

```bash
curl https://your-app.railway.app/health
```

Should return:

```json
{ "status": "healthy" }
```

### View Logs

```bash
railway logs
```

### Database Stats

```bash
railway run python -c "from app.db.base import get_db; from app.db import crud; db = next(get_db()); print(f'Users: {len(crud.get_or_create_user(db, 1))}'); "
```

## 💡 Tips

1. **Use meaningful correlation IDs**: All logs include request IDs for tracing
2. **Monitor OpenRouter usage**: Check your usage at openrouter.ai/activity
3. **Monitor Runpod credits**: Check runpod.io dashboard
4. **Backup database**: Railway provides automatic backups
5. **Rate limits**: Adjust in `config/app.yaml` if needed

## 🆘 Need Help?

Common issues and solutions:

| Issue                        | Solution                                           |
| ---------------------------- | -------------------------------------------------- |
| "Webhook not set"            | Run webhook command again with correct URL         |
| "Database connection failed" | Check DATABASE_URL format (postgresql vs postgres) |
| "OpenRouter 401"             | Verify API key is correct and has credits          |
| "Redis timeout"              | Check REDIS_URL and that Redis service is running  |
| "Image not delivered"        | Check webhook signature and callback logs          |

## 🎉 Success!

If everything works:

- ✅ Bot responds to /start
- ✅ Can chat with AI girls
- ✅ Images generate and deliver
- ✅ Rate limits work
- ✅ Conversation state persists

You're all set! Enjoy your AI companion bot. 🤖💕

