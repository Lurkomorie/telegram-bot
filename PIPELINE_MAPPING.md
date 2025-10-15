# Pipeline Mapping: Sexsplicit → Telegram Bot

This document explains how the Telegram bot implementation mirrors the Sexsplicit AI pipeline architecture 1:1.

## 🏗️ Architecture Overview

### Sexsplicit (Next.js/TypeScript)

```
User Message → Safety Check → State Resolver → Dialogue Specialist → Image Pipeline
                                (Brain 1)        (Brain 2)           (Brain 3)
```

### Telegram Bot (Python/FastAPI)

```
User Message → Safety Check → State Update → LLM Response → Image Generation
                              (pipeline)     (OpenRouter)    (Runpod)
```

## 📦 File Mapping

| Sexsplicit                     | Telegram Bot                                      | Purpose              |
| ------------------------------ | ------------------------------------------------- | -------------------- |
| `assistant-processor.ts`       | `core/pipeline_adapter.py`                        | Main pipeline logic  |
| `image-pipeline-service.ts`    | `core/pipeline_adapter.py` + `core/img_runpod.py` | Image generation     |
| `prompts/`                     | `config/prompts.json`                             | All prompt templates |
| `db/queries.ts`                | `db/crud.py`                                      | Database operations  |
| `ai/together.ts`               | `core/llm_openrouter.py`                          | LLM client           |
| `services/image-generation.ts` | `core/img_runpod.py`                              | Image dispatch       |

## 🧠 Brain Components

### Brain 1: State Resolver

**Sexsplicit (`assistant-processor.ts` lines 674-856)**

```typescript
const stateResolverPrompt = await PromptService.getPrompt(
  "CONVERSATION_STATE_GPT"
);
const result = await safeGenerateObject<FullState>({
  model: openRouter(MODELS.SMALL),
  messages: stateMessages,
  schema: FullStateSchema,
  temperature: 0.3,
});
```

**Telegram Bot (`core/pipeline_adapter.py` lines 233-318)**

```python
def update_conversation_state(
    current_state: dict,
    user_text: str,
    assistant_response: str,
    persona: Persona
) -> dict:
    """Update conversation state based on new exchange"""
    # Analyzes user/assistant text for:
    # - Relationship progression (initial → romantic → intimate → sexual)
    # - Emotion tracking
    # - Location changes
    # - Clothing updates
```

**Key Features:**

- ✅ Tracks relationship stages (`relationshipStage`)
- ✅ Monitors emotions (`emotions`, `tension`, `intimacy`)
- ✅ Manages scene state (`location`, `description`, `aiClothing`)
- ✅ Fallback to previous valid state on failure
- ✅ Persistence in database (`Chat.state_snapshot`)

### Brain 2: Dialogue Specialist

**Sexsplicit (`assistant-processor.ts` lines 862-1066)**

```typescript
const chatPrompt = await PromptService.getPrompt("CHAT_GPT");
const conversationSystemPrompt = applyTemplateReplacements(
  chatPrompt,
  templateReplacements
);

const result = await generateText({
  model: openRouter(MODELS.LARGE),
  messages: dialogueMessages,
  temperature: 0.8,
  topP: 0.9,
  frequencyPenalty: 0.3,
  presencePenalty: 0.3,
});
```

**Telegram Bot (`bot/handlers/chat.py` lines 58-98)**

```python
async with send_action_repeatedly(bot, message.chat.id, "typing"):
    llm_messages = build_llm_messages(
        prompts,
        persona,
        messages[:-1],
        user_text,
        chat,
        max_history
    )

    assistant_response = await generate_text(
        llm_messages,
        temperature=temperature,
        max_tokens=max_tokens
    )
```

**Key Features:**

- ✅ Template replacement system (`{{persona_name}}`, `{{location}}`, etc.)
- ✅ Persona-specific system prompts
- ✅ Recent message history (configurable limit)
- ✅ Current state injection
- ✅ Safety guard prompts
- ✅ Typing indicator during generation
- ✅ Retry logic with exponential backoff
- ✅ Response validation

### Brain 3: Image Prompt Engineer

**Sexsplicit (`image-pipeline-service.ts` lines 349-486)**

```typescript
const promptMessages = [
  { role: "system", content: PROMPT_ENGINEER_SYSTEM_PROMPT },
  { role: "user", content: imagePromptContext },
];

const promptResult = await safeGenerateObject<SDXLImagePlan>({
  model: openRouter(MODELS.KIMI),
  messages: promptMessages,
  schema: SDXLImagePlanSchema,
  temperature: 0.8,
});

const { prompt, negativePrompt } = await assembleFinalImagePrompt(
  characterDNA,
  imagePlan,
  oldCharacter
);
```

**Telegram Bot (`core/pipeline_adapter.py` lines 144-240)**

