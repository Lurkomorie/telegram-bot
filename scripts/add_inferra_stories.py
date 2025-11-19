"""
Script to add Inferra stories from test.txt to the database
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.base import get_db
from app.db import crud


def parse_stories(file_path):
    """Parse stories from the text file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = [line.rstrip('\n') for line in f.readlines()]
    
    stories = []
    i = 66  # Starting line (0-indexed, so line 67 in the file)
    
    while i < len(lines) and i <= 109:  # Up to line 110
        # Skip empty lines
        while i < len(lines) and not lines[i].strip():
            i += 1
        
        if i >= len(lines) or i > 109:
            break
        
        # Check if this is a story number
        if not lines[i].strip().isdigit():
            i += 1
            continue
        
        story_num = lines[i].strip()
        i += 1
        
        # Get name
        name = lines[i].strip() if i < len(lines) else ""
        i += 1
        
        # Skip empty line
        while i < len(lines) and not lines[i].strip():
            i += 1
        
        # Get description (multi-line until empty line)
        description = lines[i].strip() if i < len(lines) else ""
        i += 1
        
        # Skip empty line
        while i < len(lines) and not lines[i].strip():
            i += 1
        
        # Get text (greeting message)
        text = lines[i].strip() if i < len(lines) else ""
        # Replace \n with actual newline
        text = text.replace('\\n', '\n')
        i += 1
        
        # Skip empty line
        while i < len(lines) and not lines[i].strip():
            i += 1
        
        # Get image_url
        image_url = lines[i].strip() if i < len(lines) else ""
        i += 1
        
        # Get image_prompt (long line)
        image_prompt = lines[i].strip() if i < len(lines) else ""
        i += 1
        
        # Skip empty line
        while i < len(lines) and not lines[i].strip():
            i += 1
        
        # Get scene description
        scene_description = lines[i].strip() if i < len(lines) else ""
        i += 1
        
        # Skip empty line
        while i < len(lines) and not lines[i].strip():
            i += 1
        
        # Get wide_menu_image_url
        wide_menu_image_url = lines[i].strip() if i < len(lines) else ""
        i += 1
        
        # Get small_description
        small_description = lines[i].strip() if i < len(lines) else ""
        i += 1
        
        story = {
            'name': name,
            'text': text,
            'description': description,
            'small_description': small_description,
            'image_url': image_url,
            'wide_menu_image_url': wide_menu_image_url,
            'image_prompt': image_prompt
        }
        
        stories.append(story)
        print(f"✓ Parsed story {story_num}: {name}")
    
    return stories


def add_stories_to_inferra():
    """Add the parsed stories to Inferra persona"""
    # Parse stories from file
    file_path = os.path.join(os.path.dirname(__file__), '..', 'test.txt')
    stories = parse_stories(file_path)
    
    if not stories:
        print("❌ No stories found in file")
        return
    
    print(f"\n📚 Found {len(stories)} stories to add\n")
    
    # Get Inferra persona
    with get_db() as db:
        inferra = crud.get_persona_by_key(db, 'inferra')
        
        if not inferra:
            print("❌ Inferra persona not found in database")
            return
        
        print(f"✓ Found Inferra persona (ID: {inferra.id})\n")
        
        # Add each story
        added_count = 0
        for story in stories:
            try:
                history = crud.create_persona_history(
                    db,
                    persona_id=inferra.id,
                    text=story['text'],
                    name=story['name'],
                    small_description=story['small_description'],
                    description=story['description'],
                    image_url=story['image_url'],
                    wide_menu_image_url=story['wide_menu_image_url'],
                    image_prompt=story['image_prompt']
                )
                print(f"✅ Added: {story['name']}")
                added_count += 1
            except Exception as e:
                print(f"❌ Failed to add {story['name']}: {e}")
        
        print(f"\n🎉 Successfully added {added_count}/{len(stories)} stories to Inferra")
        
        # Reload persona cache
        try:
            from app.core.persona_cache import reload_cache
            reload_cache()
            print("✓ Persona cache reloaded")
        except Exception as e:
            print(f"⚠️ Warning: Could not reload cache: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("Adding Inferra Stories to Database")
    print("=" * 60 + "\n")
    
    try:
        add_stories_to_inferra()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)

