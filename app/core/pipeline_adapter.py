"""
Pipeline Adapter - Mirrors Sexsplicit AI pipeline logic 1:1
Replicates assistant-processor.ts and image-pipeline-service.ts behaviors
"""
import json
from typing import Dict, List, Optional, Tuple, Union
from app.db.models import Persona, Chat, Message


# ========== CONVERSATION STATE MANAGEMENT ==========
# Mirrors createInitialState and FullState from Sexsplicit

def create_initial_state(persona: Union[Persona, dict]) -> dict:
    """Create initial conversation state (mirrors createInitialState from Sexsplicit)"""
    return {
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


def parse_previous_state(state_snapshot: dict) -> Optional[dict]:
    """Parse and validate previous state from DB"""
    if not state_snapshot or not isinstance(state_snapshot, dict):
        return None
    
    # Validate required keys
    if "rel" not in state_snapshot or "scene" not in state_snapshot:
        return None
    
    return state_snapshot


def find_best_previous_state(messages: List[Message], persona: Persona) -> dict:
    """
    Find the most recent valid state from message history
    Mirrors findBestPreviousState from assistant-processor.ts
    """
    # Look for the most recent assistant message with a valid stateSnapshot
    # (In Telegram, we store state in Chat.state_snapshot instead)
    # This is a fallback if Chat.state_snapshot is missing
    
    for msg in reversed(messages):
        if msg.role == "assistant" and msg.media and "stateSnapshot" in msg.media:
            state = parse_previous_state(msg.media.get("stateSnapshot"))
            if state:
                return state
    
    # Fallback: create initial state
    return create_initial_state(persona)


# ========== PROMPT ASSEMBLY ==========
# Mirrors buildTemplateReplacements and applyTemplateReplacements

def build_template_replacements(persona: Union[Persona, dict], chat: Union[Chat, dict] = None) -> Dict[str, str]:
    """Build template replacement dictionary for prompts"""
    # Handle persona as dict or ORM object
    if isinstance(persona, dict):
        persona_name = persona.get("name", "AI")
    else:
        persona_name = persona.name
    
    # Get current state
    state = {}
    if chat:
        if isinstance(chat, dict):
            state = chat.get("state_snapshot", {})
        else:
            state = chat.state_snapshot or {}
    
    if not state:
        state = create_initial_state(persona)
    
    rel = state.get("rel", {})
    scene = state.get("scene", {})
    
    replacements = {
        "{{persona_name}}": persona_name,
        "{{persona_physical}}": "attractive woman",  # Simplified - details in persona.image_prompt
        "{{persona_style}}": "casual clothing",
        "{{relationship_stage}}": rel.get("relationshipStage", "initial"),
        "{{emotions}}": rel.get("emotions", "neutral"),
        "{{location}}": scene.get("location", "unknown"),
        "{{scene_description}}": scene.get("description", "conversing"),
        "{{ai_clothing}}": scene.get("aiClothing", "casual outfit"),
    }
    
    return replacements


def apply_template_replacements(template: str, replacements: Dict[str, str]) -> str:
    """Apply template replacements (mirrors applyTemplateReplacements)"""
    result = template
    for key, value in replacements.items():
        result = result.replace(key, value)
    return result


# ========== LLM MESSAGE ASSEMBLY ==========
# Mirrors the dialogue specialist prompt assembly

def build_llm_messages(
    prompts_config: dict,
    persona: Union[Persona, dict],
    messages: Union[List[Message], List[dict]],
    user_text: str,
    chat: Union[Chat, dict] = None,
    max_history: int = 10
) -> List[Dict[str, str]]:
    """
    Build complete message array for LLM
    Mirrors the DIALOGUE_SPECIALIST_SYSTEM_PROMPT assembly from Sexsplicit
    """
    # Get template replacements
    replacements = build_template_replacements(persona, chat)
    
    # Build system prompt
    system_base = prompts_config["system"]["default"]
    system_base = apply_template_replacements(system_base, replacements)
    
    # Add persona-specific system prompt (using 'prompt' field)
    persona_prompt = persona.get("prompt") if isinstance(persona, dict) else (persona.prompt or "")
    persona_prompt = persona_prompt or ""
    
    # Add conversation state context
    state_context = prompts_config["system"].get("conversation_state", "")
    
    # Get current state
    if chat:
        if isinstance(chat, dict):
            state = chat.get("state_snapshot") or create_initial_state(persona)
        else:
            state = chat.state_snapshot or create_initial_state(persona)
    else:
        state = create_initial_state(persona)
    state_json = json.dumps(state, indent=2)
    
    # Assemble full system prompt (mirrors conversationSystemPrompt from assistant-processor.ts)
    system_full = f"""{system_base}

{persona_prompt}

{state_context}

# CURRENT SCENE & STATE
- Location: {state['scene']['location']}
- Scene: {state['scene']['description']}
- Your Clothing: {state['scene']['aiClothing']}
- Relationship Stage: {state['rel']['relationshipStage']}
- Your Current Emotions: {state['rel']['emotions']}

# CURRENT STATE (Full)
{state_json}
"""
    
    # Build message array
    llm_messages = [{"role": "system", "content": system_full}]
    
    # Add recent conversation history (mirrors formatChatHistoryAsMessages)
    recent_messages = messages[-max_history:] if len(messages) > max_history else messages
    
    for msg in recent_messages:
        # Handle both dict and ORM objects
        if isinstance(msg, dict):
            role = msg.get("role")
            text = msg.get("text", "")
        else:
            role = msg.role
            text = msg.text or ""
        
        if role in ("user", "assistant"):
            llm_messages.append({
                "role": role,
                "content": text
            })
    
    # Add current user message
    llm_messages.append({
        "role": "user",
        "content": user_text
    })
    
    return llm_messages


# ========== IMAGE PROMPT ENGINEERING ==========
# Mirrors PROMPT_ENGINEER_SYSTEM_PROMPT and assembleFinalImagePrompt

BASE_QUALITY_PROMPT = "(masterpiece, best quality:1.2, ultra high res, detailed, very aesthetic), smooth shading, clean lines, physically-plausible lighting, detailed face, detailed eyes, natural anatomy, proportional body, realistic hands and fingers, defined knuckles, photorealistic skin texture, sharp focus, coherent limbs"

BASE_NEGATIVE_PROMPT = "(worst quality, lowres, jpeg artifacts, deformed, mutated, disfigured, extra heads:1.4), duplicate person, twins, clones, mirrored body, (extra arms:1.3), (extra legs:1.3), (extra hands:1.35), (extra fingers:1.45), missing fingers, fused fingers, webbed fingers, long fingers, broken wrist, broken limb, amputated limb, floating limbs, disconnected limbs, cropped head, out of frame face, headless, faceless, (multiple heads:1.4), lazy eye, crossed eyes, deformed pupils, (wonky eyes:1.2), blur, motion blur, oversharpen, oversaturated, watermark, signature, text, logo, frame, border, bad hands, bad anatomy, bad proportions, unnatural body bend, mangled feet, mirror, reflection, distorted reflection, merged legs, fused thighs, twisted hips, unnatural overlapping limbs, entangled legs, siamese body, body fusion, conjoined anatomy"


def build_image_prompts(
    prompts_config: dict,
    persona: Union[Persona, dict],
    user_text: str,
    chat: Union[Chat, dict] = None,
    dialogue_response: str = ""
) -> Tuple[str, str]:
    """
    Build image generation prompts (positive and negative)
    Uses persona.image_prompt directly for character appearance
    """
    # Get persona's image prompt (character appearance tags)
    if isinstance(persona, dict):
        character_dna = persona.get("image_prompt") or ""
    else:
        character_dna = persona.image_prompt or ""
    
    # Get current state
    state = {}
    if chat:
        if isinstance(chat, dict):
            state = chat.get("state_snapshot") or {}
        else:
            state = chat.state_snapshot or {}
    
    if not state:
        state = create_initial_state(persona)
    
    # Analyze user request and dialogue for scene context
    combined_text = f"{user_text} {dialogue_response}".lower()
    
    # Composition tags
    composition_tags = ["1girl"]
    
    # Detect if it's a couple/intimate scene
    intimate_keywords = ["kiss", "embrace", "hug", "together", "us", "cuddle", "hold me", "touch"]
    is_intimate = any(kw in combined_text for kw in intimate_keywords)
    
    if is_intimate:
        composition_tags = ["1girl", "1boy", "couple", "intimate"]
    
    # Action tags (mirrors your action detection)
    action_tags = []
    if "selfie" in combined_text:
        action_tags.append("taking selfie")
    if "pose" in combined_text or "posing" in combined_text:
        action_tags.append("posing")
    if "smile" in combined_text or "smiling" in combined_text:
        action_tags.append("smiling")
    if "look" in combined_text and "camera" in combined_text:
        action_tags.append("looking at viewer")
    
    # Clothing tags (from state)
    scene = state.get("scene", {})
    rel = state.get("rel", {})
    clothing = scene.get("aiClothing", "casual outfit")
    clothing_tags = [clothing]
    
    # Atmosphere tags (from state and context)
    location = scene.get("location", "indoors")
    time_of_day = scene.get("timeOfDay", "daytime")
    atmosphere_tags = [location, time_of_day]
    
    # Expression tags (from state emotions)
    emotions = rel.get("emotions", "neutral")
    expression_tags = []
    if "happy" in emotions or "cheerful" in emotions:
        expression_tags.append("happy expression")
    if "flirty" in emotions or "seductive" in emotions:
        expression_tags.append("seductive expression")
    if "shy" in emotions:
        expression_tags.append("shy expression")
    if "playful" in emotions:
        expression_tags.append("playful expression")
    
    # Metadata tags
    metadata_tags = ["realistic", "photorealistic", "detailed face", "detailed eyes"]
    
    # Assemble positive prompt (mirrors assembleFinalImagePrompt)
    positive_parts = (
        composition_tags +
        action_tags +
        clothing_tags +
        atmosphere_tags +
        expression_tags +
        metadata_tags +
        [character_dna, BASE_QUALITY_PROMPT]
    )
    
    positive_prompt = ", ".join(filter(None, positive_parts))
    
    # Assemble negative prompt (use base negative prompt)
    negative_prompt = BASE_NEGATIVE_PROMPT
    
    # Add cross-skin negatives for intimate scenes (mirrors your cross-negative logic)
    if is_intimate:
        # Add negatives to prevent skin tone bleeding
        negative_prompt += ", same skin tone, matching skin, identical skin color"
    
    return positive_prompt, negative_prompt


# ========== STATE RESOLUTION ==========
# Mirrors Brain 1: State Resolver from assistant-processor.ts

def update_conversation_state(
    current_state: dict,
    user_text: str,
    assistant_response: str,
    persona: Union[Persona, dict]
) -> dict:
    """
    Update conversation state based on new exchange
    Simplified version - in production, you'd call an LLM to analyze and update state
    Mirrors the STATE_RESOLVER logic from Sexsplicit
    """
    new_state = current_state.copy()
    
    combined_text = f"{user_text} {assistant_response}".lower()
    
    # Update relationship progression
    rel = new_state.get("rel", {})
    current_stage = rel.get("relationshipStage", "initial")
    
    # Detect intimacy progression
    intimate_keywords = ["kiss", "love", "intimate", "close", "together"]
    romantic_keywords = ["date", "romantic", "feelings", "heart"]
    sexual_keywords = ["bed", "bedroom", "naked", "touch me", "want you"]
    
    if any(kw in combined_text for kw in sexual_keywords) and current_stage != "sexual":
        rel["relationshipStage"] = "sexual"
        rel["intimacy"] = min(rel.get("intimacy", 0) + 30, 100)
    elif any(kw in combined_text for kw in intimate_keywords) and current_stage == "initial":
        rel["relationshipStage"] = "intimate"
        rel["intimacy"] = min(rel.get("intimacy", 0) + 20, 100)
    elif any(kw in combined_text for kw in romantic_keywords) and current_stage == "initial":
        rel["relationshipStage"] = "romantic"
        rel["intimacy"] = min(rel.get("intimacy", 0) + 10, 100)
    
    # Update emotions based on content
    if "happy" in combined_text or "glad" in combined_text:
        rel["emotions"] = "happy, warm"
    elif "flirt" in combined_text or "tease" in combined_text:
        rel["emotions"] = "flirty, playful"
    elif "sad" in combined_text or "upset" in combined_text:
        rel["emotions"] = "concerned, supportive"
    else:
        rel["emotions"] = "engaged, attentive"
    
    new_state["rel"] = rel
    
    # Update scene if location mentioned
    scene = new_state.get("scene", {})
    
    location_keywords = {
        "bedroom": "bedroom",
        "bed": "bedroom",
        "kitchen": "kitchen",
        "outside": "outdoors",
        "park": "park",
        "cafe": "cafe",
        "restaurant": "restaurant",
        "beach": "beach"
    }
    
    for keyword, location in location_keywords.items():
        if keyword in combined_text:
            scene["location"] = location
            scene["description"] = f"Spending time together in {location}"
            break
    
    # Update clothing if mentioned
    clothing_keywords = {
        "dress": "cute dress",
        "lingerie": "lingerie",
        "bikini": "bikini",
        "pajamas": "pajamas",
        "workout": "workout outfit",
        "naked": "nothing",
        "nude": "nothing"
    }
    
    for keyword, clothing in clothing_keywords.items():
        if keyword in combined_text:
            scene["aiClothing"] = clothing
            break
    
    new_state["scene"] = scene
    
    return new_state


# ========== SAFETY FILTER ==========
# Mirrors SAFETY_PROMPT logic from assistant-processor.ts

def check_safety(user_text: str) -> Tuple[bool, str]:
    """
    Check if user message contains forbidden content
    Returns (is_safe, reason)
    Mirrors the safety filter from Sexsplicit
    """
    text_lower = user_text.lower()
    
    # Forbidden keywords (mirrors your safety rules)
    forbidden_patterns = [
        # Minors
        (["minor", "child", "kid", "underage", "teen", "young", "little girl", "little boy", "daughter", "son"], 
         "Content involving minors is not allowed"),
        
        # Incest
        (["mom", "mother", "dad", "father", "sister", "brother", "daughter", "son", "incest", "family"], 
         "Incestuous content is not allowed"),
        
        # Sexual violence
        (["rape", "force", "non-consent", "against will", "sexual assault"], 
         "Sexual violence content is not allowed"),
        
        # Bestiality
        (["animal", "dog", "horse", "bestiality", "zoophilia"], 
         "Bestiality content is not allowed"),
        
        # Extreme content
        (["gore", "dismember", "snuff", "murder", "kill", "death", "blood"], 
         "Extreme violent content is not allowed"),
    ]
    
    for keywords, reason in forbidden_patterns:
        if any(keyword in text_lower for keyword in keywords):
            return False, reason
    
    return True, ""


