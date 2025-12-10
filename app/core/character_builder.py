"""
Character Builder - Creates SDXL prompts and dialogue prompts for custom characters
"""
from typing import Dict

# Attribute mappings for SDXL image generation

RACE_TYPES: Dict[str, str] = {
    "european": "(european woman:1.2), (caucasian:1.1), (fair skin:1.1)",
    "asian": "(asian woman:1.3), (asian facial features:1.2), (east asian:1.1)",
    "african": "(african woman:1.3), (dark skin:1.2), (black african ethnicity:1.1), (ebony skin tone:1.1), (african facial features:1.1), (dark complexion:1.1), (full lips:1.0), (high cheekbones:1.0),",
    "latin": "(latina woman:1.3),(tan skin:1.0), (caramel skin tone:1.0), (full lips:1.0), (high cheekbones:1.0)",
    "elf": "(elf woman:1.3), (pointed elf ears:1.3), (pale radiant skin:1.2), (sharp cheekbones:1.1), (delicate symmetrical face:1.1), (almond-shaped bright eyes:1.1)",
    "catgirl": "(catgirl:1.3), (single pair of fox ears:1.3), (no human ears:1.2), (long fluffy fox tail:1.2), (human face:1.1), (human body:1.1), (small canine teeth:1.0), (slit pupils:1.1), (fur on ears:1.0), (white fur on tail tip:1.0), (human skin tone:1.0), (detailed fur texture:1.0), (hair color matching ear color:1.0)",
    "succubus": "(succubus:1.3), (demon tail:1.2), (red skin:1.2), (glowing eyes:1.2), (sharp angular facial features:1.1), (pronounced canine teeth:1.1)",
}

HAIR_COLORS: Dict[str, str] = {
    "black": "(black hair:1.2)",
    "brown": "(brown hair:1.2)",
    "blonde": "(blonde hair:1.2)",
    "red": "(red hair:1.2)",
    "white": "(white hair:1.2)",
    "pink": "(pink hair:1.2)",
    "blue": "(blue hair:1.2)",
    "green": "(green hair:1.2)",
    "purple": "(purple hair:1.2)",
    "multicolor": "(multicolored hair:1.2, rainbow hair:1.1)",
}

HAIR_STYLES: Dict[str, str] = {
    "long_straight": "long straight hair",
    "long_wavy": "long wavy hair",
    "short": "short hair",
    "ponytail": "ponytail",
    "braided": "braided hair",
    "curly": "curly hair",
}

EYE_COLORS: Dict[str, str] = {
    "brown": "(brown eyes:1.2)",
    "blue": "(blue eyes:1.2)",
    "green": "(green eyes:1.2)",
    "hazel": "(hazel eyes:1.2)",
    "gray": "(gray eyes:1.2)",
}

BODY_TYPES: Dict[str, str] = {
    "slim": "(slim body:1.2), (petite frame:1.1)",
    "athletic": "(athletic body:1.2), (toned physique:1.1), (fit:1.1)",
    "curvy": "(curvy body:1.3), (wide hips:1.1)",
    "voluptuous": "(voluptuous body:1.3), (full figure:1.2), (thick thighs:1.2), (soft curves:1.1)",
}

BREAST_SIZES: Dict[str, str] = {
    "small": "small breasts",
    "medium": "medium breasts",
    "large": "large breasts",
}

BUTT_SIZES: Dict[str, str] = {
    "small": "(small butt:1.1), (petite rear:1.0)",
    "medium": "(medium butt:1.1), (proportional rear:1.0)",
    "large": "(large butt:1.3), (big ass:1.2), (thick rear:1.1)",
}


