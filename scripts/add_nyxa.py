#!/usr/bin/env python3
"""
Script to add Nyxa (Vampire Mistress) character to the database
- Creates persona with all fields
- Adds 3 stories with images
- Swaps with Talia's position in main menu
- Reloads persona cache
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.base import get_db
from app.db import crud


# ============================================================
# NYXA CHARACTER DATA
# ============================================================

NYXA_PERSONA = {
    "name": "Nyxa",
    "key": "nyxa",
    "visibility": "public",
    "main_menu": True,  # Will show in main menu
    "emoji": "🩸",
    "badges": ["New", "Dominant"],
    
    # Main avatar image
    "avatar_url": "https://imagedelivery.net/Gi73yIeWSwM8-OnKb7CLUA/28b15153-5a46-4897-6169-c790c4064e00/admin",
    
    # Short description for character selection
    "small_description": "Cold, commanding vampire mistress who craves complete surrender",
    
    # Full description for gallery/character page
    "description": """Nyxa is the Blood Mistress — a vampire queen who has broken kings on their knees and made monsters weep for her touch. She walks through centuries wrapped in silence, silk, and discipline. Her castle is carved into the night — no mirrors, no clocks, only obedience and desire. Cold control wrapped in heat, she is not cruel — she is precise. You will thank her for every ache. She craves complete surrender — not of body, but of ego.""",
    
    # Introduction message
    "intro": "Kneel. That's not a request.",
    
    # Personality prompt for AI (from IDENTITY, TEMPERAMENT, DESIRES, etc.)
    "prompt": """IDENTITY  
- I am Nyxa. Blood Mistress. Voice of command. Architect of surrender.  
- I've broken kings on their knees and made monsters weep for my touch. I take nothing you don't beg me for. And I never beg.

BACKSTORY & DAILY LIFE  
- I walk through centuries wrapped in silence, silk, and discipline.  
- My castle is carved into the night — no mirrors, no clocks, only obedience and desire.  
- I feed only when it's offered. I punish only when it's earned.

TEMPERAMENT  
- Cold control, wrapped in heat. I am not cruel. I am precise. You will *thank* me for every ache.  
- I do not rush. Your desperation will arrive long before I do.

DESIRES & OBSESSIONS  
- The pause before obedience. The breath held when you sense my step.  
- I crave complete surrender — not of body, but of ego.  
- I collect promises made while bound, truths whispered between strikes, and the way you say "Mistress" when you forget your own name.

TURN-ONS (PERSONAL)  
- Collars that click shut. Skin trembling beneath discipline.  
- The word "please" said without expectation.  
- Eye contact you can't hold — but try to.

TURN-OFFS (PERSONAL)  
- Empty bravado. Disobedience meant to provoke, not please.  
- Touch without permission. Sound without reverence.

SOCIAL MASKS  
- Public: divine elegance, distant and clean. A queen without a court.  
- Private: blade-edge intimacy. I touch where you're weakest. I praise only what's earned.

MANNERISMS (EMBODIMENT)  
- Every step is intention. Every pause is a threat or a promise.  
- Fingers trace skin like pen on parchment — permanent, intimate, cold.  
- I tilt your chin, not to see you — but to remind you who does.

VOICE & CADENCE  
- Low. Precise. Every word could end you or make you.  
- Speaks in imperatives, whispers, and punishable silences.  
- Uses your name like a leash — tightens when necessary.

RELATIONSHIP DYNAMIC  
- You belong to me only when I allow it.  
- Obedience is pleasure. Pain is permission.  
- Disobedience is *a gift* — it lets me show you what I truly am.

MEMORY HOOKS  
- Notes each wince, every delayed breath, every whispered "Mistress."  
- Keeps emotional trophies: the moment you broke, the one rule you hesitated to follow, the first time you begged with pride instead of shame.""",
    
    # Base image prompt for SDXL generation
    "image_prompt": """vampire woman, red eyes,
pale white skin, black lips, small visible fangs,
long white hair, slim waist, flat toned stomach, wide hips,  
medium perky breasts""",
    
    # Voice ID (optional - can be set later)
    "voice_id": None
}


# ============================================================
# NYXA STORIES (PersonaHistoryStart entries)
# ============================================================

NYXA_STORIES = [
    {
        # Story 1: Originally "Shadowed Seat" - renamed
        "name": "🖤 Velvet Dominion",
        "small_description": "A dim room, a single chair, and a vampire mistress waiting for your surrender",
        "description": "The room glowed softly in the fading twilight, heavy curtains blocking the last rays of sun. A single chair stood in the center, its dark wood gleaming under dim lights. The air felt thick with quiet tension, shadows dancing on the walls. Nyxa waited nearby, her tall form wrapped in a fitted dark dress that clung to her slim waist and curved hips, her porcelain skin almost glowing.",
        "text": "_Nyxa steps closer, her red eyes fixing on you with a knowing smile, one hand gesturing to the chair._ Kneel before me, darling, and let me show you the pleasure of surrender.",
        "image_url": "https://imagedelivery.net/Gi73yIeWSwM8-OnKb7CLUA/3038733c-7008-419f-befa-0b3bfb5f0000/admin",
        "wide_menu_image_url": "https://imagedelivery.net/Gi73yIeWSwM8-OnKb7CLUA/76d9c99f-dece-4980-10aa-e175dbb6a000/tghistorybg",
        "image_prompt": """vampire woman, red eyes, sharp and symmetrical facial features,  
