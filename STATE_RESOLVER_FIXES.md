# State Resolver Hallucination Fix

## Problem Identified

The state resolver was changing **location** and **clothing** values even when the conversation didn't mention these changes at all. This created inconsistency and broke immersion.

### Example of the Problem:

```
User: "hello"
State: location="bedroom", aiClothing="red dress"

User: "how are you?"
State: location="beach", aiClothing="blue bikini"  ❌ WRONG - nothing mentioned this!
```

## Root Cause

The `CONVERSATION_STATE_GPT` prompt in `config/prompts.py` was **too permissive**:

```python
# OLD (PROBLEMATIC) INSTRUCTION:
"If clothing not mentioned, infer a likely specific outfit from the context
(e.g., pool → 'blue bikini'; office → 'navy suit, white shirt')"
```

This told the AI to **invent** changes based on imagined context, causing hallucinations.

## Fixes Applied

### Fix 1: Conservative State Update Rules (`config/prompts.py`)

**Changed the core objective:**

```
OLD: "Infer and update state from conversation + previous state"
NEW: "Update state ONLY when conversation explicitly mentions changes.
     Maintain previous state for unchanged fields."
```

**Added CRITICAL CONSISTENCY RULES:**

1. **PRESERVE PREVIOUS STATE BY DEFAULT**

   - Keep all values unless conversation EXPLICITLY changes them
   - Example: If location was "bedroom" and nothing mentions moving → keep "bedroom"

2. **ONLY UPDATE WHEN EXPLICITLY MENTIONED**

   - `location`: Change ONLY when user says "let's go to...", "we're at...", "move to..."
   - `aiClothing`: Change ONLY when mentioned "I put on...", "wearing...", "takes off..."
   - `userClothing`: Change ONLY when user describes their outfit
   - **DO NOT infer or assume changes based on context**

3. **FORBIDDEN: DO NOT HALLUCINATE**

   - Don't change location just because you think it "makes sense"
   - Don't change clothing just because you imagine a different outfit
   - Don't add details that weren't mentioned
   - **If unsure whether something changed, DON'T CHANGE IT**

4. **WHAT YOU CAN UPDATE FREELY**
   - `emotions`: Always update based on current tone
   - `description`: Always update to reflect what's happening now
   - `moodNotes`: Update if conversation mentions time/lighting/atmosphere
   - `relationshipStage`: Update if clear progression in intimacy

### Fix 2: Enhanced Context Instructions (`state_resolver.py`)

**Updated the state context building** to reinforce consistency:

```python
# PREVIOUS STATE (maintain these values unless explicitly changed in conversation)
{state_text}

# STATE UPDATE RULES
CRITICAL: Preserve previous state by default. Only update fields that are
EXPLICITLY mentioned in the conversation.

DO NOT:
- Invent location changes that weren't mentioned
- Change clothing without explicit mention
- Add details that weren't in the conversation
- Assume changes based on "context" - stick to what was actually said

When unsure if something changed: DON'T CHANGE IT. Maintain consistency.
```

### Fix 3: State Change Validation (`state_resolver.py`)

**Added validation functions** to detect unjustified changes:

```python
def _validate_state_changes(previous_state: str, new_state: str, user_message: str):
    """Validate that state changes are justified by the conversation"""

    # Check location changes
    if location changed:
        location_keywords = ['go to', 'move to', "let's go", 'at the', 'in the', 'to the']
        if no keywords found:
            print("[STATE-VALIDATOR] ⚠️  WARNING: Location changed without explicit mention!")

    # Check clothing changes
    if clothing changed:
        clothing_keywords = ['wear', 'put on', 'change', 'dress', 'undress', 'remove', 'take off']
        if no keywords found:
            print("[STATE-VALIDATOR] ⚠️  WARNING: Clothing changed without explicit mention!")
```

This validation runs **after every state update** and logs warnings when unjustified changes are detected.

## How State Resolution Works Now

### Conservative Update Behavior

**Scenario 1: Nothing changes in conversation**

```
Previous State:
  location="cozy bedroom"
  aiClothing="silk nightgown, black lace"

User: "you look beautiful"
Assistant: "thank you darling"

New State:
  location="cozy bedroom"  ✅ UNCHANGED (correct)
  aiClothing="silk nightgown, black lace"  ✅ UNCHANGED (correct)
  emotions="flattered, warm"  ✅ UPDATED (emotions can change freely)
```

**Scenario 2: Explicit location change**

```
Previous State:
  location="bedroom"
  aiClothing="red dress"

User: "let's go to the balcony"
Assistant: "wonderful idea, let's step outside"

New State:
  location="balcony"  ✅ CHANGED (explicitly mentioned)
  aiClothing="red dress"  ✅ UNCHANGED (no mention of clothing)
```

