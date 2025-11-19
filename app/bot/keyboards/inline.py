"""
Inline keyboard builders
"""
from typing import List, Dict, Any
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from app.settings import get_ui_text


def build_persona_selection_keyboard(
    preset_personas: List[Dict[str, Any]],
    user_personas: List[Dict[str, Any]] = None,
    miniapp_url: str = None,
    language: str = "en"
) -> InlineKeyboardMarkup:
    """Build keyboard for persona selection
    
    Args:
        preset_personas: List of dicts with 'id', 'name', 'key', 'emoji' (optional), 'small_description' (optional)
        user_personas: List of dicts with 'id', 'name', 'key', 'emoji' (optional), 'small_description' (optional)
        miniapp_url: URL for Mini App gallery (optional)
    """
    from app.core.persona_cache import get_persona_field
    
    buttons = []
    
    # Add preset personas with two columns layout
    for i in range(0, len(preset_personas), 2):
        row = []
        # First column
        persona = preset_personas[i]
        emoji = persona.get('emoji', '💕')
        name = get_persona_field(persona, 'name', language=language) or persona['name']
        text = f"{emoji} {name}"
        row.append(InlineKeyboardButton(
            text=text,
            callback_data=f"select_persona:{persona['id']}"
        ))
        
        # Second column (if exists)
        if i + 1 < len(preset_personas):
            persona = preset_personas[i + 1]
            emoji = persona.get('emoji', '💕')
            name = get_persona_field(persona, 'name', language=language) or persona['name']
            text = f"{emoji} {name}"
            row.append(InlineKeyboardButton(
                text=text,
                callback_data=f"select_persona:{persona['id']}"
            ))
        
        buttons.append(row)
    
    # Add user's custom personas
    if user_personas:
        buttons.append([InlineKeyboardButton(text="--- Your Custom Girls ---", callback_data="noop")])
        for i in range(0, len(user_personas), 2):
            row = []
            # First column
            persona = user_personas[i]
            emoji = persona.get('emoji', '✨')
            name = get_persona_field(persona, 'name', language=language) or persona['name']
            text = f"{emoji} {name}"
            row.append(InlineKeyboardButton(
                text=text,
                callback_data=f"select_persona:{persona['id']}"
            ))
            
            # Second column (if exists)
            if i + 1 < len(user_personas):
                persona = user_personas[i + 1]
                emoji = persona.get('emoji', '✨')
                name = get_persona_field(persona, 'name', language=language) or persona['name']
                text = f"{emoji} {name}"
                row.append(InlineKeyboardButton(
                    text=text,
                    callback_data=f"select_persona:{persona['id']}"
                ))
            
            buttons.append(row)
    
    # Add create new button (commented out for now)
    # buttons.append([
    #     InlineKeyboardButton(
    #         text="➕ Create Your Own Girl",
    #         callback_data="create_persona"
    #     )
    # ])
    
    # Add gallery button to browse all characters (opens Mini App directly)
    if miniapp_url:
        buttons.append([
            InlineKeyboardButton(
                text=get_ui_text("miniapp.gallery_button", language=language),
                web_app=WebAppInfo(url=f"{miniapp_url}?page=gallery")
            )
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_confirm_keyboard(action: str, language: str = "en") -> InlineKeyboardMarkup:
    """Build yes/no confirmation keyboard"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=get_ui_text("confirmation.yes", language=language), callback_data=f"confirm:{action}"),
            InlineKeyboardButton(text=get_ui_text("confirmation.no", language=language), callback_data=f"cancel:{action}")
        ]
    ])


def build_persona_actions_keyboard(persona_id: str) -> InlineKeyboardMarkup:
    """Build actions keyboard for a selected persona"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="💬 Start Chatting",
                callback_data=f"select_persona:{persona_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🎨 Generate Image",
                callback_data=f"gen_image:{persona_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="⚙️ Settings",
                callback_data=f"settings:{persona_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Back to List",
                callback_data="show_personas"
            )
        ]
    ])


