#!/usr/bin/env python3
"""
One-time database seeding script
Run this after deploying to Railway to populate the database
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.settings import load_configs, get_prompts_config
from app.db.base import get_db
from app.db import crud


def seed_database():
    """Seed database with preset personas and initial data"""
    print("🌱 Starting database seeding...")
    
    # Load configs
    load_configs()
    prompts = get_prompts_config()
    personas_config = prompts.get("personas", [])
    
    with get_db() as db:
        # Check if presets already exist
        existing = crud.get_preset_personas(db)
        if existing:
            print(f"✅ {len(existing)} preset personas already in database")
            print("\nExisting personas:")
            for persona in existing:
                print(f"  - {persona.name} ({persona.key})")
            print("\n⚠️  Database already seeded. Skipping...")
            return
        
        # Create preset personas
        print(f"\n📝 Creating {len(personas_config)} preset personas...")
        for persona_data in personas_config:
            persona = crud.create_persona(
                db,
                name=persona_data["name"],
                system_prompt=persona_data["system_prompt"],
                style=persona_data.get("style", {}),
                negatives=persona_data.get("negatives", ""),
                appearance=persona_data.get("appearance", {}),
                key=persona_data["key"],
                is_preset=True
            )
            print(f"  ✓ Created: {persona.name} ({persona.key})")
        
        print(f"\n✅ Successfully seeded {len(personas_config)} preset personas!")
        print("\nPersonas available:")
        for persona_data in personas_config:
            print(f"  - {persona_data['name']} ({persona_data['key']})")


if __name__ == "__main__":
    try:
        seed_database()
        print("\n🎉 Database seeding complete!")
    except Exception as e:
        print(f"\n❌ Error seeding database: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

