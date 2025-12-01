# Custom Character History Flow Analysis

## Problem Statement

Custom-created characters are experiencing two critical issues:

1. **Characters always start nude** - Despite clothing being specified, images show characters without clothes
2. **Undefined locations** - Characters start in generic/undefined locations rather than scene-appropriate settings

## Complete Application Flow

### 1. Character Creation Flow

#### 1.1 User Creates Character (Frontend)

**File:** `miniapp/src/components/CharacterCreation.jsx`

User provides:

- Name
- Physical attributes (hair, eyes, body type, etc.)
- Personality description (`extra_prompt`)
- Optional visual details (clothing, style)

#### 1.2 Character DNA Generation

**File:** `app/core/character_builder.py`

**Function:** `build_character_dna()` (Lines 167-258)

```python
def build_character_dna(
    hair_color: str,
    hair_style: str,
    eye_color: str,
    body_type: str,
    breast_size: str,
    butt_size: str,
    extra_prompt: str = ""
) -> str:
```

**What it does:**

- Builds SDXL prompt tags for physical appearance
- Calls `extract_visual_details_from_text()` to parse clothing/accessories from `extra_prompt`
- Adds default traits: `"(no makeup)"`, `"(no piercings)"`, `"(no tattoos)"`
- **CRITICAL:** Does NOT include default clothing - only what's mentioned in extra_prompt

**Output Example:**

```
(1girl), (fair skin:1.2), long straight hair, (blonde hair:1.2), (blue eyes:1.2),
(slim body:1.2), (petite frame:1.1), medium breasts, (small butt:1.1),
youthful appearance, delicate hands, (no makeup), (no piercings), (no tattoos)
```

#### 1.3 Character Saved to Database

**File:** `app/api/miniapp.py` (Lines 1444-1465)

```python
persona = crud.create_persona(
    db,
    name=request.name,
    prompt=dialogue_prompt,  # Personality for dialogue
    image_prompt=character_dna,  # Physical appearance for images
    visibility="custom",
    owner_user_id=user_id
)
```

**Database Schema** (`app/db/models.py`, Lines 65-107):

- `persona.prompt`: Dialogue personality (from `build_dialogue_prompt()`)
- `persona.image_prompt`: Physical DNA (from `build_character_dna()`)
- `persona.intro`: Generic greeting: `f"Hey! I'm {request.name} 💕"`

#### 1.4 Initial Portrait Generation

**File:** `app/api/miniapp.py` (Lines 1473-1526)

**IMPORTANT - First Image Composition:**

```python
first_image_composition = (
    "standing in white room, wearing white lingerie, "
    "portrait shot, head and shoulders framing, face clearly visible, "
    "(upper body:1.2), (face focus:1.3), looking at camera, confident expression, "
    "soft studio lighting, clean white background, "
    "professional photography"
)
```

**Why this matters:**

- This creates the avatar/portrait image
- Hardcoded to show "white lingerie" and "white room"
- This image is stored but **NOT sent to chat** (has `skip_chat_send: true`)
- Sets user expectation for character's appearance

---

### 2. Story Generation Flow

#### 2.1 User Selects "Generate AI Stories"

**File:** `app/api/miniapp.py` (Lines 1242-1320)

**Endpoint:** `/generate-stories`

Calls `generate_character_stories()` to create 3 story scenarios.

#### 2.2 AI Story Generation

**File:** `app/core/story_generator.py` (Lines 10-195)

**Function:** `generate_character_stories()`

**What it does:**

- Analyzes personality traits from `extra_prompt`
- Generates 3 romantic scenarios using Claude 3.5 Sonnet
- Returns stories with:
  - `name`: Story title
  - `small_description`: Preview text
  - `description`: Scene-setting context (2-3 sentences)
  - `text`: Character's opening message

**CRITICAL ISSUES:**

1. **No Image Generation:** Stories are created WITHOUT images
2. **No image_prompt field:** Database saves stories without `image_prompt`
3. **Location mentioned only in description:** Scene location exists in text, but not as structured data

**Example Story Output:**

```json
{
  "name": "Coffee Shop Encounter",
  "description": "You're at a cozy café downtown. Emma spots you and walks over with a warm smile.",
  "text": "Hey! *walks over with a warm smile* I couldn't help but notice you..."
}
```

**What's missing:** `image_prompt` field that would describe:

- Location details
- Character's outfit for this scene
- Pose/composition
- Mood/lighting

#### 2.3 Story Saved to Database

