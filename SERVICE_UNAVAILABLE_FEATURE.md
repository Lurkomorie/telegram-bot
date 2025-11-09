# Service Unavailable Feature

## Overview

This feature allows you to temporarily disable the bot from processing user requests while showing a friendly maintenance message. This is useful during:
- System maintenance
- Urgent bug fixes
- Database migrations
- Service upgrades

## How It Works

1. **Environment Variable**: Set `SERVICE_UNAVAILABLE=True` in your environment
2. **Middleware**: A middleware intercepts all incoming messages and callbacks
3. **One-Time Notification**: Each user receives the maintenance message only once
4. **Redis Tracking**: Uses Redis to track which users have been notified (TTL: 24 hours)
5. **Graceful Handling**: Silently ignores subsequent messages from notified users

## Usage

### Enable Maintenance Mode

Set the environment variable in Railway or your hosting platform:

```bash
SERVICE_UNAVAILABLE=True
```

The bot will:
- ✅ Show a maintenance message to users on their first interaction
- ✅ Track notified users in Redis (24-hour cache)
- ✅ Silently ignore subsequent messages from the same user
- ✅ Handle both messages and callback queries

### Disable Maintenance Mode

Set the environment variable back to false:

```bash
SERVICE_UNAVAILABLE=False
```

Or simply remove the variable (defaults to `False`).

## Customizing the Message

Edit the message in `/config/ui_texts.yaml`:

```yaml
system:
  service_unavailable: "🛠 <b>Temporary Maintenance</b>\n\nWe're currently performing system maintenance to improve your experience. Our service will be back online shortly.\n\nThank you for your patience! 💙"
```

## Technical Details

### Files Modified/Created

1. **`app/settings.py`** - Added `SERVICE_UNAVAILABLE` flag
2. **`app/bot/middleware.py`** - Created middleware to intercept updates
3. **`app/bot/loader.py`** - Registered middleware with dispatcher
4. **`config/ui_texts.yaml`** - Added maintenance message text
5. **`sample.env`** - Documented the new environment variable

### Redis Keys

- **Pattern**: `service_unavailable_notified:{user_id}`
- **TTL**: 86400 seconds (24 hours)
- **Value**: `"1"` (simple flag)

### Middleware Behavior

The `ServiceUnavailableMiddleware`:
1. Runs before all other handlers
2. Checks the `SERVICE_UNAVAILABLE` setting
3. If enabled:
   - Extracts user_id from the update (message or callback)
   - Checks Redis for notification status
   - Sends message if not notified
   - Marks user as notified in Redis
   - Stops further processing
4. If disabled:
   - Passes through to normal handlers

## Testing

### Local Testing

1. Set in your `.env` file:
```env
SERVICE_UNAVAILABLE=True
```

2. Start the bot locally
3. Send any message or command
4. You should receive the maintenance message
5. Send another message - nothing should happen
6. Check logs for `[SERVICE-UNAVAILABLE]` entries

### Production Testing

1. Set the environment variable in Railway
2. Restart the service
3. Test with a test account
4. Verify the message appears only once
5. Set back to `False` and restart

## Notes

- Users are tracked per user ID, not per chat
- The notification cache expires after 24 hours
- Callback queries are answered to prevent loading states
- Works with all types of updates (messages, commands, callbacks)
- Does not affect API endpoints (only bot interactions)

## Rollback

If you need to immediately disable maintenance mode:

1. Set `SERVICE_UNAVAILABLE=False`
2. Restart the service
3. Optionally clear Redis keys: `redis-cli KEYS "service_unavailable_notified:*" | xargs redis-cli DEL`

