# Repetitive Responses - Problem Analysis & Fix

## Problem Summary

The bot was generating nearly identical responses regardless of user input, creating a poor conversational experience:

```
User: "hello"
Bot: "I tilt my head, a soft smile playing on my lips. Darling, I must admit..."

User: "What are you doing lately?"
Bot: "I tilt my head, a soft smile playing on my lips. Darling, I must admit..."

User: "hey darling, i am just a wonderer"
Bot: "I tilt my head, a soft smile playing on my lips. Darling, I must admit..."
```

Additionally, auto-follow-up messages were being sent too frequently (every 5 minutes), further amplifying the repetitiveness.

## Root Causes Identified

### 1. **Overly Aggressive Auto-Follow-Up System**

- The scheduler was checking for inactive chats **every minute**
- Auto-follow-ups were triggered after just **5 minutes** of inactivity
- Result: Multiple follow-up messages sent in quick succession

### 2. **Generic, Repetitive Auto-Follow-Up Prompts**

- The same instruction was used for every auto-follow-up:
  ```
  "You haven't heard from the user in a while. Send them a natural, contextual
  follow-up message to re-engage the conversation..."
  ```
- This caused the AI to generate similar "reaching out" messages every time

### 3. **Insufficient Conversation Context Enforcement**

- The dialogue specialist wasn't explicitly instructed to respond directly to the user's last message
- No warnings against repetition in the system prompt
- The AI would fall into patterns without explicit variation instructions

### 4. **Lack of State Change Tracking**

- No logging to verify if conversation state was evolving
- Difficult to debug whether the state resolver was properly updating context
- State changes weren't being validated

## Fixes Implemented

### Fix 1: Increased Auto-Follow-Up Interval (scheduler.py)

**Changed:** Auto-follow-up check from **5 minutes → 30 minutes**

```python
# Before:
inactive_chats = crud.get_inactive_chats(db, minutes=5)

# After:
inactive_chats = crud.get_inactive_chats(db, minutes=30)
```

**Impact:** Bot will now wait 30 minutes before sending a follow-up, giving users adequate time to respond naturally.

### Fix 2: Varied Auto-Follow-Up Prompts (scheduler.py)

**Added:** 4 different follow-up prompt templates selected randomly

```python
followup_prompts = [
    "[AUTO_FOLLOWUP] The user hasn't replied in a while. Reach out naturally - ask what they've been up to...",
    "[AUTO_FOLLOWUP] It's been quiet for a bit. Send a message that picks up naturally from your last conversation...",
    "[AUTO_FOLLOWUP] Time to re-engage. Send a natural, spontaneous message...",
    "[AUTO_FOLLOWUP] The conversation paused. Reach out with genuine curiosity..."
]
```

**Impact:** Auto-follow-up messages will now have more variety in tone and approach.

### Fix 3: Enhanced Conversation Context Enforcement (dialogue_specialist.py)

**Added:** Explicit instructions to prevent repetition

```python
# CONVERSATION FLOW RULES
- CRITICAL: Respond DIRECTLY to the user's LAST message above. Read it carefully.
- DO NOT repeat previous responses. Each message must be unique and contextual.
- Reference specific details from the user's message (their words, their questions, their actions).
- Build on the conversation naturally - don't reset or start over.
- Vary your physical actions and dialogue - never use the exact same phrases twice.
```

**Added:** Conversation history preview logging

```python
if len(chat_history) > 0:
    print(f"[DIALOGUE] 📚 Using {recent_history_count} history messages")
    print(f"[DIALOGUE] 💬 Last history: {chat_history[-1]['content'][:60]}...")
print(f"[DIALOGUE] ➡️  Current user: {user_message[:80]}...")
```

**Impact:**

- The AI now has explicit instructions to vary responses
- Better debugging visibility into what context is being used

### Fix 4: Improved State Resolution (state_resolver.py)

**Added:** State update rules and change tracking

```python
# STATE UPDATE RULES
- Update state to reflect NEW developments in the conversation
- Track relationship progression naturally based on dialogue
- Note any changes in location, clothing, mood, or emotions
- If the conversation is evolving, the state MUST evolve too
- Each user message may introduce new context - capture it
```

**Added:** State change validation logging

```python
print(f"[STATE-RESOLVER] ✅ State resolved ({len(state_text)} chars)")
print(f"[STATE-RESOLVER] 📝 Full state: {state_text}")

# Check if state has changed
if previous_state and state_text == previous_state:
    print(f"[STATE-RESOLVER] ⚠️  WARNING: State unchanged from previous!")
```

**Impact:**