**File:** `app/api/miniapp.py` (Lines 1657-1672) OR `app/core/story_generator.py` return

**Database Schema** (`app/db/models.py`, Lines 109-130):

```python
class PersonaHistoryStart:
    name = Column(String(255))
    small_description = Column(Text)
    description = Column(Text)  # Scene description (text only)
    text = Column(Text)  # Greeting message
    image_url = Column(Text, nullable=True)  # ❌ NULL for custom characters
    image_prompt = Column(Text, nullable=True)  # ❌ NULL for custom characters
```

**PROBLEM:** Custom character stories have:

- ✅ `description`: "You're at a coffee shop..."
- ❌ `image_url`: NULL (no pre-generated image)
- ❌ `image_prompt`: NULL (no SDXL prompt for this scene)

---

### 3. Chat Initialization Flow

#### 3.1 User Starts Chat with History

**File:** `app/bot/handlers/start.py` (Lines 470-602)

**Function:** `create_new_persona_chat_with_history()`

**What happens:**

```python
# Get history from cache/database
history_start = get_persona_history(persona_id, history_id)

history_start_data = {
    "text": history_start["text"],  # ✅ Opening message
    "image_url": history_start["image_url"],  # ❌ NULL
    "image_prompt": history_start.get("image_prompt")  # ❌ NULL
}
description_text = history_start["description"]  # ✅ "You're at coffee shop..."
```

**Messages saved to database:**

1. **System message (role="system"):** The description text
2. **Assistant message (role="assistant"):** The greeting text

**Initial Image Job Creation (Lines 563-572):**

```python
# Create initial ImageJob for continuity if history has image_prompt
if history_start_data and history_start_data.get("image_prompt"):
    crud.create_initial_image_job(
        db, user_id, persona_id, chat_id,
        prompt=history_start_data["image_prompt"],
        result_url=history_start_data.get("image_url")
    )
```

**PROBLEM:** For custom characters, this block is **SKIPPED** because:

- `image_prompt` is NULL
- No initial image job is created
- No visual context is established

#### 3.2 Chat State Initialization

**File:** `app/core/brains/state_resolver.py` (Lines 15-23)

**Function:** `_create_initial_state()`

```python
def _create_initial_state(persona_name: str) -> str:
    return f"""Relationship: stranger, just starting conversation with {persona_name}
Emotions: curious, friendly
Location: online chat room
Scene: Having a casual conversation online
AI Clothing: casual outfit, comfortable clothes
User Clothing: unknown
Mood: Just starting conversation"""
```

**PROBLEM #1 - Generic Default State:**

- Always starts in "online chat room"
- Always wearing "casual outfit, comfortable clothes"
- Ignores history description completely

**Chat state snapshot** (`app/db/models.py` Line 195):

```python
state_snapshot = Column(JSONB, default={})
```

**For new chats:** State is NULL initially, will be created on first user message.

---

### 4. First User Message Flow

#### 4.1 User Sends First Message

**File:** `app/bot/handlers/chat.py` (Lines 74-255)

Message added to Redis queue → Pipeline triggered

#### 4.2 Pipeline Processing

**File:** `app/core/multi_brain_pipeline.py` (Lines 56-177)

**Function:** `process_message_pipeline()`

**Data fetched (Lines 203-254):**

```python
# Get chat history
messages = crud.get_chat_messages(db, chat_id, limit=20)
chat_history = [
    {"role": m.role, "content": m.text}
    for m in messages[-10:]
    if m.text
]

# Get previous state
previous_state = chat.state_snapshot.get("state")  # ❌ NULL for new chat
```

**Chat history for custom character:**

```python
[
    {"role": "system", "content": "You're at a cozy café downtown. Emma spots you..."},
    {"role": "assistant", "content": "Hey! *walks over* I couldn't help but notice you..."}
]
```

**PROBLEM:** `previous_state` is NULL - no state exists yet

#### 4.3 Brain 1: Dialogue Generation

**File:** `app/core/brains/dialogue_specialist.py`

**What it receives:**

- `state`: NULL
- `chat_history`: System description + Assistant greeting
- `user_message`: User's first message
- `persona`: {name, prompt (dialogue personality), image_prompt (DNA)}

**Generates:** AI's dialogue response (text only)

#### 4.4 Brain 2: State Resolution

**File:** `app/core/brains/state_resolver.py` (Lines 76-207)

**Function:** `resolve_state()`

**Since previous_state is NULL, creates initial state:**

**Context sent to LLM (Lines 26-73):**

