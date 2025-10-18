"""
Seed test personas for development and testing
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.base import get_db
from app.db import crud


def seed_test_personas():
    """Create test personas with different configurations"""
    
    with get_db() as db:
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
        print(f"✅ Created persona: {persona1.name} ({persona1.id})")
        
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
        print(f"✅ Created persona: {persona2.name} ({persona2.id})")
        
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
        print(f"✅ Created persona: {persona3.name} ({persona3.id})")
        
    print(f"\n✅ Seeded 3 test personas successfully!")


if __name__ == "__main__":
    seed_test_personas()


