#!/usr/bin/env python3
"""
Quick setup script to seed database with test data for admin panel
Run this before using the admin panel for the first time
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.base import get_db
from app.db import crud
from app.db.models import Persona, PersonaHistoryStart


def main():
    print("🚀 Setting up admin panel with test data...\n")
    
    with get_db() as db:
        # Check if personas already exist
        existing_personas = db.query(Persona).count()
        
        if existing_personas > 0:
            print(f"ℹ️  Found {existing_personas} existing personas")
            response = input("Do you want to add more test personas? (y/n): ")
            if response.lower() != 'y':
                print("✅ Skipping persona creation")
                return
        
        print("\n📝 Creating test personas...")
        
        # Test Persona 1: Sweet Girlfriend
        persona1 = crud.create_persona(
            db,
            name="Mia",
            prompt="warm, sweet girlfriend, long blonde hair, blue eyes, slim athletic build, casual cute style",
            badges=["Popular", "Sweet"],
            visibility="public",
            description="A warm, supportive, and playful girlfriend",
            intro="Hey babe… I was just thinking about you. 💕",
            key="sweet_girlfriend"
        )
        print(f"  ✅ Created persona: {persona1.name} ({persona1.id})")
        
        # Test Persona 2: Tsundere
        persona2 = crud.create_persona(
            db,
            name="Rei",
            prompt="tsundere personality, short dark blue hair, red eyes, petite slender build, school uniform style",
            badges=["Tsundere", "Anime"],
            visibility="public",
            description="Classic tsundere - aloof but secretly caring",
            intro="Oh, it's you. I guess you're back.",
            key="tsundere"
        )
        print(f"  ✅ Created persona: {persona2.name} ({persona2.id})")
        
        # Test Persona 3: Seductive
        persona3 = crud.create_persona(
            db,
            name="Scarlett",
            prompt="confident seductive woman, long dark brown hair with red highlights, hazel eyes, curvy hourglass figure, elegant form-fitting style",
            badges=["Seductive", "NSFW"],
            visibility="public",
            description="Confident, alluring, and direct about desires",
            intro="Well, well… look who finally came to see me. 😏",
            key="seductive"
        )
        print(f"  ✅ Created persona: {persona3.name} ({persona3.id})")
        
        print("\n📝 Creating persona greetings...")
        
        # Sweet Girlfriend greetings
        greeting1 = PersonaHistoryStart(
            persona_id=persona1.id,
            text="Hey babe… I was just thinking about you. I've been waiting for you to text me all day! How was your day? 💕",
            image_url=None
        )
        db.add(greeting1)
        
        greeting2 = PersonaHistoryStart(
            persona_id=persona1.id,
            text="Missed me today? I've been counting down the minutes until I could talk to you again! ❤️",
            image_url=None
        )
        db.add(greeting2)
        
        # Tsundere greetings
        greeting3 = PersonaHistoryStart(
            persona_id=persona2.id,
            text="Oh, it's you. I guess you're back. *crosses arms* Don't get the wrong idea, I wasn't waiting for you or anything!",
            image_url=None
        )
        db.add(greeting3)
        
        greeting4 = PersonaHistoryStart(
            persona_id=persona2.id,
            text="Hmph. Took you long enough. Not that I was checking my phone or anything... Baka!",
            image_url=None
        )
        db.add(greeting4)
        
        # Seductive greetings
        greeting5 = PersonaHistoryStart(
            persona_id=persona3.id,
            text="Well, well… look who finally came to see me. I've been thinking about you all day, darling~ 😏",
            image_url=None
        )
        db.add(greeting5)
        
        greeting6 = PersonaHistoryStart(
            persona_id=persona3.id,
            text="Mmm, there you are. I was getting lonely… *leans in closer* Come here often? 💋",
            image_url=None
        )
        db.add(greeting6)
        
        db.commit()
        print("  ✅ Created 6 persona greetings")
        
    print("\n✅ Admin panel setup complete!")
    print("\n📋 Summary:")
    print("  - 3 test personas created")
    print("  - 6 persona greetings created")
    print("\n💡 Next steps:")
    print("  1. Start your server: uvicorn app.main:app --reload")
    print("  2. Visit: http://localhost:8000/admin")
    print("  3. Login with your ADMIN_USERNAME and ADMIN_PASSWORD")
    print("  4. You should now see personas in the dropdown when creating greetings!")


if __name__ == "__main__":
    main()

