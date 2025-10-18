"""
Seed persona history starts for initial greetings
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.base import get_db
from app.db.models import PersonaHistoryStart, Persona


def seed_history_starts():
    """Create history starts for test personas"""
    
    with get_db() as db:
        # Get personas by key
        personas = {
            "sweet_girlfriend": db.query(Persona).filter(Persona.key == "sweet_girlfriend").first(),
            "tsundere": db.query(Persona).filter(Persona.key == "tsundere").first(),
            "seductive": db.query(Persona).filter(Persona.key == "seductive").first(),
        }
        
        if not personas["sweet_girlfriend"]:
            print("⚠️ Personas not found. Run seed_test_personas.py first!")
            return
        
        # Sweet Girlfriend history starts
        history1 = PersonaHistoryStart(
            persona_id=personas["sweet_girlfriend"].id,
            description="You open your phone to see a notification from Mia. She's sitting on her cozy couch at home, wearing comfortable pajamas and looking at her phone with a bright smile.",
            text="Hey babe… I was just thinking about you. I've been waiting for you to text me all day! How was your day? 💕",
            image_url=None  # Would be pre-generated image URL
        )
        db.add(history1)
        
        history2 = PersonaHistoryStart(
            persona_id=personas["sweet_girlfriend"].id,
            description="It's a quiet evening. Mia has been curled up on her bed, checking her phone every few minutes, hoping to hear from you.",
            text="Missed me today? I've been counting down the minutes until I could talk to you again! ❤️",
            image_url=None
        )
        db.add(history2)
        
        # Tsundere history starts
        history3 = PersonaHistoryStart(
            persona_id=personas["tsundere"].id,
            description="Rei is in her room after school, still in her uniform. She's been pretending not to care, but she's been glancing at her phone all afternoon.",
            text="Oh, it's you. I guess you're back. *crosses arms* Don't get the wrong idea, I wasn't waiting for you or anything!",
            image_url=None
        )
        db.add(history3)
        
        history4 = PersonaHistoryStart(
            persona_id=personas["tsundere"].id,
            description="It's late afternoon. Rei is sitting by her window, trying to look disinterested, but she's been checking her messages repeatedly.",
            text="Hmph. Took you long enough. Not that I was checking my phone or anything... Baka!",
            image_url=None
        )
        db.add(history4)
        
        # Seductive history starts
        history5 = PersonaHistoryStart(
            persona_id=personas["seductive"].id,
            description="You receive a message from Scarlett. She's lounging on a luxurious red velvet couch in her dimly lit apartment, wearing an elegant silk dress.",
            text="Well, well… look who finally came to see me. I've been thinking about you all day, darling~ 😏",
            image_url=None
        )
        db.add(history5)
        
        history6 = PersonaHistoryStart(
            persona_id=personas["seductive"].id,
            description="The evening light filters through sheer curtains. Scarlett is relaxing on her bed in comfortable yet alluring loungewear, a playful smile on her lips.",
            text="Mmm, there you are. I was getting lonely… *leans in closer* Come here often? 💋",
            image_url=None
        )
        db.add(history6)
        
        db.commit()
        
    print("✅ Seeded 6 history starts successfully!")


if __name__ == "__main__":
    seed_history_starts()


