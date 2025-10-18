# Redis-Based Message Batching Implementation

## Overview

Successfully implemented Redis-based message batching system that:

- Queues messages in Redis instead of database
- Processes batches sequentially, one response per batch
- Automatically loops through batches until queue is empty
- Uses Redis locks to prevent race conditions

## Changes Made

### 1. New File: `app/core/redis_queue.py`

Redis queue management with the following functions:

- `add_message_to_queue()` - Add message to Redis list
- `get_batch_messages()` - Get all queued messages for a chat
- `clear_batch_messages()` - Clear queue after processing
- `set_processing_lock()` - Redis-based locking mechanism
- `is_processing()` - Check if chat is being processed
- `get_queue_length()` - Get current queue size

### 2. Updated: `app/bot/handlers/chat.py`

**Key Changes:**

- Messages no longer saved to DB immediately
- Messages queued in Redis instead
- Removed DB-based processing lock checks
- Simplified message handler logic
- Pipeline called with new signature (no batched_messages/batched_text params)

**Flow:**

1. User message arrives
2. Add to Redis queue
3. Check if processing (Redis lock)
4. If not processing, start pipeline
5. If processing, message stays queued

### 3. Updated: `app/core/multi_brain_pipeline.py`

**Major Refactor:**

- Changed function signature - now receives only `chat_id`, `user_id`, `tg_chat_id`
- Implements batch processing loop
- Uses Redis lock instead of DB lock
- New `_process_single_batch()` helper function

**Flow:**

1. Set Redis processing lock
2. **Loop while queue not empty:**
   - Get batch from Redis
   - Process with AI brains (State + Dialogue)
   - Save all messages to DB (marked as processed)
   - Send response to user
   - Clear batch from Redis
   - Check queue again
3. Clear processing lock
4. Start background image generation

### 4. Updated: `app/db/crud.py`

**Added:**

- `create_batch_messages()` - Save multiple user messages at once from Redis batch
- Messages saved with `is_processed=True` (already processed by time of saving)

**Note:** DB-based locking functions (`set_chat_processing`, `is_chat_processing`) are kept for backward compatibility but no longer used.

### 5. Updated: `app/bot/handlers/start.py`

**Added:**

- Clear Redis queue when switching personas
- Clear Redis processing lock on persona switch
- Prevents stale messages from previous persona

## Benefits

### ✅ True Batching

- Multiple messages receive **one combined response**
- AI analyzes all messages together as context

### ✅ No Race Conditions

- Redis atomic operations
- Automatic lock expiration (10 min timeout)
- Clean state management

### ✅ Sequential Processing

- Batches processed in order
- Loop continues until queue empty
- No messages left unprocessed

### ✅ Simpler State Management

- Queue-based instead of DB flags
- Redis handles concurrency
- Automatic cleanup with TTL

## Testing Checklist

### Basic Flow

- [ ] Send single message → receives response
- [ ] Send 3 quick messages → receives 1 combined response
- [ ] Send messages while processing → queued and processed in next batch

### Edge Cases

- [ ] Switch persona mid-queue → old messages cleared
- [ ] `/clear` command → Redis queue cleared
- [ ] Multiple batches → all processed sequentially

### Error Recovery

- [ ] Pipeline error → lock cleared, next message works
- [ ] Redis connection issue → fallback behavior
- [ ] Stuck lock (10 min) → auto-expires

## Configuration

### Redis Keys

- `msg_queue:{chat_id}` - Message queue (list)
- `processing_lock:{chat_id}` - Processing lock (string, 10 min TTL)

### Queue Settings

- Queue TTL: 30 minutes
- Lock timeout: 10 minutes (auto-cleanup)

## Migration Notes

### What Changed

- Messages **NOT** saved to DB on arrival
- Messages saved to DB **after** processing
- Processing lock moved from DB to Redis

### Backward Compatibility

- DB fields `is_processing`, `processing_started_at` kept in Chat model
- DB field `is_processed` still used in Message model
- Old CRUD functions still exist but unused

### No Migration Required

- Redis-only changes
- DB schema unchanged
- Existing data unaffected

## Deployment

1. Ensure Redis is running and `REDIS_URL` is set
2. Deploy updated code
3. No database migration needed
4. Monitor logs for `[PIPELINE]` and `[BATCH]` messages

## Logs

### New Log Markers

- `[PIPELINE]` - Pipeline orchestration
- `[BATCH]` - Individual batch processing
- `[CHAT]` - Message handler
- `[REDIS-QUEUE]` - Redis operations (errors)

### Example Flow

```
[CHAT] 📨 Message from user 12345
[CHAT] 📥 Adding message to Redis queue
[CHAT] 📊 Queue length: 1
[CHAT] 🚀 Starting batch processing (1 message(s))
[PIPELINE] 🚀 Starting pipeline
[PIPELINE] 🔒 Processing lock SET (Redis)
[PIPELINE] 📦 Processing batch #1 (1 message(s))
[BATCH] 🧠 Brain 1: Resolving state...
[BATCH] 🧠 Brain 2: Generating dialogue...
[BATCH] 💾 Saving batch to database...
[BATCH] ✅ Response sent to user
[PIPELINE] ✅ Queue empty, stopping loop
[PIPELINE] 🔓 Processing lock CLEARED
```

## Future Improvements

1. **Configurable batch timing** - Add delay before processing to collect more messages
2. **Batch size limits** - Max messages per batch
3. **Priority queues** - VIP users processed first
4. **Metrics** - Track batch sizes, processing times
5. **Redis pub/sub** - Notify when queue has messages