```python
# LAST 10 MESSAGES
SYSTEM: You're at a cozy café downtown. Emma spots you...
ASSISTANT: Hey! *walks over* I couldn't help but notice you...
USER: [user's message]

# PREVIOUS STATE
No previous state

# PREVIOUS IMAGE SHOWN
[None - no image_prompt was saved]

# STATE UPDATE RULES
- Update state to reflect NEW developments
- Track relationship, location, clothing, mood
```

**LLM generates initial state:**

**PROBLEM #2 - State Created from Limited Context:**

- LLM sees text description of café, but no structured location data
- No `image_prompt` reference for clothing
- Must infer everything from text alone
- Often defaults to generic values

**Typical output:**

```
Relationship: stranger, just met
Emotions: curious, interested
Location: café downtown
Scene: First meeting at a coffee shop
AI Clothing: casual outfit
User Clothing: unknown
Mood: friendly, open
```

**Notice:** "casual outfit" - not specific, no details

---

### 5. Image Generation Flow

#### 5.1 Image Decision (Brain 4)

**File:** `app/core/multi_brain_pipeline.py` (Lines 274-311)

For first 2 messages: **Always YES**

#### 5.2 Image Plan Generation (Brain 3)

**File:** `app/core/brains/image_prompt_engineer.py` (Lines 60-159)

**Function:** `generate_image_plan()`

**Context sent to LLM (Lines 15-57):**

```python
# CONVERSATION STATE
Relationship: stranger, just met
Location: café downtown
AI Clothing: casual outfit
...

# PREVIOUS IMAGE (for continuity)
[None - no previous_image_prompt]

# CHAT HISTORY
SYSTEM: You're at a cozy café downtown...
ASSISTANT: Hey! *walks over*...
USER: [message]
ASSISTANT: [response]

# PERSONA IMAGE DNA
(1girl), (fair skin:1.2), long straight hair, (blonde hair:1.2), ...
[NO CLOTHING SPECIFIED IN DNA]
```

**LLM generates image prompt for this specific moment**

**PROBLEM #3 - No Visual Reference:**

- State says "casual outfit" (generic)
- No previous_image_prompt to maintain continuity
- DNA has no default clothing
- Must infer outfit from conversation context alone

**Likely output:**

```
Character sitting in café, talking across table,
full body shot, café interior in background,
intimate conversation, soft natural lighting
```

**Notice:** No clothing specified → SDXL will render what it thinks fits → often defaults to revealing/nude

#### 5.3 Final Prompt Assembly

**File:** `app/core/brains/image_prompt_engineer.py` (Lines 162+)

**Function:** `assemble_final_prompt()`

```python
positive = f"{image_prompt}, {persona.image_prompt}, {BASE_QUALITY_PROMPT}"
```

**Assembled prompt:**

```
Character sitting in café, talking across table, full body shot, café interior,
intimate conversation, soft natural lighting,
(1girl), (fair skin:1.2), long straight hair, (blonde hair:1.2), (blue eyes:1.2),
(slim body:1.2), medium breasts, (small butt:1.1),
youthful appearance, (no makeup), (no piercings), (no tattoos),
masterpiece, best quality, highly detailed, 8k...
```

**PROBLEM #4 - Missing Clothing:**

- Image prompt: No clothing
- Character DNA: No clothing (unless extracted from extra_prompt)
- Result: SDXL interprets "no clothes specified" → nude/partially clothed

---

## Root Causes Summary

### Issue #1: Characters Always Start Nude

**Primary Causes:**

1. **No Clothing in Character DNA (Root)**

   - `build_character_dna()` only extracts clothing from `extra_prompt`
   - If user doesn't explicitly mention clothes → DNA has no clothing
   - Default traits are negatives: "(no makeup), (no piercings), (no tattoos)"
   - No positive default like "wearing casual clothes"

2. **No Image Prompt in History**

   - Custom character stories have NULL `image_prompt`
   - No initial visual reference for what character wears in this scene
   - First image generated from scratch without clothing guidance

3. **Generic Initial State**

   - `_create_initial_state()` says "casual outfit, comfortable clothes"
   - But this is too vague for SDXL
   - State Resolver must infer specifics from limited context

4. **No Clothing Continuity System**
   - `previous_image_prompt` is NULL for first image
   - No visual memory of what character wore in portrait
   - Each image generated independently

**Code References:**

- `app/core/character_builder.py:167-258` - DNA builder
- `app/core/story_generator.py:10-195` - Story generation (no image_prompt)
- `app/core/brains/state_resolver.py:15-23` - Generic initial state
- `app/core/brains/image_prompt_engineer.py:60-159` - Image plan from state