- State resolver now explicitly tracks conversation evolution
- We can now detect when state isn't changing (indicating a problem)

### Fix 5: Enhanced Pipeline Logging (multi_brain_pipeline.py)

**Added:** Conversation history preview before processing

```python
if chat_history:
    print(f"[BATCH] 📚 Conversation history ({len(chat_history)} messages):")
    for i, msg in enumerate(chat_history[-5:], 1):
        print(f"[BATCH]    {i}. {msg['role']}: {msg['content'][:80]}...")
else:
    print(f"[BATCH] 📚 No conversation history (new chat)")

print(f"[BATCH] 💬 Current batch text: {batched_text[:100]}...")
```

**Impact:**

- Much better visibility into what the pipeline is processing
- Easier to debug conversation context issues

## Expected Improvements

### Immediate Benefits

1. **Less Frequent Auto-Messages**: 30-minute interval prevents spam
2. **More Varied Auto-Follow-Ups**: Random selection from 4 different prompt styles
3. **Better Context Awareness**: AI explicitly instructed to respond to specific user input
4. **Improved Debugging**: Comprehensive logging shows exactly what's happening at each step

### Behavioral Improvements

1. **Unique Responses**: Each reply should now reference specific details from the user's message
2. **Natural Conversation Flow**: The AI should build on previous exchanges rather than resetting
3. **Varied Language**: Explicit instruction against repeating phrases
4. **State Evolution**: Conversation state should now update more dynamically

## Testing Checklist

To verify the fixes are working:

### ✅ Response Variety Test

- [ ] Send 3-5 different messages to the bot
- [ ] Verify each response is unique and contextually relevant
- [ ] Check that the bot references specific details from your messages

### ✅ Auto-Follow-Up Test

- [ ] Wait 30+ minutes without replying
- [ ] Verify only ONE follow-up message is sent (not multiple)
- [ ] Check that follow-up messages vary in style over multiple tests

### ✅ Conversation Memory Test

- [ ] Have a 10+ message conversation
- [ ] Verify the bot remembers and references earlier parts of the conversation
- [ ] Check that state is evolving (look at logs for state changes)

### ✅ Log Inspection

```bash
# Monitor the bot logs to see:
# 1. Conversation history is being properly loaded
# 2. State is changing between messages
# 3. No "WARNING: State unchanged" messages

tail -f /path/to/bot/logs
```

## How to Restart the Bot

To apply these changes:

```bash
# If running locally:
pkill -f "python.*main.py"  # Stop the bot
python -m app.main          # Restart with new code

# If on Railway/Heroku:
git add -A
git commit -m "Fix repetitive responses and auto-follow-up spam"
git push origin main        # Will auto-deploy
```

## Monitoring After Deploy

Watch the logs for these key indicators:

```
[DIALOGUE] ➡️  Current user: <different messages each time>
[STATE-RESOLVER] 📝 Full state: <should vary>
[BATCH] 📚 Conversation history: <should accumulate>
```

If you still see repetition, check for:

1. State not changing (WARNING message)
2. Conversation history not loading properly
3. Same user input being logged repeatedly

## Additional Recommendations

### If Repetition Persists:

1. **Check the Model Configuration** (`config/app.yaml`)

   - Ensure `temperature` is set to at least `0.7` for creativity
   - Consider trying a different model if the current one is too deterministic

2. **Review the Base Prompt** (`config/prompts.py`)

   - The `CHAT_GPT` prompt might need more variety instructions
   - Consider adding more "forbidden phrases" examples

3. **Increase Temperature** (dialogue_specialist.py)

   ```python
   # Current: temperature = 0.8 + (attempt - 1) * 0.1
   # Consider: temperature = 0.9 + (attempt - 1) * 0.05
   ```

4. **Expand Conversation History**
   ```python
   # Current: MAX_CONTEXT_MESSAGES = 10
   # Consider: MAX_CONTEXT_MESSAGES = 15
   ```

## Summary

The core issue was a combination of:

- **Too-frequent auto-follow-ups** (5 min → 30 min)
- **Generic follow-up prompts** (1 template → 4 varied templates)
- **Insufficient context enforcement** (added explicit anti-repetition rules)
- **Poor debugging visibility** (added comprehensive logging)

These fixes should dramatically improve response variety and reduce the "robotic" feeling of repetitive responses.

---

**Date Fixed**: October 18, 2025  
**Files Modified**:

- `app/core/scheduler.py`
- `app/core/brains/dialogue_specialist.py`
- `app/core/brains/state_resolver.py`
- `app/core/multi_brain_pipeline.py`
