# Persona and Story Selection UI Update

## Summary

Updated the `/start` command flow to match the new UI design with enhanced persona and story selection interfaces.

## Changes Made

### 1. Database Schema Updates (`app/db/models.py`)

Added new fields to enhance UI display:

**Persona Model:**

- `small_description` (Text): Short one-line description for persona selection
- `emoji` (String, max 10 chars): Emoji icon for persona (e.g., "💕", "🌟")

**PersonaHistoryStart Model:**

- `name` (String, max 255): Story name (e.g., "The Dairy Queen")
- `small_description` (Text): Short story description for menu display

### 2. Database Migration

Created migration file: `app/db/migrations/versions/012_add_persona_display_fields.py`

**To apply the migration, run:**

```bash
alembic upgrade head
```

### 3. Keyboard Builders (`app/bot/keyboards/inline.py`)

**Updated `build_persona_selection_keyboard`:**

- Now displays personas in a 2-column grid layout
- Uses emoji and small_description from database
- Format: "emoji Name" for each button

**New `build_story_selection_keyboard`:**

- Displays stories in a 2-column grid layout
- Extracts emoji from story name if present
- Includes "Back" button to return to persona selection

**Updated `build_chat_options_keyboard`:**

- Changed "Start New" to use `new_chat_select` callback to show story selection

### 4. Start Handler (`app/bot/handlers/start.py`)

**New Flow:**

1. `/start` → Shows persona selection with descriptions
2. User selects persona → Shows story selection (or continue/new options if chat exists)
3. User selects story → Creates chat and starts conversation with hint message

**Key Changes:**

- Persona selection now displays full descriptions in message text
- Added `show_story_selection()` helper function
- Added `select_story_callback()` handler for story selection
- Added `new_chat_select_callback()` to show story selection when starting new chat
- System messages are edited (not duplicated) using `message.edit_text()`
- Selection message is deleted after story is selected
- Hint message is sent after story selection: "💡 HINT: Press /start to restart conversation any time"

**Message Flow:**

- Initial persona selection: New message
- Story selection: Edits the persona selection message
- After story selected: Deletes selection message, sends greeting + hint

## UI Format

### Persona Selection

```
Choose your companion:

💕 Jane – Flirtatious traditional girl

👩 Mrs. Grace – Caring and charming MILF

✨ Bianca – Confident, sharp-tongued, seductively witty, MILF

💜 Kate – Caring, confident, direct, MILF

🐱 Nya – Playful, mischievous, and affectionate cat girl

...

[Buttons in 2-column grid]
```

### Story Selection

```
Choose your story:

🥛 The Dairy Queen – A beautiful stranger approaches you to lend a hand.

🌧️🕯️ Power Outage Guest – A storm knocks out power, and Jane asks to stay the night.

🎀🏙️ Southern Charm in the City – You help Jane move into the city, and she invites you to stay a while.

[Buttons in 2-column grid]
[Back button]
```

## Next Steps

1. **Run the database migration:**

   ```bash
   alembic upgrade head
   ```

2. **Update existing personas** to add emoji and small_description fields

3. **Update existing persona history starts** to add name and small_description fields

4. **Test the flow:**
   - Send `/start` in Telegram
   - Select a persona
   - Select a story
   - Verify greeting and hint message appear
   - Test "Continue" vs "Start New" flow for existing chats

## Notes

- All system messages (persona/story selection) are properly edited instead of creating new messages
- The selection message is deleted after user makes final choice
- Hint message helps users understand they can restart anytime with `/start`
- Back button allows users to return to persona selection from story selection
- Maintains backward compatibility with existing chat flows (continue, start new, deep links)
