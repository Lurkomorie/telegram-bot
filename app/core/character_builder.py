"""
Character Builder - Creates SDXL prompts and dialogue prompts for custom characters
"""
from typing import Dict

# Attribute mappings for SDXL image generation
HAIR_COLORS: Dict[str, str] = {
    "black": "(black hair:1.2)",
    "brown": "(brown hair:1.2)",
    "blonde": "(blonde hair:1.2)",
    "red": "(red hair:1.2)",
    "white": "(white hair:1.2)",
    "pink": "(pink hair:1.2)",
    "blue": "(blue hair:1.2)",
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
    "slim": "slim body, petite frame",
    "athletic": "athletic body, toned physique",
    "curvy": "curvy body, hourglass figure",
    "voluptuous": "voluptuous body, full figure",
}

BREAST_SIZES: Dict[str, str] = {
    "small": "small breasts",
    "medium": "medium breasts",
    "large": "large breasts",
}

BUTT_SIZES: Dict[str, str] = {
    "small": "small butt",
    "medium": "medium butt",
    "large": "large butt",
}


def build_character_dna(
    hair_color: str,
    hair_style: str,
    eye_color: str,
    body_type: str,
    breast_size: str,
    butt_size: str,
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
    
    Returns:
        SDXL tag string with weighted attributes
    """
    # Get base quality prompt from config (will be added by pipeline)
    # We build the character-specific DNA here
    
    dna_parts = [
        "(1girl)",
        "(fair skin:1.2)",  # Default skin tone, can be customized later
    ]
    
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
    
    # Base physical traits
    dna_parts.extend([
        "youthful appearance",
        "delicate hands",
        "(no piercings)",
        "(no tattoos)",
        "(no makeup)",
    ])
    
    return ", ".join(filter(None, dna_parts))


def build_dialogue_prompt(name: str, extra_prompt: str) -> str:
    """
    Build dialogue personality prompt for the character.
    
    Combines character name with user's personality/relationship description.
    
    Args:
        name: Character name
        extra_prompt: User's description of personality, relationship, background
    
    Returns:
        Complete dialogue prompt for the character
    """
    # Clean up the extra prompt
    extra_prompt = extra_prompt.strip()
    
    # Build comprehensive dialogue prompt
    prompt = f"""You are {name}.

{extra_prompt}

Always stay in character and be engaging, flirty, and maintain a romantic atmosphere. Respond naturally to the user's messages and show genuine interest in them. Be affectionate, playful, and create intimate moments. Remember details about your conversations and reference them to show you care."""
    
    return prompt


def validate_attributes(
    hair_color: str,
    hair_style: str,
    eye_color: str,
    body_type: str,
    breast_size: str,
    butt_size: str,
) -> tuple[bool, str | None]:
    """
    Validate that all attribute choices are valid.
    
    Returns:
        (is_valid, error_field) tuple where error_field is None if valid
    """
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