### Issue #2: Undefined Locations

**Primary Causes:**

1. **Location Only in Text Description**

   - Story has: `description: "You're at a cozy café..."`
   - Saved as system message (text)
   - Not parsed into structured state initially

2. **Initial State Ignores History Description**

   - `_create_initial_state()` hardcodes "online chat room"
   - Doesn't read the system message with actual location
   - State created before considering chat history

3. **State Resolver Must Infer Location**

   - On first user message, LLM receives:
     - System message with location (text)
     - NULL previous state
   - Must create state from scratch
   - Sometimes misses location details

4. **No Structured Scene Metadata**
   - Stories don't have `location`, `time_of_day`, `setting` fields
   - Everything mixed in prose description
   - Harder for LLM to extract reliably

**Code References:**

- `app/core/story_generator.py:79-147` - Story prompt (text only)
- `app/core/brains/state_resolver.py:15-23` - Hardcoded initial state
- `app/db/models.py:109-130` - PersonaHistoryStart schema
- `app/bot/handlers/start.py:523-533` - History data extraction

---

## Comparison: Preset vs Custom Characters

### Preset Characters (Working Correctly)

**Example:** Eva, Kiki, Emma, etc.

**What they have:**

1. **Pre-generated History Images**

   - Each history has `image_url` (Cloudflare CDN)
   - Each history has `image_prompt` (SDXL prompt used)
   - Visual continuity from first message

2. **Detailed Image Prompts**

   - Location: "bedroom at night, dim lighting, moonlight through window"
   - Clothing: "wearing white lace lingerie, garter belt, stockings"
   - Pose: "lying on bed, looking at camera seductively"
   - Mood: "intimate, sensual atmosphere"

3. **Initial Image Job Created**

   - `create_initial_image_job()` is called (Line 435-444 in start.py)
   - Sets `previous_image_prompt` for continuity
   - First user message already has visual context

4. **Location Well-Defined**
   - Description AND image_prompt both specify location
   - State Resolver has visual reference
   - Images maintain consistent setting

**Flow for Eva's "Late Night Texting":**

```
1. User selects history
2. System message: "It's 1 AM, Eva can't sleep..."
3. Assistant message + Image: Shows Eva in bed, dim room, night setting
4. Initial image job: image_prompt = "bedroom at night, dim lighting, Eva lying in bed wearing white lace lingerie..."
5. First user message → State created with:
   - Location: "Eva's bedroom at night"
   - Clothing: "white lace lingerie" (from image_prompt)
   - Scene: specific details from visual
6. Next image maintains continuity via previous_image_prompt
```

### Custom Characters (Broken)

**What they lack:**

1. **No Pre-generated History Images**

   - `image_url`: NULL
   - `image_prompt`: NULL
   - No visual reference at all

2. **Text-Only Scene Description**

   - Description: "You're at a café..."
   - No structured visual data
   - LLM must infer everything

3. **No Initial Image Job**

   - `create_initial_image_job()` skipped (image_prompt is NULL)
   - No visual baseline
   - `previous_image_prompt` starts NULL

4. **Location Inference Only**
   - State Resolver reads text description
   - May or may not extract location correctly
   - No visual confirmation

**Flow for Custom "Café Encounter":**

```
1. User creates character → DNA (no clothing)
2. Generate AI stories → 3 stories (text only)
3. User selects "Café Encounter"
4. System message: "You're at a cozy café..."
5. Assistant message: "Hey! *walks over*..."
6. NO image sent (image_url is NULL)
7. NO initial image job (image_prompt is NULL)
8. First user message → State created from:
   - Previous state: NULL
   - Chat history: Text descriptions only
   - Image reference: NONE
   - Result: "Location: café, Clothing: casual outfit"
9. First image generation:
   - Image prompt: "sitting in café, talking..."
   - Character DNA: Physical traits only (no clothing)
   - Result: SDXL renders nude/partially clothed figure
```

---

## Technical Debt & Architecture Issues

### 1. Two-Track System

- **Preset personas:** Fully supported with pre-generated content
- **Custom personas:** Second-class citizens with missing features
- Code branches based on whether fields are NULL

### 2. Image Prompts as Visual Memory

- `image_prompt` field serves dual purpose:
  - Storage of SDXL prompt used
  - Continuity mechanism for next image
- Custom characters start with no "visual memory"

### 3. State Initialization Problem

