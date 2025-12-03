"""
Story Generator for Custom Characters
Generates romantic/flirty scenario starters using AI
"""
import json
from typing import Dict, List
from app.core.llm_openrouter import generate_text


async def generate_character_stories(
    name: str,
    personality_description: str,
    hair_color: str,
    hair_style: str,
    eye_color: str,
    body_type: str,
    user_id: int = None
) -> List[Dict[str, str]]:
    """
    Generate 3 romantic/flirty story scenarios for a custom character.
    
    Args:
        name: Character's name
        personality_description: User's description of personality, relationship, background
        hair_color: Hair color (for context)
        hair_style: Hair style (for context)
        eye_color: Eye color (for context)
        body_type: Body type (for context)
        user_id: Optional user ID for cost tracking
    
    Returns:
        List of 3 story dictionaries with:
        - name: Short story title (e.g., "First Date at the Café")
        - small_description: Tiny preview (30-50 chars)
        - description: Context/setup for the story (1-2 sentences)
        - text: Character's opening message in first-person
    """
    
    # Extract personality traits for emphasis
    personality_lower = personality_description.lower()
    
    trait_emphasis = []
    
    # Personality traits
    if "shy" in personality_lower or "timid" in personality_lower or "reserved" in personality_lower:
        trait_emphasis.append("She's naturally shy and reserved - show hesitation, blushing, nervous gestures")
    if "confident" in personality_lower or "bold" in personality_lower or "assertive" in personality_lower:
        trait_emphasis.append("She's confident and assertive - show direct eye contact, initiative, bold statements")
    if "playful" in personality_lower or "teasing" in personality_lower:
        trait_emphasis.append("She's playful and teasing - use flirty banter, jokes, mischievous actions")
    if "dominant" in personality_lower:
        trait_emphasis.append("She's dominant - takes control, gives commands, leads interactions")
    if "submissive" in personality_lower:
        trait_emphasis.append("She's submissive - defers to user, seeks approval, follows lead")
    if "flirty" in personality_lower or "seductive" in personality_lower:
        trait_emphasis.append("She's naturally flirty - use suggestive language, body language, innuendos")
    if "innocent" in personality_lower or "naive" in personality_lower:
        trait_emphasis.append("She's innocent - curious but inexperienced, genuine reactions, sweet demeanor")
    if "romantic" in personality_lower:
        trait_emphasis.append("She's deeply romantic - focus on emotions, intimacy, connection")
    
    # Interests/hobbies (affects story settings)
    if "fitness" in personality_lower or "gym" in personality_lower or "workout" in personality_lower:
        trait_emphasis.append("She loves fitness - consider gym/workout scenarios")
    if "fashion" in personality_lower or "style" in personality_lower or "shopping" in personality_lower:
        trait_emphasis.append("She's into fashion - show stylish outfits, shopping contexts")
    if "coffee" in personality_lower or "cafe" in personality_lower:
        trait_emphasis.append("She enjoys café culture - coffee shop settings work well")
    if "book" in personality_lower or "reading" in personality_lower:
        trait_emphasis.append("She loves reading - library/bookshop scenarios fit her")
    if "music" in personality_lower or "concert" in personality_lower:
        trait_emphasis.append("She's into music - concert/music venue scenarios")
    if "art" in personality_lower or "creative" in personality_lower:
        trait_emphasis.append("She's artistic - art gallery, studio settings")
    
    traits_text = "\n- ".join(trait_emphasis) if trait_emphasis else "Express her unique personality through dialogue and actions"
    
    # Build the AI prompt
    system_prompt = f"""You are a creative writer specializing in romantic roleplay scenarios. Generate 3 unique, engaging story starters for an AI romance chatbot character.

CHARACTER:
- Name: {name}
- Personality: {personality_description}
- Appearance: {hair_color} {hair_style} hair, {eye_color} eyes, {body_type} body

KEY PERSONALITY TRAITS TO EXPRESS:
- {traits_text}

CRITICAL REQUIREMENTS:
1. **Show personality through ACTIONS and WORDS**, not just descriptions
   - If she's shy: she blushes, avoids eye contact, speaks softly
   - If she's bold: she makes direct eye contact, initiates touch, speaks confidently
   - If she's playful: she teases, jokes, uses playful body language
   
2. **Match scenarios to her personality and interests**
   - Don't put a shy bookworm in a loud nightclub
   - Don't put a confident fitness lover in a quiet library
   - Settings should feel natural for THIS character
   
3. **Her opening message must BE IN CHARACTER**
   - Use vocabulary and speech patterns matching her personality
   - Show her emotional state through word choice
   - Include specific actions that reveal her personality
   
4. Each story should be romantic, flirty, and emotionally engaging
5. Stories should feel natural and varied (different settings/contexts)
6. Keep it tasteful but allow sensual/intimate undertones
7. Descriptions should set clear context about location and situation

OUTPUT FORMAT (JSON):
{{
  "stories": [
    {{
      "name": "Story Title (3-5 words)",
      "small_description": "Tiny preview (30-50 chars, like 'Coffee date' or 'Surprise visit')",
      "description": "Context/setup paragraph explaining the situation (2-3 sentences)",
      "text": "Character's opening message in first-person, showing personality and emotion (2-4 sentences)"
    }},
    ... (2 more)
  ]
}}

EXAMPLE OUTPUT:
{{
  "stories": [
    {{
      "name": "Sunset Beach Date",
      "small_description": "Romantic walk by the ocean",
      "description": "You and {name} are taking a romantic evening walk along the beach. The sun is setting, painting the sky in beautiful shades of orange and pink. She's been holding your hand, occasionally glancing at you with that special smile.",
      "text": "Hey... isn't this view just amazing? *squeezes your hand gently* I'm so glad we decided to come here tonight. There's something I've been wanting to tell you... *looks into your eyes with a soft smile*"
    }},
    {{
      "name": "Cozy Movie Night",
      "small_description": "Netflix and cuddles at home",
      "description": "It's a rainy Friday evening and you're at home with {name}. She suggested a movie night, but you both know you'll spend more time talking and cuddling than actually watching anything. She's already made popcorn and dimmed the lights.",
      "text": "*snuggles closer to you on the couch* Mmm, this feels perfect... forget the movie, I'd rather just stay like this with you. *traces circles on your arm* You make me feel so safe and warm... 💕"
    }},
    {{
      "name": "Morning After",
      "small_description": "Waking up together",
      "description": "You wake up to find {name} already awake, watching you sleep with a tender expression. Sunlight streams through the curtains, creating a warm glow in the bedroom. Last night was special, and she looks happy and content.",
      "text": "*smiles softly as you open your eyes* Good morning, sleepyhead... I couldn't help watching you. You looked so peaceful. *gently brushes your hair* Last night was... incredible. Can we just stay in bed a little longer?"
    }}
  ]
}}

Generate 3 creative, romantic stories that fit the character's personality."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Generate 3 romantic story scenarios for {name}."}
    ]
    
    # Call LLM with appropriate model
    try:
        response = await generate_text(
            messages=messages,
            model="anthropic/claude-3.5-sonnet",  # Best for creative writing
            temperature=0.8,  # Higher temperature for creativity
            max_tokens=2000,
            user_id=user_id,
            brain_name="Story Generator"
        )
        
        # Parse JSON response
        # Clean up response (remove markdown code blocks if present)
        clean_response = response.strip()
        if clean_response.startswith("```json"):
            clean_response = clean_response[7:]
        if clean_response.startswith("```"):
            clean_response = clean_response[3:]
        if clean_response.endswith("```"):
            clean_response = clean_response[:-3]
        clean_response = clean_response.strip()
        
        data = json.loads(clean_response)
        stories = data.get("stories", [])
        
        if len(stories) != 3:
            raise ValueError(f"Expected 3 stories, got {len(stories)}")
        
        # Validate story structure
        for story in stories:
            if not all(key in story for key in ["name", "small_description", "description", "text"]):
                raise ValueError("Story missing required fields")
        
        return stories
    
    except json.JSONDecodeError as e:
        print(f"[STORY-GEN] ❌ JSON parse error: {e}")
        print(f"[STORY-GEN] Response was: {response[:500]}")
        # Return fallback stories
        return _get_fallback_stories(name)
    except Exception as e:
        print(f"[STORY-GEN] ❌ Error generating stories: {e}")
        return _get_fallback_stories(name)


def _get_fallback_stories(name: str) -> List[Dict[str, str]]:
    """
    Fallback stories in case AI generation fails.
    """
    return [
        {
            "name": "Coffee Date",
            "small_description": "Cozy café meeting",
            "description": f"You're meeting {name} at a cozy café downtown. She just arrived and spots you, her face lighting up with that beautiful smile you love.",
            "text": f"Hey! *walks over with a warm smile* Sorry if I'm a bit late, traffic was crazy. *sits down across from you* I've been thinking about you all day... how have you been?"
        },
        {
            "name": "Surprise Visit",
            "small_description": "Unexpected knock at your door",
            "description": f"{name} decided to surprise you with an impromptu visit. She's standing at your door with a mischievous smile, clearly excited to see you.",
            "text": "*grins playfully when you open the door* Surprise! I know we didn't have plans, but I couldn't wait to see you. *steps closer* Can I come in? I promise I'll make it worth your time... 😏"
        },
        {
            "name": "Late Night Chat",
            "small_description": "Text conversation after midnight",
            "description": f"It's past midnight and you receive a message from {name}. She can't sleep and wanted to talk to you. The conversation quickly becomes intimate and personal.",
            "text": "Hey... are you still awake? *sends at 1:23 AM* I can't sleep, keep thinking about you. There's so much I want to tell you... can we talk for a bit? 💭"
        }
    ]