**Scenario 3: Explicit clothing change**

```
Previous State:
  location="bedroom"
  aiClothing="red dress"

User: "why don't you put on something more comfortable?"
Assistant: "I'll change into my silk robe"

New State:
  location="bedroom"  ✅ UNCHANGED (no mention of moving)
  aiClothing="silk robe"  ✅ CHANGED (explicitly mentioned)
```

## Testing the Fix

### How to Verify It's Working

1. **Start a conversation** without mentioning location or clothing
2. **Send 5-10 messages** like:
   - "hello"
   - "how are you?"
   - "what's on your mind?"
   - "tell me about yourself"
3. **Check the logs** for state updates:
   ```bash
   grep "STATE-RESOLVER" logs.txt | tail -20
   ```
4. **Verify location and clothing remain consistent**

### What to Look For in Logs

**Good signs (state is working correctly):**

```
[STATE-RESOLVER] ✅ State resolved (150 chars)
[STATE-RESOLVER] 📝 Full state: ... location="bedroom" ... aiClothing="red dress" ...
```

**Warning signs (unjustified changes detected):**

```
[STATE-VALIDATOR] ⚠️  WARNING: Location changed without explicit mention!
[STATE-VALIDATOR]    Old: bedroom
[STATE-VALIDATOR]    New: balcony
[STATE-VALIDATOR]    User message: how are you?
```

If you see validation warnings, the state resolver is still hallucinating changes despite the new rules. This would indicate:

- The LLM model is too creative and ignoring instructions
- Temperature might need to be lowered further
- We may need even more explicit constraints

## Expected Improvements

### Before Fix:

- ❌ Location changed randomly every few messages
- ❌ Clothing changed without any mention
- ❌ State was unreliable and inconsistent
- ❌ Broke immersion with nonsensical changes

### After Fix:

- ✅ Location stays consistent unless explicitly changed
- ✅ Clothing stays consistent unless explicitly mentioned
- ✅ State changes are predictable and logical
- ✅ Maintains immersion with consistent scene continuity

## Advanced: If Hallucinations Continue

If you still see unjustified state changes after this fix, try these additional measures:

### 1. Lower Temperature for State Resolver

In `app/core/brains/state_resolver.py`:

```python
# Current: temperature=0.3
# Try: temperature=0.1
result = await generate_text(
    messages=messages,
    model=state_model,
    temperature=0.1,  # More deterministic
    max_tokens=500
)
```

### 2. Try a Different Model

In `config/app.yaml`:

```yaml
llm:
  state_model: mistralai/mistral-nemo:nitro  # Try a different model
  # or
  state_model: openai/gpt-4o-mini  # More expensive but better at following rules
```

### 3. Add Few-Shot Examples

Add examples to the prompt showing correct behavior:

```python
EXAMPLE 1 (Correct):
Previous: location="bedroom", aiClothing="red dress"
User: "how are you?"
Output: location="bedroom", aiClothing="red dress"  ← UNCHANGED (correct!)

EXAMPLE 2 (Wrong):
Previous: location="bedroom", aiClothing="red dress"
User: "how are you?"
Output: location="balcony", aiClothing="blue bikini"  ← WRONG! Nothing mentioned this!
```

### 4. Implement Strict Field Locking

Modify state resolver to programmatically preserve fields:

```python
def resolve_state_with_locking(previous_state, new_state, user_message):
    # Parse both states
    prev = parse_state(previous_state)
    new = parse_state(new_state)

    # Check if change is justified
    if prev['location'] != new['location']:
        if not has_location_keywords(user_message):
            # Force keep previous location
            new['location'] = prev['location']

    if prev['aiClothing'] != new['aiClothing']:
        if not has_clothing_keywords(user_message):
            # Force keep previous clothing
            new['aiClothing'] = prev['aiClothing']

    return serialize_state(new)
```

This would add a **hard constraint** that overrides the LLM if it makes unjustified changes.

## Summary

**Files Modified:**

- `config/prompts.py` - Made CONVERSATION_STATE_GPT much more conservative
- `app/core/brains/state_resolver.py` - Added validation and clearer instructions

**Key Changes:**

1. Changed objective from "infer" to "only update when explicitly mentioned"
2. Added CRITICAL CONSISTENCY RULES section with explicit forbidden behaviors
3. Added validation function to detect and warn about unjustified changes
4. Enhanced logging to show when state changes inappropriately

**Expected Result:**

- Location and clothing now stay consistent unless conversation explicitly changes them
- Emotions and description still update naturally with the conversation flow
- Validation warnings help identify if the model is still hallucinating

---

**Date Fixed**: October 18, 2025  
**Issue**: State resolver hallucinating location and clothing changes  
**Status**: Fixed with conservative update rules and validation


