#!/usr/bin/env python3
"""
Setup admin overrides for user Railgunchan:
- Set energy to 999999999
- Set custom image_prompt override for Airi (shy_romantic)

Usage:
    python scripts/setup_railgunchan_admin.py
    python scripts/setup_railgunchan_admin.py --dry-run
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.settings import settings
from app.db.models import User

USERNAME = "Railgunchan"
TARGET_ENERGY = 999999999

AIRI_CUSTOM_IMAGE_PROMPT = (
    "(1catgirl), white cat ears (two), loli, very young looking, "
    "one long fluffy white tail, long straight white hair with soft bangs, "
    "green almond-shaped eyes with slit pupils, small feline fang, "
    "petite loli body, narrow shoulders, slim waist, small loli breasts, "
    "small loli round butt, soft smile, gentle gaze"
)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Setup admin overrides for Railgunchan")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without applying")
    args = parser.parse_args()

    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        user = db.query(User).filter(User.username == USERNAME).first()
        if not user:
            print(f"User @{USERNAME} not found in database!")
            sys.exit(1)

        print(f"Found user: @{user.username} (id={user.id})")
        print(f"  Current energy: {user.energy}")
        print(f"  Current settings: {user.settings}")
        print()

        if args.dry_run:
            print("[DRY RUN] Would set:")
            print(f"  energy: {user.energy} -> {TARGET_ENERGY}")
            print(f"  settings.image_prompt_overrides.shy_romantic: <custom Airi prompt>")
            return

        # Set energy
        user.energy = TARGET_ENERGY
        user.max_energy = TARGET_ENERGY

        # Set image prompt override in settings
        if not user.settings or not isinstance(user.settings, dict):
            user.settings = {}
        user.settings["image_prompt_overrides"] = {
            "shy_romantic": AIRI_CUSTOM_IMAGE_PROMPT
        }

        # Mark JSONB as modified
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(user, "settings")

        db.commit()

        print("Applied changes:")
        print(f"  energy: {TARGET_ENERGY}")
        print(f"  max_energy: {TARGET_ENERGY}")
        print(f"  image_prompt_overrides.shy_romantic set")
        print()
        print("Done!")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
