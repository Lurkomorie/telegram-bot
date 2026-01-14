"""
Script to update persona images, emojis, and menu settings

This script:
1. Uploads new images from local folder to Cloudflare
2. Updates persona avatar_url in database
3. Updates persona emojis for buttons
4. Stores menu image URL in app config

Usage:
    python scripts/update_personas_and_menu.py
"""
import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.base import get_db
from app.db.models import Persona
from app.core.cloudflare_upload import upload_to_cloudflare_tg


# Mapping of image filenames to persona keys
PERSONA_IMAGE_MAPPING = {
    "airi.jpg": "shy_romantic",      # Airi
    "ekaterina.jpg": "ekaterina",     # Ekaterina
    "emilia.jpg": "emilia",           # Emilia (not in main menu)
    "eva.jpg": "eva",                 # Eva
    "inferra.png": "inferra",         # Inferra
    "isabella.png": "isabella",       # Isabella (not in main menu)
    "lumi.jpg": "sweet_girlfriend",   # Lumi
    "nixa.jpg": "nyxa",               # Nyxa
    "sparkle.jpg": "sparkle",         # Sparkle (not in main menu)
    "talia.png": "hacker",            # Talia
    "zenara.png": "amazon",           # Zenara
}

# New emojis for personas (for buttons in main menu)
PERSONA_EMOJIS = {
    "shy_romantic": "🐱🌸",   # Airi - catgirl with blossom
    "eva": "🦊🌈",            # Eva - fox with rainbow  
    "ekaterina": "👩‍🏫",         # Ekaterina - teacher
    "inferra": "🔥",           # Inferra - fire (succubus)
    # Other personas keep their existing emojis
}

# Path to images folder
IMAGES_FOLDER = Path("/Users/artemtrifanuk/Downloads/Telegram Desktop/new images")


async def upload_image(filepath: Path) -> str | None:
    """Upload an image to Cloudflare and return the URL"""
    if not filepath.exists():
        print(f"  ❌ File not found: {filepath}")
        return None
    
    # Read the image bytes
    with open(filepath, "rb") as f:
        image_bytes = f.read()
    
    # Upload to Cloudflare
    result = await upload_to_cloudflare_tg(
        image_bytes,
        filename=filepath.name
    )
    
    if result.success:
        print(f"  ✅ Uploaded {filepath.name} -> {result.image_url}")
        return result.image_url
    else:
        print(f"  ❌ Failed to upload {filepath.name}: {result.error}")
        return None


async def main():
    print("=" * 60)
    print("🚀 Updating persona images and emojis")
    print("=" * 60)
    
    # Step 1: Upload menu image
    print("\n📸 Step 1: Uploading menu image...")
    menu_image_path = IMAGES_FOLDER / "menu.jpg"
    menu_image_url = await upload_image(menu_image_path)
    
    if menu_image_url:
        print(f"\n✅ Menu image URL: {menu_image_url}")
        print("   Add this to your app config or code!")
    
    # Step 2: Upload persona images and update database
    print("\n📸 Step 2: Uploading persona images...")
    uploaded_images = {}
    
    for filename, persona_key in PERSONA_IMAGE_MAPPING.items():
        image_path = IMAGES_FOLDER / filename
        print(f"\n  Processing {filename} -> {persona_key}...")
        
        url = await upload_image(image_path)
        if url:
            uploaded_images[persona_key] = url
    
    # Step 3: Update database
    print("\n💾 Step 3: Updating database...")
    
    with get_db() as db:
        for persona_key, avatar_url in uploaded_images.items():
            persona = db.query(Persona).filter(Persona.key == persona_key).first()
            if persona:
                persona.avatar_url = avatar_url
                print(f"  ✅ Updated {persona_key} avatar_url")
            else:
                print(f"  ⚠️  Persona with key '{persona_key}' not found")
        
        # Step 4: Update emojis
        print("\n🎨 Step 4: Updating emojis...")
        for persona_key, new_emoji in PERSONA_EMOJIS.items():
            persona = db.query(Persona).filter(Persona.key == persona_key).first()
            if persona:
                old_emoji = persona.emoji
                persona.emoji = new_emoji
                print(f"  ✅ Updated {persona_key} emoji: {old_emoji} -> {new_emoji}")
            else:
                print(f"  ⚠️  Persona with key '{persona_key}' not found")
        
        db.commit()
        print("\n✅ Database changes committed!")
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 SUMMARY")
    print("=" * 60)
    print(f"\n📷 Menu image URL:")
    print(f"   {menu_image_url}")
    print(f"\n📷 Uploaded {len(uploaded_images)} persona images")
    print(f"\n🎨 Updated {len(PERSONA_EMOJIS)} persona emojis")
    
    print("\n⚠️  NEXT STEPS:")
    print("   1. Add menu image URL to your code")
    print("   2. Update translations in config/translations/ru.json")
    print("   3. Restart the bot to apply changes")
    print("   4. Clear persona cache if needed")


if __name__ == "__main__":
    asyncio.run(main())