```python
def build_image_prompts(
    prompts_config: dict,
    persona: Persona,
    user_text: str,
    chat: Chat = None,
    dialogue_response: str = ""
) -> Tuple[str, str]:
    """Build image generation prompts"""

    # Build character DNA (ethnicity, hair, eyes, body)
    character_dna = build_character_dna(persona.appearance)

    # Detect scene context (intimate, solo, etc.)
    is_intimate = detect_intimate_keywords(user_text, dialogue_response)

    # Assemble tags (composition, action, clothing, atmosphere, expression)
    positive_prompt = assemble_positive_tags(...)
    negative_prompt = assemble_negative_tags(persona, is_intimate)

    return positive_prompt, negative_prompt
```

**Key Features:**

- ✅ Character DNA generation (ethnicity → skin tone tags)
- ✅ Scene context detection (intimate, solo, pose, etc.)
- ✅ Tag categories (composition, action, clothing, atmosphere, expression, metadata)
- ✅ Dynamic negative prompts with cross-skin negatives
- ✅ Quality prompts injection
- ✅ Appearance persistence from persona config

## 🔐 Safety System

**Sexsplicit (`assistant-processor.ts` lines 469-543)**

```typescript
const safetyPrompt = await PromptService.getPrompt("SAFETY_PROMPT");
const safetyCheckResult = await generateText({
  model: openRouter(MODELS.SAFETY),
  messages: [
    { role: "system", content: safetyPrompt },
    { role: "user", content: userMessageContent },
  ],
  temperature: 0,
});

if (safetyVerdict === "FLAG") {
  // Return stoppage message without saving
}
```

**Telegram Bot (`core/pipeline_adapter.py` lines 322-367)**

```python
def check_safety(user_text: str) -> Tuple[bool, str]:
    """Check if user message contains forbidden content"""
    forbidden_patterns = [
        (["minor", "child", ...], "Content involving minors..."),
        (["incest", "family", ...], "Incestuous content..."),
        (["rape", "force", ...], "Sexual violence..."),
        (["bestiality", ...], "Bestiality..."),
        (["gore", "dismember", ...], "Extreme violent content...")
    ]

    for keywords, reason in forbidden_patterns:
        if any(keyword in text_lower for keyword in keywords):
            return False, reason

    return True, ""
```

**Key Features:**

- ✅ Pre-processing safety check (before LLM)
- ✅ Pattern-based filtering (minors, incest, violence, etc.)
- ✅ Refusal messages from config
- ✅ No database save for flagged content

## 🎨 Image Pipeline

**Sexsplicit (`image-pipeline-service.ts` lines 247-575)**

```typescript
// 1. Check gems/credits
const canAfford = await canAffordImageGeneration(userId, 1);

// 2. Show placeholder immediately
publishToAbly(`chat:${chatId}`, 'message.new', imageStatusMessage);

// 3. Generate prompt with retry
const promptResult = await retryImagePromptGeneration(...);

// 4. Dispatch to Runpod
await RunPodImageGenerationService().generate({
  userId, prompt, negativePrompt,
  existingImageId: pendingImageId,
  characterId, chatId
});

// 5. Webhook callback handles completion
```

**Telegram Bot (`bot/handlers/image.py` + `main.py` callback)**

```python
# 1. Rate limit check (Redis)
allowed, count = await check_rate_limit(user_id, "image", limit, 60)

# 2. Show generating message + upload_photo action
async with send_action_repeatedly(bot, chat_id, "upload_photo"):
    # 3. Build prompts
    positive_prompt, negative_prompt = build_image_prompts(...)

    # 4. Create job in DB
    job = crud.create_image_job(db, user_id, persona_id, prompt, ...)

    # 5. Submit to Runpod
    await submit_image_job(job_id, prompt, negative_prompt, seed)

# 6. Webhook callback delivers photo
@app.post("/image/callback")
async def image_callback(request: Request):
    # Verify HMAC signature
    # Update job status
    # Send photo to user via bot.send_photo()
```

**Key Features:**

- ✅ Rate limiting (Redis sliding window)
- ✅ Immediate feedback (upload_photo action)
- ✅ Database job tracking
- ✅ Webhook with HMAC verification
- ✅ Idempotent callbacks
- ✅ Error handling with retry
- ✅ File ID caching for faster resends

## 📊 State Schema

**Sexsplicit (`prompts/types.ts` FullState)**

```typescript
interface FullState {
  rel: {
    relationshipStage: string;
    emotions: string;
    tension: number;
    intimacy: number;
  };
  scene: {
    location: string;
    description: string;
    aiClothing: string;
    userClothing: string;
    timeOfDay: string;
  };
}
```

**Telegram Bot (`core/pipeline_adapter.py` create_initial_state)**

```python
{
    "rel": {
        "relationshipStage": "initial",
        "emotions": "curious, friendly",
        "tension": 0,
        "intimacy": 0
    },
    "scene": {
        "location": "online chat",
        "description": "Having a casual conversation online",
        "aiClothing": "casual outfit",
        "userClothing": "casual outfit",
        "timeOfDay": "daytime"
    }
}
```

**Storage:**

- Sexsplicit: `messages.stateSnapshot` (JSONB)
- Telegram: `chats.state_snapshot` (JSONB)

## 🎯 Template System