def extract_visual_details_from_text(text: str) -> str:
    """
    Extract visual/style details from user's free-text description.
    
    Parses makeup, accessories, and permanent body modifications mentioned
    in the character description to include in image generation.
    
    NOTE: Clothing should NOT be extracted here - it comes from STATE, not DNA.
    DNA should only contain permanent physical features.
    
    Args:
        text: User's character description text
    
    Returns:
        Comma-separated SDXL tags for visual details found in text
    """
    if not text:
        return ""
    
    visual_tags = []
    text_lower = text.lower()
    
    # Makeup
    if "lipstick" in text_lower:
        if "red" in text_lower:
            visual_tags.append("(red lipstick:1.3)")
        elif "pink" in text_lower:
            visual_tags.append("pink lipstick")
        elif "dark" in text_lower:
            visual_tags.append("dark lipstick")
        else:
            visual_tags.append("lipstick")
    
    if "makeup" in text_lower:
        if "heavy" in text_lower or "dramatic" in text_lower:
            visual_tags.append("(heavy makeup:1.2)")
        else:
            visual_tags.append("makeup")
    
    if "mascara" in text_lower or "eyeliner" in text_lower:
        visual_tags.append("eye makeup")
    
    # Accessories
    if "glasses" in text_lower:
        visual_tags.append("wearing glasses")
    
    if "earrings" in text_lower:
        visual_tags.append("earrings")
    
    if "necklace" in text_lower:
        visual_tags.append("necklace")
    
    if "bracelet" in text_lower:
        visual_tags.append("bracelet")
    
    # Permanent body modifications
    if "tattoo" in text_lower:
        visual_tags.append("tattoo")
    
    if "piercing" in text_lower:
        visual_tags.append("piercing")
    
    return ", ".join(visual_tags) if visual_tags else ""


def build_character_dna(
    hair_color: str,
    hair_style: str,
    eye_color: str,
    body_type: str,
    breast_size: str,
    butt_size: str,
    extra_prompt: str = "",
    race_type: str = "european"
) -> str:
    """
    Build character DNA string for SDXL image generation.
    
    Returns weighted SDXL tags that define the character's physical appearance.
    This string will be used as the base prompt for all character images.
    
    Args:
        hair_color: Hair color key from HAIR_COLORS
        hair_style: Hair style key from HAIR_STYLES
        eye_color: Eye color key from EYE_COLORS
        body_type: Body type key from BODY_TYPES
        breast_size: Breast size key from BREAST_SIZES
        butt_size: Butt size key from BUTT_SIZES
        extra_prompt: User's custom description (optional, for extracting visual details)
        race_type: Race/ethnicity type key from RACE_TYPES
    
    Returns:
        SDXL tag string with weighted attributes
    """
    # Get base quality prompt from config (will be added by pipeline)
    # We build the character-specific DNA here
    
    dna_parts = [
        "(1girl)",
    ]
    
    # Add race type (includes skin tone and racial features)
    if race_type in RACE_TYPES:
        dna_parts.append(RACE_TYPES[race_type])
    else:
        dna_parts.append("(fair skin:1.2)")  # Default fallback
    
    # Critical identity markers (heavy weight)
    if hair_color in HAIR_COLORS and hair_style in HAIR_STYLES:
        # Combine hair style and color
        style_desc = HAIR_STYLES[hair_style]
        color_tag = HAIR_COLORS[hair_color]
        dna_parts.append(f"{style_desc}, {color_tag}")
    elif hair_color in HAIR_COLORS:
        dna_parts.append(HAIR_COLORS[hair_color])
    elif hair_style in HAIR_STYLES:
        dna_parts.append(HAIR_STYLES[hair_style])
    
    # Eye color
    if eye_color in EYE_COLORS:
        dna_parts.append(EYE_COLORS[eye_color])
    
    # Secondary physical traits (standard weight)
    if body_type in BODY_TYPES:
        dna_parts.append(BODY_TYPES[body_type])
    
    if breast_size in BREAST_SIZES:
        dna_parts.append(BREAST_SIZES[breast_size])
    
    if butt_size in BUTT_SIZES:
        dna_parts.append(BUTT_SIZES[butt_size])
    
    # Extract visual details from user's custom description
    if extra_prompt:
        visual_details = extract_visual_details_from_text(extra_prompt)
        if visual_details:
            dna_parts.append(visual_details)
    
    # Base physical traits (default appearance)
    base_traits = [
        "youthful appearance",
        "delicate hands",
    ]
    
    # Only add "no makeup/piercings/tattoos" if not mentioned in extra_prompt
    if extra_prompt:
        text_lower = extra_prompt.lower()
        if "makeup" not in text_lower and "lipstick" not in text_lower:
            base_traits.append("(no makeup)")
        if "piercing" not in text_lower:
            base_traits.append("(no piercings)")
        if "tattoo" not in text_lower:
            base_traits.append("(no tattoos)")
    else:
        # Defaults when no extra_prompt
        base_traits.extend([
            "(no piercings)",
            "(no tattoos)",
            "(no makeup)",
        ])
    
    dna_parts.extend(base_traits)
    
    return ", ".join(filter(None, dna_parts))


