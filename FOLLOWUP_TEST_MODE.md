# Followup Test Mode

## Problem
When testing followup messages with a different bot token (test/development), enabling `ENABLE_FOLLOWUPS=True` would send followups to **all users in the database**, including production users, causing unwanted messages.

## Solution
A new **user whitelist** feature allows you to restrict followup messages to specific Telegram user IDs during testing.

## How to Test Followups Safely

### 1. Find Your Telegram User ID

You can get your Telegram user ID by:
- Messaging [@userinfobot](https://t.me/userinfobot) on Telegram
- Or using [@get_id_bot](https://t.me/get_id_bot)
- Or checking your database: `SELECT id FROM users WHERE username = 'your_username';`

### 2. Set the Environment Variable

Add this to your `.env` file:

```bash
# Enable followups
ENABLE_FOLLOWUPS=True

# Restrict to your test user(s) only
FOLLOWUP_TEST_USERS=123456789

# Or multiple users (comma-separated)
FOLLOWUP_TEST_USERS=123456789,987654321
```

### 3. Testing

With this configuration:
- ✅ Followups will **only** be sent to the user IDs you specified
- ✅ All other users in the database will be **ignored** by the followup scheduler
- ✅ You can safely test with your test bot token without affecting real users

### 4. Production Deployment

For production, either:
- **Option A**: Remove or comment out `FOLLOWUP_TEST_USERS` entirely:
  ```bash
  # FOLLOWUP_TEST_USERS=
  ```

- **Option B**: Leave the variable unset in your Railway/production environment

When `FOLLOWUP_TEST_USERS` is not set, followups work normally for all users.

## How It Works

The scheduler now checks for the whitelist on every run:

```
[SCHEDULER] Checking for inactive chats (30min)...
[SCHEDULER] 🧪 Test mode: Followups restricted to user IDs: [123456789]
[SCHEDULER] Found 1 inactive chats (30min)
```

The database queries filter by user ID, so only whitelisted users are considered for followups.

## Feature Flags Summary

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_FOLLOWUPS` | `True` | Enable/disable followup system entirely |
| `ENABLE_IMAGES_IN_FOLLOWUP` | `False` | Generate images in followup messages |
| `FOLLOWUP_TEST_USERS` | `None` | Restrict followups to specific user IDs (testing) |

## Example Testing Workflow

```bash
# 1. Copy env.local.example to .env
cp env.local.example .env

# 2. Edit .env
nano .env

# 3. Add your settings
ENABLE_BOT=True
ENABLE_FOLLOWUPS=True
FOLLOWUP_TEST_USERS=YOUR_TELEGRAM_ID_HERE

# 4. Start your test bot
python -m app.main

# 5. Chat with your bot, then wait 30+ minutes
# You should receive a followup message

# 6. Check logs
[SCHEDULER] 🧪 Test mode: Followups restricted to user IDs: [YOUR_ID]
[SCHEDULER] Found 1 inactive chats (30min)
[SCHEDULER] ✅ Auto-follow-up sent successfully
```

## Files Modified

- `app/settings.py` - Added `FOLLOWUP_TEST_USERS` setting and parsing
- `app/db/crud.py` - Added `test_user_ids` parameter to query functions
- `app/core/scheduler.py` - Pass whitelist to queries and log test mode
- `env.local.example` - Documented new variable
- `sample.env` - Documented new variable
- `README.md` - Added documentation

