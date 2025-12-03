"""
Upload current prompts to Langfuse Prompt Management.
Run this once to initialize prompts in Langfuse, then manage them in the UI.

Usage:
    python scripts/upload_prompts_to_langfuse.py
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.settings import settings, load_configs


def upload_prompts():
    """Upload all prompts to Langfuse"""
    # Ensure Langfuse is configured
    if not settings.LANGFUSE_SECRET_KEY or not settings.LANGFUSE_PUBLIC_KEY:
        print("❌ Langfuse not configured. Set LANGFUSE_SECRET_KEY and LANGFUSE_PUBLIC_KEY in .env")
        return False
    
    try:
        from langfuse import Langfuse
    except ImportError:
        print("❌ langfuse package not installed. Run: pip install langfuse")
        return False
    
    # Initialize Langfuse
    langfuse = Langfuse(
        secret_key=settings.LANGFUSE_SECRET_KEY,
        public_key=settings.LANGFUSE_PUBLIC_KEY,
        host=settings.LANGFUSE_BASE_URL
    )
    
    # Import local prompts
    from config.prompts import (
        CHAT_GPT,
        IMAGE_TAG_GENERATOR_GPT,
        CONVERSATION_STATE_GPT,
        MEMORY_EXTRACTOR_GPT,
        IMAGE_DECISION_GPT
    )
    
    # Define prompts to upload
    prompts_to_upload = [
        {
            "name": "dialogue-specialist",
            "prompt": CHAT_GPT,
            "config": {
                "brain": "dialogue",
                "model": "thedrummer/cydonia-24b-v4.1",
                "temperature": 0.8,
                "max_tokens": 512,
            },
            "labels": ["production", "dialogue"],
        },
        {
            "name": "state-resolver",
            "prompt": CONVERSATION_STATE_GPT,
            "config": {
                "brain": "state",
                "model": "mistralai/mistral-nemo",
                "temperature": 0.3,
                "max_tokens": 800,
            },
            "labels": ["production", "state"],
        },
        {
            "name": "image-prompt-engineer",
            "prompt": IMAGE_TAG_GENERATOR_GPT,
            "config": {
                "brain": "image-prompt",
                "model": "moonshotai/kimi-k2:nitro",
                "temperature": 0.5,
                "max_tokens": 512,
            },
            "labels": ["production", "image"],
        },
        {
            "name": "image-decision",
            "prompt": IMAGE_DECISION_GPT,
            "config": {
                "brain": "image-decision",
                "model": "mistralai/ministral-3b",
                "temperature": 0.3,
                "max_tokens": 50,
            },
            "labels": ["production", "decision"],
        },
        {
            "name": "memory-extractor",
            "prompt": MEMORY_EXTRACTOR_GPT,
            "config": {
                "brain": "memory",
                "model": "x-ai/grok-4-fast",
                "temperature": 0.5,
                "max_tokens": 800,
            },
            "labels": ["production", "memory"],
        },
    ]
    
    print(f"\n📤 Uploading {len(prompts_to_upload)} prompts to Langfuse...")
    print(f"   Host: {settings.LANGFUSE_BASE_URL}\n")
    
    success_count = 0
    for prompt_config in prompts_to_upload:
        name = prompt_config["name"]
        try:
            # Create/update prompt in Langfuse
            langfuse.create_prompt(
                name=name,
                prompt=prompt_config["prompt"],
                config=prompt_config["config"],
                labels=prompt_config["labels"],
                type="text"  # Simple text prompt
            )
            print(f"   ✅ {name}")
            success_count += 1
        except Exception as e:
            # Check if prompt already exists (common case)
            if "already exists" in str(e).lower() or "409" in str(e):
                print(f"   ⚠️  {name} (already exists - update in Langfuse UI)")
            else:
                print(f"   ❌ {name}: {e}")
    
    print(f"\n✅ Upload complete: {success_count}/{len(prompts_to_upload)} prompts uploaded")
    print(f"\n📋 Next steps:")
    print(f"   1. Go to {settings.LANGFUSE_BASE_URL}")
    print(f"   2. Navigate to 'Prompts' in the sidebar")
    print(f"   3. You can now edit prompts and create new versions")
    print(f"   4. Use labels like 'production' or 'testing' to manage versions")
    
    # Flush to ensure all events are sent
    langfuse.flush()
    
    return success_count == len(prompts_to_upload)


if __name__ == "__main__":
    # Load configs first
    load_configs()
    
    success = upload_prompts()
    sys.exit(0 if success else 1)

