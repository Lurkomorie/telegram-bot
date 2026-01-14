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
        
        # Add create girlfriend button
        buttons.append([
            InlineKeyboardButton(
                text=get_ui_text("welcome.create_girlfriend_button", language=language),
                web_app=WebAppInfo(url=f"{miniapp_url}?page=gallery&create=true")
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


def build_energy_upsell_keyboard(
    miniapp_url: str, 
    language: str = "en", 
    message_variant: int = 1, 
    button_variant: int = 1,
    button_count: int = 1,
    button2_variant: int = 2
) -> InlineKeyboardMarkup:
    """Build keyboard with one or two buttons for energy upsell A/B test.
    
    Button leads to premium page. All variants are included in callback data for tracking.
    
    Args:
        miniapp_url: Base miniapp URL
        language: User language code
        message_variant: Which message variant was shown (1-4)
        button_variant: Which button text to show for first button (1-4)
        button_count: How many buttons to show (1 or 2)
        button2_variant: Which button text for second button (1-4), used when button_count=2
    """
    # Get first button text based on variant
    button_key = f"tokens.outOfTokens.button{button_variant}"
    button_text = get_ui_text(button_key, language=language)
    
    buttons = [
        [InlineKeyboardButton(
            text=button_text,
            callback_data=f"upsell_click:{message_variant}:{button_variant}:{button_count}"
        )]
    ]
    
    # Add second button if button_count is 2
    if button_count == 2:
        button2_key = f"tokens.outOfTokens.button{button2_variant}"
        button2_text = get_ui_text(button2_key, language=language)
        buttons.append([InlineKeyboardButton(
            text=button2_text,
            callback_data=f"upsell_click:{message_variant}:{button2_variant}:{button_count}"
        )])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


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
        # Generate image button temporarily disabled
        # [InlineKeyboardButton(
        #     text=get_ui_text("image.generate_button", language=language), 
        #     callback_data=f"generate_image_for_persona:{persona_id}"
        # )],
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
        persona_id: Persona ID for back button
        language: Language code for translations
    """
    from app.core.persona_cache import get_history_field
    
    buttons = []
    
    # Generate image button temporarily disabled
    # if persona_id:
    #     buttons.append([InlineKeyboardButton(
    #         text=get_ui_text("image.generate_button", language=language),
    #         callback_data=f"generate_image_for_persona:{persona_id}"
    #     )])
    
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


def build_no_active_chat_keyboard(language: str = "en") -> InlineKeyboardMarkup:
    """Build keyboard with Start button for when user has no active chat"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=get_ui_text("no_active_chat.start_button", language=language),
            callback_data="trigger_start"
        )]
    ])


def build_another_image_keyboard(language: str = "en") -> InlineKeyboardMarkup:
    """Build keyboard for confirming another image generation"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=get_ui_text("image.confirm_another", language=language),
            callback_data="confirm_another_image"
        )],
        [InlineKeyboardButton(
            text=get_ui_text("image.cancel_another", language=language),
            callback_data="cancel_another_image"
        )],
        [InlineKeyboardButton(
            text=get_ui_text("common.main_menu", language=language),
            callback_data="trigger_start"
        )]
    ])


def build_age_verification_keyboard(deep_link: str = None, language: str = "en") -> InlineKeyboardMarkup:
    """Build keyboard for age verification with language selection
    
    Args:
        deep_link: Optional deep link to pass through callback (e.g., "telegram_ads_kiki3")
    """
    # Build callback data with optional deep link
    en_callback = "confirm_age_lang:en"
    ru_callback = "confirm_age_lang:ru"
    
    if deep_link:
        # Encode deep link in callback data (max 64 bytes for callback_data)
        en_callback = f"confirm_age_lang:en:{deep_link}"
        ru_callback = f"confirm_age_lang:ru:{deep_link}"
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🇬🇧 English",
                callback_data=en_callback
            ),
            InlineKeyboardButton(
                text="🇷🇺 Русский",
                callback_data=ru_callback
            )
        ]
    ])


def build_voice_button_keyboard(message_id: int, language: str = "en", is_free: bool = False) -> InlineKeyboardMarkup:
    """Build keyboard with 'Create Voice' button for AI responses
    
    Args:
        message_id: Database message ID to retrieve text for voice generation
        language: Language code for button text
        is_free: If True, shows "Free" text on button (first voice is free)
    """
    # Choose button text based on whether this is a free voice
    button_text_key = "voice.create_button_free" if is_free else "voice.create_button"
    
    # Both buttons in one row
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=get_ui_text(button_text_key, language=language),
                callback_data=f"create_voice:{message_id}"
            ),
            InlineKeyboardButton(
                text=get_ui_text("voice.hide_button", language=language),
                callback_data="hide_voice_buttons"
            )
        ]
    ])


def build_promo_keyboard(miniapp_url: str, language: str = "en") -> InlineKeyboardMarkup:
    """Build keyboard for promotional message (premium / hide)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=get_ui_text("miniapp.premium_button", language=language),
                web_app=WebAppInfo(url=f"{miniapp_url}?page=premium")
            ),
            InlineKeyboardButton(
                text=get_ui_text("system.hide_button", language=language),
                callback_data="hide_promo"
            )
        ]
    ])


def build_blurred_image_keyboard(
    job_id: str,
    miniapp_url: str,
    language: str = "en"
) -> InlineKeyboardMarkup:
    """Build keyboard for blurred image unlock (Open / Premium)
    
    Args:
        job_id: Image job ID for unlock callback
        miniapp_url: Base miniapp URL for premium button
        language: User language code
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=get_ui_text("blurred_image.open_button", language=language),
            callback_data=f"unlock_blurred_image:{job_id}"
        )],
        [InlineKeyboardButton(
            text=get_ui_text("blurred_image.premium_button", language=language),
            web_app=WebAppInfo(url=f"{miniapp_url}?page=premium")
        )]
    ])

