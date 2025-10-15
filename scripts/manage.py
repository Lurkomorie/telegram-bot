#!/usr/bin/env python3
"""
Management script for local development and testing
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def set_webhook(public_url: str = None):
    """Set Telegram webhook"""
    from app.settings import settings
    import httpx
    
    # Use provided URL or auto-detect from Railway
    if not public_url:
        public_url = settings.public_url
    
    webhook_url = f"{public_url}/webhook/{settings.WEBHOOK_SECRET}"
    api_url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/setWebhook"
    
    async with httpx.AsyncClient() as client:
        response = await client.post(api_url, json={"url": webhook_url})
        print(response.json())


async def delete_webhook():
    """Delete Telegram webhook"""
    from app.settings import settings
    import httpx
    
    api_url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/deleteWebhook"
    
    async with httpx.AsyncClient() as client:
        response = await client.post(api_url)
        print(response.json())


async def get_webhook_info():
    """Get current webhook info"""
    from app.settings import settings
    import httpx
    
    api_url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/getWebhookInfo"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(api_url)
        import json
        print(json.dumps(response.json(), indent=2))


def seed_personas():
    """Seed preset personas from config to database"""
    from app.settings import load_configs, get_prompts_config
    from app.db.base import get_db
    from app.db import crud
    
    load_configs()
    prompts = get_prompts_config()
    
    with get_db() as db:
        existing = crud.get_preset_personas(db)
        if existing:
            print(f"✅ {len(existing)} preset personas already exist")
            return
        
        for persona_data in prompts["personas"]:
            crud.create_persona(
                db,
                name=persona_data["name"],
                system_prompt=persona_data["system_prompt"],
                style=persona_data.get("style", {}),
                negatives=persona_data.get("negatives", ""),
                appearance=persona_data.get("appearance", {}),
                key=persona_data["key"],
                is_preset=True
            )
        
        print(f"✅ Seeded {len(prompts['personas'])} preset personas")


def list_personas():
    """List all personas in database"""
    from app.db.base import get_db
    from app.db import crud
    
    with get_db() as db:
        presets = crud.get_preset_personas(db)
        
        print("\n📚 Preset Personas:")
        for p in presets:
            print(f"  - {p.name} ({p.key})")
        
        print(f"\nTotal: {len(presets)}")


def test_openrouter():
    """Test OpenRouter API connection"""
    import asyncio
    from app.core.llm_openrouter import generate_text
    from app.settings import load_configs
    
    load_configs()
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say hello in one short sentence."}
    ]
    
    async def test():
        try:
            result = await generate_text(messages)
            print(f"✅ OpenRouter API working!")
            print(f"Response: {result}")
        except Exception as e:
            print(f"❌ OpenRouter API failed: {e}")
    
    asyncio.run(test())


def test_runpod():
    """Test Runpod API connection"""
    import asyncio
    from uuid import uuid4
    from app.core.img_runpod import submit_image_job
    from app.settings import load_configs
    
    load_configs()
    
    async def test():
        try:
            job_id = uuid4()
            result = await submit_image_job(
                job_id=job_id,
                prompt="test portrait, 1girl, smiling",
                negative_prompt="low quality",
                seed=12345
            )
            print(f"✅ Runpod API working!")
            print(f"Response: {result}")
        except Exception as e:
            print(f"❌ Runpod API failed: {e}")
    
    asyncio.run(test())


def main():
    """Main CLI entry point"""
    if len(sys.argv) < 2:
        print("""
🤖 Bot Management CLI

Usage: python scripts/manage.py <command> [args]

Commands:
  set-webhook <public_url>   - Set Telegram webhook
  delete-webhook             - Delete Telegram webhook
  webhook-info               - Get current webhook info
  seed-personas              - Seed preset personas to DB
  list-personas              - List all personas in DB
  test-openrouter            - Test OpenRouter API
  test-runpod                - Test Runpod API

Examples:
  python scripts/manage.py set-webhook https://my-app.railway.app
  python scripts/manage.py seed-personas
  python scripts/manage.py test-openrouter
""")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "set-webhook":
        # Public URL is optional, will use Railway domain if not provided
        public_url = sys.argv[2] if len(sys.argv) >= 3 else None
        asyncio.run(set_webhook(public_url))
    
    elif command == "delete-webhook":
        asyncio.run(delete_webhook())
    
    elif command == "webhook-info":
        asyncio.run(get_webhook_info())
    
    elif command == "seed-personas":
        seed_personas()
    
    elif command == "list-personas":
        list_personas()
    
    elif command == "test-openrouter":
        test_openrouter()
    
    elif command == "test-runpod":
        test_runpod()
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()