- `_create_initial_state()` is generic fallback
- Should be context-aware from history
- Currently ignores available chat history

### 4. Story Generation Incomplete

- `generate_character_stories()` creates text only
- Should also generate initial scene image prompts
- Missing step in pipeline

### 5. Clothing Not First-Class Data

- Clothing is tags buried in prompts
- Should be tracked as state field
- Currently inferred indirectly

---

## Impact on User Experience

### User Journey for Custom Character:

1. **Character Creation:**

   - User specifies physical traits ✅
   - User writes personality: "She's confident and playful, loves coffee and fashion"
   - User EXPECTS: Character will look fashionable, be at coffee shop

2. **Story Generation:**

   - AI generates: "Coffee Shop Encounter - You meet at a trendy café"
   - User EXPECTS: Character will be dressed appropriately for café date

3. **Chat Starts:**

   - Text description: "At cozy café downtown..."
   - User EXPECTS: First image will show character at café, dressed nicely

4. **Reality:**
   - First image: Character nude/semi-nude at café
   - Location: Sometimes correct, sometimes generic
   - User is confused and disappointed

### What Went Wrong:

1. "Loves fashion" → Not converted to "wearing stylish outfit"
2. "Coffee shop" story → No visual of coffee shop outfit created
3. Initial state → Says "casual outfit" but too vague
4. Image generation → No specific clothing → SDXL defaults to suggestive

---

## Proposed Solutions

### Solution A: Generate Image Prompts with Stories (Recommended)

**Modify:** `app/core/story_generator.py`

**Add to AI story generation:**

- Generate `image_prompt` field for each story
- Include: location details, character outfit, pose, lighting
- Store in `PersonaHistoryStart.image_prompt`

**Benefits:**

- Solves both nude and location issues
- Works with existing architecture
- Gives custom characters visual baseline

**Implementation:**

```python
# In generate_character_stories()
# Add to LLM prompt:
"""
For each story, also provide:
- image_prompt: SDXL prompt describing the opening scene
  Include: location, character's outfit, pose, lighting, mood

Example:
{
  "name": "Coffee Date",
  "description": "You meet at a café...",
  "text": "Hey! *waves*...",
  "image_prompt": "cozy café interior, sitting at table, wearing casual chic outfit (skinny jeans, white blouse, brown cardigan), holding coffee cup, warm afternoon lighting, bokeh background, intimate atmosphere"
}
"""
```

### Solution B: Default Clothing in Character DNA

**Modify:** `app/core/character_builder.py`

**Add default clothing to DNA:**

```python
def build_character_dna(...):
    # ... existing code ...

    # Add default clothing if not specified
    if not visual_details or "dress" not in text_lower and "outfit" not in text_lower:
        dna_parts.append("wearing casual outfit (jeans, top)")

    return ", ".join(filter(None, dna_parts))
```

**Benefits:**

- Quick fix for nude issue
- Minimal code change

**Limitations:**

- Doesn't solve location problem
- Generic clothing, not scene-specific

### Solution C: Context-Aware Initial State

**Modify:** `app/core/brains/state_resolver.py`

**Change `_create_initial_state()`:**

```python
def _create_initial_state(persona_name: str, chat_history: list[dict] = None) -> str:
    # Parse system message for location and context
    location = "online chat"
    scene_desc = "casual conversation"

    if chat_history:
        for msg in chat_history:
            if msg["role"] == "system":
                # Extract location from description
                location, scene_desc = parse_scene_description(msg["content"])

    return f"""Relationship: stranger, just starting
Location: {location}
Scene: {scene_desc}
AI Clothing: appropriate outfit for setting
..."""
```

**Benefits:**

- Makes initial state smarter
- Uses available context

**Limitations:**

- Doesn't solve missing visual reference
- "Appropriate outfit" still vague for SDXL

### Solution D: Generate Initial Scene Images (Full Solution)

**Add new pipeline step after story creation:**

1. User generates stories (text only)
2. **NEW:** System generates initial image for each story
   - Calls SDXL with: character DNA + scene description → image
   - Saves `image_url` and `image_prompt` to database
3. When user selects story → has complete visual baseline

**Benefits:**

- Parity with preset characters
- Solves all issues comprehensively
- Best user experience

**Limitations:**

- Most expensive (3 images per character)
- Takes time to generate
- Requires token/cost management

---

## Recommended Implementation Plan

### Phase 1: Quick Fixes (Week 1)

1. **Add default clothing to DNA** (Solution B)

   - Immediate mitigation of nude issue
   - Low risk, fast to implement