def build_image_prompt_keyboard() -> InlineKeyboardMarkup:
    """Build keyboard for image generation prompts"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📸 Selfie", callback_data="img_prompt:selfie")],
        [InlineKeyboardButton(text="💋 Flirty Pose", callback_data="img_prompt:flirty")],
        [InlineKeyboardButton(text="😊 Casual Portrait", callback_data="img_prompt:casual")],
        [InlineKeyboardButton(text="✍️ Custom Prompt", callback_data="img_prompt:custom")],
        [InlineKeyboardButton(text="🔙 Cancel", callback_data="cancel_image")]
    ])


def build_image_refresh_keyboard(image_job_id: str) -> InlineKeyboardMarkup:
    """Build keyboard with refresh button for generated images"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Refresh Image", callback_data=f"refresh_image:{image_job_id}")]
    ])


def build_energy_upsell_keyboard(miniapp_url: str, language: str = "en") -> InlineKeyboardMarkup:
    """Build keyboard with button to open premium page in Mini App"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=get_ui_text("miniapp.premium_button", language=language),
            web_app=WebAppInfo(url=f"{miniapp_url}?page=premium")
        )]
    ])


def build_persona_gallery_keyboard(miniapp_url: str, language: str = "en") -> InlineKeyboardMarkup:
    """Build keyboard with button to open persona gallery in Mini App"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=get_ui_text("miniapp.gallery_button", language=language),
            web_app=WebAppInfo(url=f"{miniapp_url}?page=gallery")
        )]
    ])


def build_chat_options_keyboard(persona_id: str, language: str = "en") -> InlineKeyboardMarkup:
    """Build Continue/Start New keyboard for existing conversations"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=get_ui_text("chat_options.continue_button", language=language), 
            callback_data=f"continue_chat:{persona_id}"
        )],
        [InlineKeyboardButton(
            text=get_ui_text("chat_options.start_new_button", language=language), 
            callback_data=f"new_chat_select:{persona_id}"
        )],
        [InlineKeyboardButton(
            text=get_ui_text("chat_options.back_button", language=language), 
            callback_data="show_personas"
        )]
    ])


def build_story_selection_keyboard(stories: List[Dict[str, Any]], persona_id: str = None, language: str = "en") -> InlineKeyboardMarkup:
    """Build keyboard for story/history selection in 2x2 grid
    
    Args:
        stories: List of dicts with 'id', 'name', 'small_description', 'description'
        persona_id: Persona ID for back button (optional, unused for now)
        language: Language code for translations
    """
    from app.core.persona_cache import get_history_field
    
    buttons = []
    
    # Helper function to create a story button
    def create_story_button(story):
        # Get translated name if available
        name = get_history_field(story, 'name', language=language) or story.get('name', 'Story')
        # Try to extract emoji from the beginning of the name
        emoji = ""
        if name and len(name) > 0:
            # Check if first character is emoji (basic check for common emoji ranges)
            first_char = name[0]
            if ord(first_char) > 127:  # Non-ASCII, likely emoji
                emoji = first_char
                name = name[1:].strip()
        
        text = f"{emoji} {name}" if emoji else name
        return InlineKeyboardButton(
            text=text,
            callback_data=f"select_story:{story['id']}"
        )
    
    # Create 2x2 grid: first row has 2 stories, second row has 1 story + back button
    # Row 1: Story 1, Story 2
    row1 = []
    if len(stories) >= 1:
        row1.append(create_story_button(stories[0]))
    if len(stories) >= 2:
        row1.append(create_story_button(stories[1]))
    
    if row1:
        buttons.append(row1)
    
    # Row 2: Story 3, Back button
    row2 = []
    if len(stories) >= 3:
        row2.append(create_story_button(stories[2]))
    
    # Add Back button in second column
    row2.append(InlineKeyboardButton(
        text=get_ui_text("story.back_button", language=language), 
        callback_data="show_personas"
    ))
    
    buttons.append(row2)
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_age_verification_keyboard(deep_link: str = None, language: str = "en") -> InlineKeyboardMarkup:
    """Build keyboard for age verification confirmation
    
    Args:
        deep_link: Optional deep link to pass through callback (e.g., "telegram_ads_kiki3")
    """
    callback_data = "confirm_age_18"
    if deep_link:
        # Encode deep link in callback data (max 64 bytes for callback_data)
        callback_data = f"confirm_age_18:{deep_link}"
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=get_ui_text("age_verification.confirm_button", language=language),
            callback_data=callback_data
        )]
    ])


