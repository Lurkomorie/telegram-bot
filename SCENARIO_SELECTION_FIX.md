# Scenario Selection Fix

## Status: ✅ FIXED (Oct 22, 2025)

The issue with scenario selection not working has been resolved. The miniapp now uses a dedicated API endpoint to create chats and send greeting messages directly.

## Problem

The "Select This Scenario" button in the miniapp wasn't working. Users could browse characters and scenarios, but clicking the button did nothing.

## Root Cause

The miniapp was using `WebApp.sendData()` to send the selection back to the bot. However, **`WebApp.sendData()` only works when the Mini App is opened from a reply keyboard button** (KeyboardButton), not from an inline keyboard button (InlineKeyboardButton with `web_app` parameter).

Since the miniapp is opened via an InlineKeyboardButton (see `app/bot/keyboards/inline.py` line 113-116), the `sendData()` method fails silently and the bot's `web_app_data` handler is never triggered.

## Solution

Created a new API endpoint that handles scenario selection server-side:

### 1. New API Endpoint (`app/api/miniapp.py`)

- **Added `/api/miniapp/select-scenario` endpoint** (POST)
- **Request body**: `{persona_id: string, history_id: string | null}`
- **What it does**:
  1. Validates Telegram WebApp authentication
  2. Extracts user ID from init data
  3. Checks if a chat already exists with the persona
  4. Creates a new chat in the database
  5. Gets the selected history (or random if not specified)
  6. Saves greeting messages to the database
  7. **Directly sends the greeting messages to the user via the bot API**
  8. Returns success/failure status
- **Benefits**: No reliance on deep links, more reliable, works consistently

### 2. Frontend API Client (`miniapp/src/api.js`)

- **Added `selectScenario()` function** to call the new endpoint
- Takes persona_id, history_id (optional), and initData
- Returns promise with success status

### 3. Frontend Changes (`miniapp/src/App.jsx`)

- **Old approach**: Used `WebApp.sendData()` (doesn't work with inline buttons) or deep links (unreliable)
- **New approach**: Calls the `selectScenario()` API endpoint
- When user clicks "Select This Scenario", the miniapp now:
  1. Shows loading state with MainButton progress indicator
  2. Calls the API endpoint with persona_id and history_id
  3. API creates chat and sends greeting directly to user
  4. Closes the miniapp on success
  5. Shows alert if chat already exists or on error

### 4. Backend Integration

- Bot instance is imported in the API route handler
- Uses `bot.send_message()` and `bot.send_photo()` to send greetings
- Messages are sent directly to the user's Telegram chat
- All database operations (chat creation, message storage) happen server-side

## How It Works Now

1. User clicks "👯 Browse Characters" button in bot (or opens miniapp from energy page)
2. Miniapp loads and displays persona gallery
3. User selects a persona → miniapp fetches available scenarios
4. User clicks "Select This Scenario" button
5. Miniapp calls `/api/miniapp/select-scenario` with persona_id and history_id
6. API endpoint:
   - Validates authentication
   - Checks if chat exists (returns error if it does)
   - Creates new chat in database
   - Gets selected scenario (or random if none selected)
   - Saves greeting messages to database
   - **Sends greeting directly to user via bot.send_message()**
7. Miniapp receives success response and closes
8. User sees the greeting message appear in their Telegram chat
9. User can immediately start chatting with the selected persona and scenario

**No deep links, no command parsing, no redirect - just a direct API call that creates the chat and sends the message!**

## Testing

To test the fix:

1. Deploy the updated miniapp (already built to `miniapp/dist/`)
2. Restart the bot to load the updated handlers
3. Open the miniapp and navigate to persona gallery
4. Select a persona
5. Click "Select This Scenario" button
6. Verify you're redirected back to the bot with the correct scenario

## Files Changed

- `app/api/miniapp.py` - Added `/select-scenario` endpoint that creates chat and sends greeting
- `miniapp/src/api.js` - Added `selectScenario()` function to call new endpoint
- `miniapp/src/App.jsx` - Changed `handleHistoryClick()` to use API endpoint instead of deep links
- `app/bot/handlers/start.py` - Added debug logging for /start command (deep link support kept for backward compatibility)
- `miniapp/dist/` - Rebuilt with updated code

## Additional Bug Fixes

### 1. Missing Model Fields (Root Cause Fix)

**The main issue was that database migrations added columns, but the SQLAlchemy model definitions were never updated.**

- **Symptom**: `AttributeError: 'Persona' object has no attribute 'avatar_url'`
- **Root Cause**: Migrations 007, 008, 010, and 011 added database columns, but `models.py` wasn't updated to reflect them
- **Missing fields that were added**:
  - `Persona.avatar_url` (migration 007) - Avatar image for gallery display
  - `PersonaHistoryStart.wide_menu_image_url` (migration 008) - Wide image for menu
  - `Chat.ext` (migration 010) - Extended metadata
  - `User.energy`, `User.max_energy` (migration 007) - Energy system
  - `User.is_premium`, `User.premium_until` (migration 011) - Premium subscription
- **Solution**: Updated `app/db/models.py` to include all missing fields

### 2. SQLAlchemy Session Management

Fixed a lazy loading issue in `app/api/miniapp.py`:

- **Problem**: Database session was closing before all ORM attributes were accessed
- **Symptom**: 500 Internal Server Error when calling `/api/miniapp/personas`
- **Solution**: Moved the result list initialization outside the session context and ensured all attributes are accessed within the `with get_db() as db:` block
- This prevents lazy loading errors that occur when trying to access ORM object attributes after the session closes

## Alternative Approaches Considered

1. ~~**Use a reply keyboard button instead of inline keyboard**~~ - Would work but changes the UX flow
2. ~~**Use Telegram deep links**~~ - Unreliable when user is already in chat with bot
3. ~~**Keep using web_app_data handler**~~ - Only works with reply keyboard buttons
4. **✅ Direct API endpoint (CHOSEN)** - Most reliable, server-side chat creation, direct message sending

The API endpoint approach is the most robust solution:

- No reliance on deep links or redirect flows
- Server-side validation and error handling
- Direct message sending via bot API
- Consistent behavior regardless of user's current context