2. **Context-aware initial state** (Solution C)
   - Better location inference
   - Uses existing data better

### Phase 2: Story Enhancement (Week 2-3)

3. **Generate image prompts with stories** (Solution A)
   - Update `generate_character_stories()` prompt
   - Add `image_prompt` to story output
   - Save to database
   - Test with existing custom characters

### Phase 3: Full Solution (Week 4-5)

4. **Optional: Pre-generate scene images** (Solution D)
   - Add after story generation
   - Queue 3 image jobs (low priority)
   - Update UI to show loading states
   - Test cost/time impact

### Phase 4: Polish (Week 6)

5. **Improve story generation prompts**

   - Better outfit suggestions based on scene
   - More detailed location descriptions
   - Consistent with character personality

6. **Add clothing state tracking**
   - Add "current_outfit" to state
   - Track outfit changes in conversation
   - Pass to image generation explicitly

---

## Testing Strategy

### Test Case 1: New Custom Character with Clothing Mention

```
Name: "Sarah"
Personality: "Confident businesswoman who loves fashion"
Physical: Blonde, blue eyes, slim, medium
Extra prompt: "She loves wearing elegant dresses and high heels"

Expected:
- DNA includes: "elegant dress, high heels"
- Story image prompts include professional attire
- First image shows character clothed appropriately
```

### Test Case 2: New Custom Character without Clothing Mention

```
Name: "Mia"
Personality: "Shy bookworm who loves reading"
Physical: Brown hair, green eyes, petite, small
Extra prompt: "She's quiet and loves spending time at libraries"

Expected:
- DNA includes default: "casual outfit"
- Story at library includes: "wearing sweater and jeans"
- First image shows character in modest clothing
```

### Test Case 3: Coffee Shop Story

```
Story: "Coffee Date" - "You meet at a cozy café..."

Expected:
- Image prompt includes: "sitting in café, wearing casual chic outfit"
- Location state: "cozy café downtown"
- First image shows: character at café table, fully dressed
```

### Test Case 4: Bedroom Story

```
Story: "Late Night Chat" - "It's midnight, character texts you from bed..."

Expected:
- Image prompt includes: "in bedroom, wearing pajamas/sleepwear"
- Location state: "character's bedroom at night"
- First image shows: appropriate nighttime attire, bedroom setting
```

---

## Code Files to Modify

1. **`app/core/character_builder.py`**

   - Add default clothing to DNA
   - Improve visual detail extraction

2. **`app/core/story_generator.py`**

   - Update AI prompt to generate image_prompts
   - Parse and return image_prompt field
   - Add example outputs to prompt

3. **`app/api/miniapp.py`** (generate-stories endpoint)

   - Save image_prompt when storing stories
   - Optionally: trigger image pre-generation

4. **`app/core/brains/state_resolver.py`**

   - Make `_create_initial_state()` context-aware
   - Parse chat history for scene details
   - Add clothing inference logic

5. **`app/db/crud.py`** (if new fields needed)
   - Update persona history creation
   - Add image_prompt parameter

---

## Success Metrics

After implementation, measure:

1. **Image Quality:**

   - % of first images with appropriate clothing
   - % of images matching scene location
   - User reports of "nude" issue

2. **State Accuracy:**

   - % of chats with correct initial location
   - % of chats with specific (not "casual") clothing in state

3. **User Satisfaction:**

   - Custom character creation completion rate
   - Custom character chat continuation rate
   - User feedback/complaints

4. **Technical:**
   - % of custom character histories with image_prompt
   - Average time to generate story + image prompts
   - Token cost per character creation

---

## Conclusion

The root cause of both issues is the **incomplete custom character pipeline**:

1. **Nude characters:** Missing clothing data throughout the stack

   - DNA has no default clothing
   - Stories have no visual prompts
   - State resolver has no visual reference
   - Image generation works from incomplete data

2. **Undefined locations:** Scene info stays in text, never structured
   - Stories have descriptions (prose) but not prompts (structured)
   - Initial state ignores available context
   - State resolver must infer from limited data

**The fix requires:** Bringing custom characters to parity with preset personas by:

- Adding visual prompts to stories (image_prompt field)
- Ensuring clothing is always specified (DNA defaults + scene outfits)
- Making initial state context-aware (read chat history)
- Optionally pre-generating scene images (like presets have)

With these changes, custom characters will have the same rich visual context as preset personas, resulting in appropriate clothing and clear locations from the very first message.