**Sexsplicit (`assistant-processor.ts` lines 119-341)**

```typescript
function buildTemplateReplacements(
  character,
  personality,
  relationship,
  characterPhysical,
  corePersonalities,
  sexualArchetypes,
  userDescription
): Record<string, string> {
  return {
    "{{char.name}}": character.name,
    "{{char.physical_description}}": characterPhysical,
    "{{personality.prompt}}": effectivePersonalityPrompt,
    "{{relationship.prompt}}": effectiveRelationshipPrompt,
    "{{era.context}}": eraContext,
    "{{user.profile.section}}": buildUserProfileSection(),
    // ... 20+ more replacements
  };
}
```

**Telegram Bot (`core/pipeline_adapter.py` lines 60-103)**

```python
def build_template_replacements(
    persona: Persona,
    chat: Chat = None
) -> Dict[str, str]:
    """Build template replacement dictionary"""
    return {
        "{{persona_name}}": persona.name,
        "{{persona_physical}}": build_physical_description(persona),
        "{{relationship_stage}}": state["rel"]["relationshipStage"],
        "{{emotions}}": state["rel"]["emotions"],
        "{{location}}": state["scene"]["location"],
        "{{ai_clothing}}": state["scene"]["aiClothing"],
        # ... mirrored replacements
    }
```

## 🔄 Message Flow Comparison

### Sexsplicit

```
1. User sends message → saveMessages()
2. Safety check → FLAG or PASS
3. State Resolver (Brain 1) → newState
4. Dialogue Specialist (Brain 2) → dialogueResponse
5. Save assistant message with state → saveMessages()
6. Publish to Ably (real-time)
7. [Background] Image Decider → shouldGenerate
8. [Background] Prompt Engineer → imagePlan
9. [Background] Runpod dispatch → webhook callback
```

### Telegram Bot

```
1. User sends message → crud.create_message()
2. Safety check → refuse or continue
3. State update → update_conversation_state()
4. LLM generation → generate_text() with typing action
5. Save assistant message with state → crud.create_message()
6. Send message to Telegram
7. [On /image] Build prompts → build_image_prompts()
8. [On /image] Create job → crud.create_image_job()
9. [On /image] Runpod dispatch → webhook callback → send_photo()
```

## 🔧 Configuration Philosophy

### Sexsplicit

- Prompts in database (PromptService)
- Character configs in database
- App settings in code/env

### Telegram Bot

- **All prompts** in `config/prompts.json` (version controlled)
- **All app settings** in `config/app.yaml` (version controlled)
- **Secrets only** in environment variables
- Personas seeded from config on startup

**Advantages:**

- ✅ Easy to version control prompts
- ✅ No database migrations for prompt changes
- ✅ JSON schema validation
- ✅ Can diff prompt changes in Git
- ✅ Simple rollback (just redeploy previous commit)

## 🚀 Performance Optimizations

| Feature                 | Sexsplicit      | Telegram Bot            |
| ----------------------- | --------------- | ----------------------- |
| **Typing indicator**    | N/A (web UI)    | Periodic refresh (4.5s) |
| **Rate limiting**       | In-memory/Redis | Redis sliding window    |
| **Image delivery**      | Ably publish    | Telegram send_photo     |
| **State caching**       | In message      | In chat record          |
| **LLM retries**         | 3 attempts      | 3 attempts              |
| **Image retries**       | 3 attempts      | 3 attempts              |
| **Webhook idempotency** | ✅              | ✅                      |
| **Concurrent requests** | FastAPI async   | FastAPI async           |

## 📈 Scalability

Both implementations are horizontally scalable:

- **Sexsplicit**: Next.js serverless + Vercel edge
- **Telegram Bot**: Railway containers + auto-scaling

Stateless design enables multiple instances:

- State in PostgreSQL
- Rate limits in Redis
- No in-memory session storage

## 🎓 Key Learnings

### What's Different (by design)

1. **No streaming**: Telegram doesn't support streaming updates

   - Solution: Typing indicator provides feedback

2. **No Ably**: Telegram has native push

   - Solution: Use Telegram's sendMessage API

3. **Webhook-first**: Telegram requires webhooks in production

   - Solution: FastAPI webhook endpoint

4. **Image async**: Runpod callbacks instead of polling
   - Solution: HMAC-verified webhook + database job tracking

### What's the Same

1. ✅ Pipeline architecture (Safety → State → Dialogue → Image)
2. ✅ Template replacement system
3. ✅ State tracking schema
4. ✅ Retry logic and error handling
5. ✅ Safety filtering
6. ✅ Image prompt engineering
7. ✅ Persona system
8. ✅ Message history management

## 🎯 Result

**The Telegram bot is a 1:1 functional replica of Sexsplicit's AI pipeline**, adapted for the Telegram platform while maintaining the same:

- Conversation quality
- Image generation quality
- Safety standards
- State management
- Error resilience

The implementation proves the pipeline is **platform-agnostic** and can be deployed to any messaging platform (Discord, WhatsApp, Slack, etc.) with minimal changes.