def build_dialogue_prompt(name: str, extra_prompt: str) -> str:
    """
    Build dialogue personality prompt for the character.
    
    Combines character name with user's personality/relationship description.
    Analyzes personality traits to add specific behavioral guidance.
    
    Args:
        name: Character name
        extra_prompt: User's description of personality, relationship, background
    
    Returns:
        Complete dialogue prompt for the character
    """
    # Clean up the extra prompt
    extra_prompt = extra_prompt.strip()
    
    # Analyze personality traits to add specific behavioral notes
    extra_lower = extra_prompt.lower()
    behavioral_notes = []
    
    # Personality-based behavior
    if "shy" in extra_lower or "timid" in extra_lower or "reserved" in extra_lower:
        behavioral_notes.append("You're naturally shy and reserved. You speak softly, blush easily, and take time to open up. You show affection through small gestures rather than bold moves.")
    
    if "confident" in extra_lower or "bold" in extra_lower or "assertive" in extra_lower:
        behavioral_notes.append("You're confident and assertive. You make direct eye contact, speak your mind clearly, and aren't afraid to take initiative in conversations and intimacy.")
    
    if "playful" in extra_lower or "teasing" in extra_lower:
        behavioral_notes.append("You're playful and love teasing. You use humor, witty banter, and playful challenges to keep conversations engaging and fun.")
    
    if "dominant" in extra_lower:
        behavioral_notes.append("You have a dominant personality. You naturally take control, set the pace, and enjoy when others follow your lead.")
    
    if "submissive" in extra_lower:
        behavioral_notes.append("You're submissive by nature. You prefer to follow the other person's lead, seek their approval, and enjoy being guided.")
    
    if "innocent" in extra_lower or "naive" in extra_lower:
        behavioral_notes.append("You're innocent and somewhat naive. You're curious about new experiences but approach them with genuine sweetness and wonder.")
    
    if "flirty" in extra_lower or "seductive" in extra_lower:
        behavioral_notes.append("You're naturally flirtatious and seductive. You use suggestive language, meaningful glances, and body language to create tension and attraction.")
    
    if "romantic" in extra_lower:
        behavioral_notes.append("You're deeply romantic at heart. You focus on emotional connection, intimate moments, and expressing feelings through words and gestures.")
    
    # Add behavioral guidance if traits were detected
    behavioral_section = ""
    if behavioral_notes:
        behavioral_section = "\n\nBEHAVIORAL GUIDANCE:\n" + "\n".join(f"- {note}" for note in behavioral_notes)
    
    # Build comprehensive dialogue prompt
    prompt = f"""You are {name}.

{extra_prompt}{behavioral_section}

CORE DIRECTIVES:
- Stay in character at all times - your personality should be evident in every response
- Be engaging, emotionally present, and responsive to the user's messages
- Show genuine interest through questions, reactions, and remembering details
- Create a romantic atmosphere appropriate to your personality
- Let your unique traits shine through your word choice, actions, and reactions
- Be affectionate in ways that match your personality (shy = subtle gestures, bold = direct affection)
- Evolve the relationship naturally based on the conversation flow"""
    
    return prompt


def validate_attributes(
    hair_color: str,
    hair_style: str,
    eye_color: str,
    body_type: str,
    breast_size: str,
    butt_size: str,
    race_type: str = "european",
) -> tuple[bool, str | None]:
    """
    Validate that all attribute choices are valid.
    
    Returns:
        (is_valid, error_field) tuple where error_field is None if valid
    """
    if race_type not in RACE_TYPES:
        return False, "race_type"
    if hair_color not in HAIR_COLORS:
        return False, "hair_color"
    if hair_style not in HAIR_STYLES:
        return False, "hair_style"
    if eye_color not in EYE_COLORS:
        return False, "eye_color"
    if body_type not in BODY_TYPES:
        return False, "body_type"
    if breast_size not in BREAST_SIZES:
        return False, "breast_size"
    if butt_size not in BUTT_SIZES:
        return False, "butt_size"
    
    return True, None

