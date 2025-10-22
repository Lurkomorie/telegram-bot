# Scenario Selection Fix

## Problem

The "Select This Scenario" button in the miniapp wasn't working. Users could browse characters and scenarios, but clicking the button did nothing.

## Root Cause

The miniapp was using `WebApp.sendData()` to send the selection back to the bot. However, **`WebApp.sendData()` only works when the Mini App is opened from a reply keyboard button** (KeyboardButton), not from an inline keyboard button (InlineKeyboardButton with `web_app` parameter).

Since the miniapp is opened via an InlineKeyboardButton (see `app/bot/keyboards/inline.py` line 113-116), the `sendData()` method fails silently and the bot's `web_app_data` handler is never triggered.

## Solution

Switched from `WebApp.sendData()` to using Telegram deep links:

### 1. Frontend Changes (`miniapp/src/App.jsx`)

- **Old approach**: Used `WebApp.sendData(JSON.stringify(data))` to send persona_id and history_id
- **New approach**: Uses `WebApp.openTelegramLink()` with a deep link in the format: `https://t.me/BOT_USERNAME?start=persona_<UUID>_h<HISTORY_UUID>`
- When user clicks "Select This Scenario", the miniapp now:
  1. Opens the deep link using `WebApp.openTelegramLink()`
  2. Closes itself using `WebApp.close()`
  3. Redirects user to the bot with the selection encoded in the start parameter

### 2. Backend Changes (`app/bot/handlers/start.py`)

- **Updated the `/start` command handler** to parse both persona_id and history_id from deep links
- **Deep link format**: `/start persona_<UUID>_h<HISTORY_UUID>`
  - Example: `/start persona_123e4567-e89b-12d3-a456-426614174000_h987fcdeb-51a3-87b6-c765-123456789abc`
- **Parsing logic**:
  ```python
  parts = deep_link_param.replace("persona_", "").split("_h")
  persona_id = parts[0]
  history_id = parts[1] if len(parts) > 1 else None
  ```
- If history_id is provided, calls `create_new_persona_chat_with_history()`
- If not, calls `create_new_persona_chat()` (random history)

### 3. Additional Keyboard (`app/bot/keyboards/inline.py`)

- Added `build_persona_gallery_keyboard()` function to create a button that opens the persona gallery page in the miniapp
- Can be used in commands like `/start` or `/girls` to provide a modern UI for character selection

## How It Works Now

1. User clicks "👯 Browse Characters" button in bot (or opens miniapp from energy page)
2. Miniapp loads and displays persona gallery
3. User selects a persona → miniapp fetches available scenarios
4. User clicks "Select This Scenario" button
5. Miniapp constructs deep link: `https://t.me/sexsplicit_companion_bot?start=persona_<ID>_h<HISTORY_ID>`
6. Miniapp opens the deep link and closes itself
7. User is redirected to the bot, which receives the `/start` command with parameters
8. Bot parses the persona_id and history_id from the deep link
9. Bot checks if chat exists:
   - If exists: Shows "Continue / Start New" options
   - If not: Creates new chat with selected scenario
10. User starts chatting with the selected persona and scenario

## Testing

To test the fix:

1. Deploy the updated miniapp (already built to `miniapp/dist/`)
2. Restart the bot to load the updated handlers
3. Open the miniapp and navigate to persona gallery
4. Select a persona
5. Click "Select This Scenario" button
6. Verify you're redirected back to the bot with the correct scenario

## Files Changed

- `miniapp/src/App.jsx` - Changed handleHistoryClick() to use deep links
- `app/bot/handlers/start.py` - Updated /start handler to parse history_id from deep link
- `app/bot/keyboards/inline.py` - Added build_persona_gallery_keyboard() function
- `miniapp/dist/` - Rebuilt with updated code

## Alternative Approaches Considered

1. **Use a reply keyboard button instead of inline keyboard** - Would work but changes the UX flow
2. **Make API call to backend instead of deep link** - Would require storing state and polling
3. **Keep using web_app_data handler** - Only works with reply keyboard buttons

The deep link approach is the cleanest solution that maintains the current UX while providing reliable functionality.
