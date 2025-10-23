# UI Text Configuration System

## Overview

All user-facing text strings (buttons, messages, errors, etc.) are now centralized in a configuration file for easy management and potential localization.

## Structure

### Configuration Files

1. **`config/ui_texts.yaml`** - All UI text strings organized by category
2. **`app/settings.py`** - Updated with `get_ui_text()` helper function

### How It Works

**Before (Hardcoded):**
```python
await message.answer("Choose your companion:")
button = InlineKeyboardButton(text="✨ Discover all characters", ...)
```

**After (Configured):**
```python
from app.settings import get_ui_text

await message.answer(get_ui_text("welcome.title"))
button = InlineKeyboardButton(text=get_ui_text("welcome.discover_button"), ...)
```

## Usage Guide

### Basic Usage

```python
from app.settings import get_ui_text

# Simple text retrieval
title = get_ui_text("welcome.title")  # Returns: "Choose your companion:"
error = get_ui_text("errors.persona_not_found")  # Returns: "❌ Persona not found!"
```

### With Variables (String Formatting)

```python
# Text with placeholders
title = get_ui_text("chat_options.title", persona_name="Jane")
# Returns: "💬 You have an existing conversation with Jane"

description = get_ui_text(
    "energy.insufficient_description", 
    required=5, 
    current=2
)
# Returns: "You need 5 energy to send a message, but you only have 2."
```

### In Keyboard Builders

```python
from app.settings import get_ui_text
from aiogram.types import InlineKeyboardButton

button = InlineKeyboardButton(
    text=get_ui_text("welcome.discover_button"),
    callback_data="discover_characters"
)
```

## Configuration Structure

The `config/ui_texts.yaml` file is organized into logical sections:

```yaml
# Welcome & Start Flow
welcome:
  title: "Choose your companion:"
  discover_button: "✨ Discover all characters"
  
# Error Messages
errors:
  persona_not_found: "❌ Persona not found!"
  story_not_found: "❌ Story not found!"
  
# Chat Options
chat_options:
  title: "💬 You have an existing conversation with {persona_name}"
  continue_button: "💬 Continue"
  start_new_button: "🆕 Start New"
```

### Available Categories

- **welcome** - Welcome messages and persona selection
- **story** - Story selection UI
- **chat_options** - Existing chat options (Continue/Start New)
- **hints** - User hints and tips
- **errors** - Error messages
- **energy** - Energy system messages
- **image** - Image generation messages
- **prompts** - Prompt selection UI
- **miniapp** - Mini App integration
- **confirmation** - Yes/No confirmations
- **system** - System/debug messages
- **premium** - Premium/subscription
- **settings** - Settings UI

## Adding New Text Strings

1. **Add to `config/ui_texts.yaml`:**
```yaml
payment:
  success: "✅ Payment successful!"
  failed: "❌ Payment failed: {reason}"
  button: "💳 Buy Premium"
```

2. **Use in code:**
```python
from app.settings import get_ui_text

# Simple text
success_msg = get_ui_text("payment.success")

# With variables
fail_msg = get_ui_text("payment.failed", reason="Insufficient funds")

# In buttons
button = InlineKeyboardButton(
    text=get_ui_text("payment.button"),
    callback_data="buy_premium"
)
```

## Benefits

### 1. **Centralized Management**
- All text in one place
- Easy to find and update
- No hunting through code files

### 2. **Consistency**
- Same text used everywhere
- No duplicate strings
- Easy to maintain brand voice

### 3. **Future Localization**
- Ready for multi-language support
- Simple structure for translation
- Can load different YAML files per language

### 4. **Easy A/B Testing**
- Change text without touching code
- Test different messages
- Quick iterations

### 5. **Non-Technical Editing**
- Marketing can update copy
- No code deployment needed
- YAML is human-readable

## Migration Checklist

To migrate existing hardcoded text:

1. ✅ Identify hardcoded text strings in handlers
2. ✅ Add them to `config/ui_texts.yaml` under appropriate category
3. ✅ Replace hardcoded text with `get_ui_text()` calls
4. ✅ Test the flow to ensure text appears correctly
5. ✅ Remove old hardcoded strings

### Example Migration

**Before:**
```python
@router.callback_query(lambda c: c.data == "buy_premium")
async def buy_premium(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "⭐ Premium Membership\n\n"
        "Unlimited energy, priority support, and more!"
    )
```

**After:**
```python
@router.callback_query(lambda c: c.data == "buy_premium")
async def buy_premium(callback: types.CallbackQuery):
    title = get_ui_text("premium.title")
    benefits = get_ui_text("premium.benefits")
    await callback.message.edit_text(f"{title}\n\n{benefits}")
```

## Future Enhancements

### Multi-Language Support

```python
# Future implementation
def get_ui_text(key_path: str, lang: str = "en", **kwargs) -> str:
    """Get UI text in specified language"""
    # Load from ui_texts_{lang}.yaml
    pass

# Usage
title_en = get_ui_text("welcome.title", lang="en")
title_ru = get_ui_text("welcome.title", lang="ru")
```

### Dynamic Loading

```python
# Reload texts without restart
reload_ui_texts()
```

## Best Practices

1. **Use descriptive keys**: `welcome.title` not `text1`
2. **Group logically**: Related text in same category
3. **Use variables**: `{name}` instead of multiple similar strings
4. **Keep formatting**: Include emojis and formatting in YAML
5. **Document variables**: Comment what variables are needed

## Examples in Production

### Start Handler
```python
# Get persona selection title
welcome_text = get_ui_text("welcome.title") + "\n\n"

# Build persona list with descriptions
for persona in personas:
    welcome_text += f"{persona.emoji} <b>{persona.name}</b> – {persona.description}\n\n"
```

### Chat Options
```python
# Show existing chat options
title = get_ui_text("chat_options.title", persona_name="Jane")
description = get_ui_text("chat_options.description")
await callback.message.edit_text(f"{title}\n\n{description}")
```

### Error Handling
```python
try:
    # ... some operation
except PersonaNotFound:
    error_msg = get_ui_text("errors.persona_not_found")
    await callback.answer(error_msg, show_alert=True)
```

## Loading Configuration

The UI texts are automatically loaded at startup in `app/main.py`:

```python
from app.settings import load_configs

# This loads both app.yaml and ui_texts.yaml
load_configs()
```

No additional configuration needed!

## Troubleshooting

### KeyError: UI text key not found

**Problem:** `KeyError: UI text key not found: welcome.titlexxx`

**Solution:** Check that the key exists in `config/ui_texts.yaml`:
```yaml
welcome:
  title: "Choose your companion:"  # Correct key
```

### Missing Variables

**Problem:** `KeyError: 'persona_name'`

**Solution:** Ensure you pass all required variables:
```python
# Wrong
get_ui_text("chat_options.title")  # Missing persona_name

# Correct
get_ui_text("chat_options.title", persona_name="Jane")
```

### Config Not Loaded

**Problem:** `RuntimeError: UI texts not loaded`

**Solution:** Ensure `load_configs()` is called at startup in `main.py`

