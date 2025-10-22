# Refresh Image Button Fix - COMPLETE

## Problem

The refresh image button was appearing on ALL images in the chat history, even when they were no longer the last message. The button should only appear on the most recent image.

## Root Cause Analysis

### Issue 1: Missing Removal Logic ✅ FIXED

The button was only being removed when a **user** sent a text message, but not when the **AI assistant** sent a response.

**Solution:** Added button removal logic before AI sends responses in the multi-brain pipeline.

### Issue 2: SQLAlchemy JSONB Field Not Updating ✅ FIXED (CRITICAL BUG!)

This was the **REAL problem**! The code was modifying the `ext` JSONB field like this:

```python
# BUGGY CODE - Changes not persisted to database!
chat.ext["last_image_msg_id"] = None
db.commit()
```

**The Problem:** In SQLAlchemy, when you have a JSONB/JSON field and modify its contents (like updating a dictionary key), SQLAlchemy doesn't automatically detect the change. The `commit()` does nothing because SQLAlchemy thinks nothing changed.

**The Solution:** You must explicitly tell SQLAlchemy that the field was modified:

```python
# FIXED CODE - Changes ARE persisted!
from sqlalchemy.orm.attributes import flag_modified

chat.ext["last_image_msg_id"] = None
flag_modified(chat, "ext")  # ← This is critical!
db.commit()
```

This is why:

- Logs showed "✅ Cleared last_image_msg_id from database" but it wasn't actually cleared
- The database kept the old message ID forever
- Every new message tried to remove the button from the same old message
- Telegram returned "message is not modified" error because the button was already gone

## Files Modified

All files where `chat.ext["last_image_msg_id"]` is modified now use `flag_modified()`:

1. **`app/bot/handlers/chat.py`** - User message handler

   - Clears button when user sends message
   - Uses flag_modified to persist changes

2. **`app/core/multi_brain_pipeline.py`** - AI response handler

   - Clears button when AI sends response
   - Uses flag_modified to persist changes

3. **`app/api/miniapp.py`** - Scenario selection

   - Clears button when new scenario starts
   - Uses flag_modified to persist changes

4. **`app/main.py`** - Image callback handler (2 places)

   - Clears old button when new image sent
   - STORES new button message ID
   - Uses flag_modified for both operations

5. **`app/bot/handlers/image.py`** - Refresh image handler
   - Clears button when image is refreshed
   - Uses flag_modified to persist changes

## How It Works Now

The refresh button lifecycle:

1. **New image sent** → Button added, message ID stored with `flag_modified()`
2. **User sends message** → Button removed (if exists), message ID cleared with `flag_modified()`
3. **AI sends response** → Button removed (if exists), message ID cleared with `flag_modified()`
4. **New image generated** → Old button removed, old ID cleared, new button added, new ID stored (all with `flag_modified()`)
5. **New scenario selected** → Old button removed, ID cleared with `flag_modified()`

**Key improvement:** Database changes are now **actually persisted** because we use `flag_modified()` on JSONB fields.

## Technical Details: SQLAlchemy JSONB Tracking

SQLAlchemy doesn't automatically track changes to mutable types (dicts, lists) stored in JSON/JSONB columns. You have three options:

1. **Use `flag_modified()`** (our approach):

   ```python
   obj.ext["key"] = value
   flag_modified(obj, "ext")
   db.commit()
   ```

2. **Reassign the entire dict**:

   ```python
   obj.ext = {**obj.ext, "key": value}  # Creates new dict
   db.commit()
   ```

3. **Use `MutableDict` type** (requires schema change):
   ```python
   from sqlalchemy.ext.mutable import MutableDict
   ext = Column(MutableDict.as_mutable(JSONB))
   ```

We chose option 1 as it's the least invasive fix.

## Testing Results

After the fix:

- ✅ Button appears only on the latest image
- ✅ Button disappears when any message (user or AI) is sent
- ✅ Database state is properly updated and persisted
- ✅ No more "message is not modified" errors (or harmless if they occur)
- ✅ New images properly track message IDs

## Result

The refresh button now works **exactly as intended**:

- Only the **last message** in the chat (if it's an image) has a refresh button
- Any subsequent message (from user OR AI) removes the button
- The system properly tracks which image currently has the button
- Database state stays clean and up-to-date