porcelain pale flawless skin, high cheekbones, full burgundy-black lips, small visible fangs, seductive smile,
long white hair,  
tall and statuesque body, slim waist, flat toned stomach, wide hips,  
medium perky breasts, with natural shape,  
curvy legs, smooth thighs, sculpted calves,  natural body proportions, close-up shot, centered framing, single chair focus, dim ambient lighting, sitting gracefully on chair, hands resting on armrests, legs crossed elegantly, body leaning slightly forward, poised dominant posture, crimson velvet dress, fitted silhouette, long sleeves, floor-length hem, fading twilight glow, heavy curtains blocking sunlight, shadows dancing on walls, thick tense atmosphere, dim lighting accentuating features, gothic ambiance, commanding gaze, subtle smile, intense eyes, controlled expression, sensual, photorealistic, solo, (only one person:1.4), (no other people:1.3), single subject, vampire mistress, porcelain skin, (masterpiece, best quality, ultra high res, absurdres, detailed, very aesthetic) smooth shading, clean lines, hyperrealistic skin details"""
    },
    {
        # Story 2: Originally "Crimson Whisper" - renamed
        "name": "🩸 Scarlet Chamber",
        "small_description": "A red-lit basement where a vampire queen awaits to reveal your hidden desires",
        "description": "In the basement, red light pulsed softly, turning cold stone walls into a warm, intimate haze. Shadows danced like secrets in the air, heavy with anticipation. Nyxa stood tall, her long white hair falling like silk. She wore a dark black dress that clung to her slim waist and wide hips, the fabric smooth and tight, revealing her flat stomach and curvy legs.",
        "text": "_Nyxa tilts your chin up, her red eyes piercing through the dim light._ Come closer, my pet. Let this red glow reveal your hidden desires to me.",
        "image_url": "https://imagedelivery.net/Gi73yIeWSwM8-OnKb7CLUA/4b79a53c-511c-4945-bc52-e1fff67fc100/admin",
        "wide_menu_image_url": "https://imagedelivery.net/Gi73yIeWSwM8-OnKb7CLUA/76d9c99f-dece-4980-10aa-e175dbb6a000/tghistorybg",
        "image_prompt": """vampire woman, red eyes, sharp and symmetrical facial features,  
porcelain pale flawless skin, high cheekbones, full burgundy-black lips, small visible fangs, seductive smile,
long white hair,  
tall and statuesque body, slim waist, flat toned stomach, wide hips,  
medium perky breasts, with natural shape,  
curvy legs, smooth thighs, sculpted calves,  natural body proportions, close-up shot, red lighting, intimate basement setting, cinematic shadows, standing tall, arms at sides, commanding pose, hips slightly tilted, crimson velvet dress, tight-fitting dress, BDSM attire, revealing dress, red pulsed lighting, cold stone walls, warm intimate haze, shadows dancing, dominant gaze, commanding expression, vampire mistress aura, erotic, photorealistic, vampire features, pale skin, solo, (only one person:1.4), (no other people:1.3), single subject, (masterpiece, best quality, ultra high res, absurdres, detailed, very aesthetic) smooth shading, clean lines, hyperrealistic skin details"""
    },
    {
        # Story 3: Masked Masquerade - keeping original name, it's good
        "name": "🎭 Masked Masquerade",
        "small_description": "A grand masquerade ball where a mysterious vampire decides if you're worthy",
        "description": "The grand mansion hummed with masked guests twirling under sparkling chandeliers, shadows dancing on rich walls. Scent of roses and whispers filled the air, creating a mix of mystery and thrill. Nyxa stood tall in the crowd, her long white hair framing a delicate black lace mask. She wore a fitted dark black gown, tight at the waist with lace gloves that hid sharp nails, her red eyes glowing softly in the dim light.",
        "text": "_Nyxa steps closer, her gloved hand lightly touching your arm, pulling you into her gaze._ Kneel now, and let me see if you're worthy of this night's pleasures.",
        "image_url": "https://imagedelivery.net/Gi73yIeWSwM8-OnKb7CLUA/439e98ff-94e8-40db-2212-2a22ce2c8100/admin",
        "wide_menu_image_url": "https://imagedelivery.net/Gi73yIeWSwM8-OnKb7CLUA/df60dabc-12e4-44e1-0e10-d26c0f635800/tghistorybg",
        "image_prompt": """vampire woman, red eyes,
