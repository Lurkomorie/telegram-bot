# Prompt Issues Found and Fixed

## Issues Identified

### 1. ❌ Duplicate User Message in Dialogue Specialist

**Severity:** High  
**Location:** `app/core/brains/dialogue_specialist.py`

**Problem:**  
The dialogue specialist was receiving the user's message TWICE:

1. Once in `chat_history` (fetched from database)
2. Once explicitly as `user_message` parameter

This caused the LLM to see duplicate messages in the prompt, as seen in logs:

```
[Message 2] Role: USER - "hello"
[Message 3] Role: USER - "hello"  # ❌ DUPLICATE
```

**Root Cause:**

- User messages are saved to DB before pipeline runs
- `chat_history` is fetched from DB, including the current unprocessed messages
- Then `user_message` is added again to the messages array

**Fix Applied:**  
Modified `multi_brain_pipeline.py` to exclude current unprocessed messages from `chat_history`:

```python
# Build chat history EXCLUDING current unprocessed messages
current_message_ids = {m["id"] for m in batched_messages}
chat_history = [
    {"role": m.role, "content": m.text}
    for m in messages[-10:]
    if m.text and str(m.id) not in current_message_ids
]
```

---

### 2. ❌ Confusing History Display for First Messages

**Severity:** Medium  
**Location:** `app/core/brains/state_resolver.py`

**Problem:**  
For the very first user message, the "LAST 10 MESSAGES OF CONVERSATION HISTORY" section would show:

```
# LAST 10 MESSAGES OF CONVERSATION HISTORY
**USER:** hello
```

This is confusing because:

- It looks like there's already history when there isn't
- The "history" is actually the current message being processed
- This happened due to the same root cause as issue #1

**Fix Applied:**  
The fix in `multi_brain_pipeline.py` also resolves this. Now for the first message:

```
# LAST 10 MESSAGES OF CONVERSATION HISTORY
No conversation history yet.
```

---

### 3. ⚠️ State Resolver Seeing Message Twice

**Severity:** Medium  
**Location:** `app/core/brains/state_resolver.py`

**Problem:**  
State resolver prompt structure:

1. Shows chat history (which included current message)
2. Then shows "Last user message: hello" (same message again)

This created redundancy in the prompt.

**Fix Applied:**  
Same fix as above - current message is now excluded from history, so it only appears once in the "Last user message" section.

---

## Additional Improvements

### Documentation Updates

Added clarifying comments to make the data flow clear:

**In `multi_brain_pipeline.py`:**

```python
# Build chat history EXCLUDING current unprocessed messages
# (they'll be added separately as user_message parameter)
```

**In `dialogue_specialist.py`:**

```python
# Build messages (include recent context + current user message)
# Note: user_message is NOT in chat_history, so we add it here
messages = [
    {"role": "system", "content": full_system_prompt},
    *chat_history[-MAX_CONTEXT_MESSAGES:],  # Recent processed messages
    {"role": "user", "content": user_message}  # Current unprocessed message
]
```

**In `state_resolver.py`:**

```python
"""Build context for state resolver

Note: chat_history contains ONLY processed messages (not current user message)
"""
```

---

## Expected Behavior After Fixes

### First User Message

**State Resolver Prompt:**

```
# LAST 10 MESSAGES OF CONVERSATION HISTORY
No conversation history yet.

# PREVIOUS STATE
{...initial state...}

# CHARACTER INFO
- Name: Rei

Last user message: hello
```

**Dialogue Specialist Prompt:**

```
[Message 1] Role: SYSTEM
[system prompt...]

[Message 2] Role: USER
hello
```

### Second User Message (after AI response)

**State Resolver Prompt:**

```
# LAST 10 MESSAGES OF CONVERSATION HISTORY
**USER:** hello
**ASSISTANT:** [AI response...]

# PREVIOUS STATE
{...updated state...}

Last user message: hi again
```

**Dialogue Specialist Prompt:**

```
[Message 1] Role: SYSTEM
[system prompt...]

[Message 2] Role: USER
hello

[Message 3] Role: ASSISTANT
[AI response...]

[Message 4] Role: USER
hi again
```

---

## Testing Recommendations

1. **Test first message in new chat:**

   - Verify no duplicate messages in logs
   - Verify "No conversation history yet" appears
   - Verify AI responds naturally

2. **Test conversation continuity:**

   - Send 3-4 messages back and forth
   - Check logs for proper history building
   - Verify no duplicates in any prompt
   - Verify AI maintains context correctly

3. **Test message batching:**
   - Send multiple messages rapidly
   - Verify batched messages are excluded from history
   - Verify AI responds to all batched content

---

## Files Modified

1. `app/core/multi_brain_pipeline.py` - Core fix for filtering current messages
2. `app/core/brains/dialogue_specialist.py` - Updated comments for clarity
3. `app/core/brains/state_resolver.py` - Updated comments for clarity