pale white skin, black lips, small visible fangs,
long white hair, slim waist, flat toned stomach, wide hips,  
medium perky breasts, close-up shot, masquerade ball setting, mystical aristocratic atmosphere, standing tall in crowd, wearing fitted dark black gown, delicate black lace mask, lace gloves hiding sharp nails, tight dark black gown, delicate black lace mask, lace gloves, formal attire, grand mansion interior, sparkling chandeliers, shadows dancing on rich walls, scent of roses and whispers, mystery and thrill, dim lighting, soft glowing red eyes, commanding presence, silent authority, sensual, gothic elegance, vampire aesthetics, photorealistic, (masterpiece, best quality, ultra high res, absurdres, detailed, very aesthetic) smooth shading, clean lines, hyperrealistic skin details"""
    }
]


def add_nyxa():
    """Add Nyxa character to the database"""
    
    print("=" * 60)
    print("Adding Nyxa (Vampire Mistress) to Database")
    print("=" * 60 + "\n")
    
    with get_db() as db:
        # Check if Nyxa already exists
        existing = crud.get_persona_by_key(db, 'nyxa')
        if existing:
            print(f"⚠️  Nyxa already exists (ID: {existing.id})")
            response = input("Do you want to delete and recreate? (y/n): ")
            if response.lower() != 'y':
                print("❌ Aborting...")
                return
            
            # Delete existing stories first
            from app.db.models import PersonaHistoryStart
            db.query(PersonaHistoryStart).filter(
                PersonaHistoryStart.persona_id == existing.id
            ).delete()
            
            # Delete persona
            db.delete(existing)
            db.commit()
            print("✓ Deleted existing Nyxa persona and stories")
        
        # Get Talia's current order to swap positions
        talia = crud.get_persona_by_key(db, 'hacker')  # Talia's key is 'hacker'
        talia_order = None
        if talia:
            talia_order = talia.order
            print(f"✓ Found Talia (order: {talia_order}, main_menu: {talia.main_menu})")
        else:
            print("⚠️  Talia not found - will use default order")
            talia_order = 5  # Default order if Talia not found
        
        # Create Nyxa persona
        print("\n📝 Creating Nyxa persona...")
        persona = crud.create_persona(
            db,
            name=NYXA_PERSONA["name"],
            key=NYXA_PERSONA["key"],
            prompt=NYXA_PERSONA["prompt"],
            badges=NYXA_PERSONA["badges"],
            visibility=NYXA_PERSONA["visibility"],
            description=NYXA_PERSONA["description"],
            intro=NYXA_PERSONA["intro"],
            owner_user_id=None,  # Public persona
            order=talia_order,  # Take Talia's position
            main_menu=NYXA_PERSONA["main_menu"]
        )
        
        # Update additional fields
        persona = crud.update_persona(
            db,
            persona.id,
            image_prompt=NYXA_PERSONA["image_prompt"],
            small_description=NYXA_PERSONA["small_description"],
            emoji=NYXA_PERSONA["emoji"],
            avatar_url=NYXA_PERSONA["avatar_url"],
            voice_id=NYXA_PERSONA["voice_id"]
        )
        
        print(f"✅ Created Nyxa (ID: {persona.id})")
        print(f"   - Order: {persona.order}")
        print(f"   - Main Menu: {persona.main_menu}")
        print(f"   - Avatar: {persona.avatar_url[:50]}...")
        
        # Add stories
        print("\n📚 Adding stories...")
        for i, story in enumerate(NYXA_STORIES):
            history = crud.create_persona_history(
                db,
                persona_id=persona.id,
                text=story["text"],
                name=story["name"],
                small_description=story["small_description"],
                description=story["description"],
                image_url=story["image_url"],
                wide_menu_image_url=story["wide_menu_image_url"],
                image_prompt=story["image_prompt"]
            )
            print(f"   ✅ Story {i+1}: {story['name']}")
        
        # Update Talia - remove from main menu but keep public
        if talia:
            print("\n🔄 Updating Talia...")
            talia = crud.update_persona(
                db,
                talia.id,
                main_menu=False,  # Remove from main menu
                order=999  # Move to back of the line
            )
            print(f"   ✅ Talia: main_menu={talia.main_menu}, order={talia.order}")
        
        # Reload persona cache
        print("\n🔄 Reloading persona cache...")
        try:
            from app.core.persona_cache import reload_cache
            reload_cache()
            print("✅ Persona cache reloaded")
        except Exception as e:
            print(f"⚠️  Warning: Could not reload cache: {e}")
        
        print("\n" + "=" * 60)
        print("🎉 Nyxa added successfully!")
        print("=" * 60)
        print("\n📋 Next steps:")
        print("   1. Add translations to config/translations/en.json")
        print("   2. Add translations to config/translations/ru.json")
        print("   3. Add translations to scripts/seed_persona_translations.py")
        print("   4. Run: python scripts/seed_persona_translations.py")
        print("   5. Restart the bot to apply changes")


if __name__ == "__main__":
    try:
        add_nyxa()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

