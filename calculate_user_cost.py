#!/usr/bin/env python3
"""
Calculate the cost of a free user spending all 100 energy
Based on actual OpenRouter pricing and system configuration
"""
import os
from datetime import datetime, timedelta
from sqlalchemy import create_engine, func, text
from sqlalchemy.orm import sessionmaker
from app.db.models import Message, User, TgAnalyticsEvent

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:XGlKgqmSQtgFMVsVkGtFjAzYZlAULdwo@trolley.proxy.rlwy.net:18646/railway")

try:
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    db_connected = True
except Exception as e:
    print(f"⚠️  Database co
    nnection failed: {e}")
    print("📊 Continuing with pricing calculations only...\n")
    db_connected = False
    session = None

print("=" * 80)
print("FREE USER COST ANALYSIS")
print("=" * 80)

# OpenRouter Pricing (per 1M tokens) - Based on actual pricing research
# Source: OpenRouter API pricing as of Jan 2026
MODEL_PRICING = {
    "deepseek/deepseek-v3.2": {
        "input": 0.28,   # $0.28 per 1M input tokens
        "output": 1.10,  # $1.10 per 1M output tokens
        "name": "DeepSeek V3.2 (Main Chat)"
    },
    "mistralai/mistral-nemo": {
        "input": 0.10,   # $0.10 per 1M input tokens
        "output": 0.10,  # $0.10 per 1M output tokens
        "name": "Mistral Nemo (State Resolution)"
    },
    "moonshotai/kimi-k2:nitro": {
        "input": 0.60,   # $0.60 per 1M input tokens
        "output": 2.50,  # $2.50 per 1M output tokens
        "name": "Kimi K2 Nitro (Image Tags)"
    },
    "x-ai/grok-4-fast": {
        "input": 0.20,   # $0.20 per 1M input tokens
        "output": 0.50,  # $0.50 per 1M output tokens
        "name": "Grok 4 Fast (Memory)"
    },
    "mistralai/ministral-3b": {
        "input": 0.04,   # $0.04 per 1M input tokens
        "output": 0.04,  # $0.04 per 1M output tokens
        "name": "Ministral 3B (Decisions/Summary)"
    }
}

# Image generation cost (RunPod)
IMAGE_COST = 0.0031  # USD per image

# Energy costs per action (from code analysis)
ENERGY_PER_TEXT_MESSAGE = 1  # 1 energy per text message
ENERGY_PER_IMAGE_FREE = 5    # 5 energy per image for free users
ENERGY_PER_IMAGE_PREMIUM = 3 # 3 energy per image for premium users

# Estimated token usage per message (based on typical usage)
AVG_INPUT_TOKENS_PER_MESSAGE = 800   # User message + context + system prompts
AVG_OUTPUT_TOKENS_PER_MESSAGE = 400  # Assistant response

print("\n💰 MODEL PRICING (per 1M tokens):")
print("-" * 80)
for model_id, pricing in MODEL_PRICING.items():
    print(f"   {pricing['name']}")
    print(f"      Model: {model_id}")
    print(f"      Input:  ${pricing['input']:.2f} / 1M tokens")
    print(f"      Output: ${pricing['output']:.2f} / 1M tokens")
    print()

print(f"🖼️  IMAGE GENERATION:")
print(f"   Cost per image: ${IMAGE_COST:.4f}")
print()

print(f"⚡ ENERGY COSTS:")
print(f"   Text message: {ENERGY_PER_TEXT_MESSAGE} energy")
print(f"   Image (free user): {ENERGY_PER_IMAGE_FREE} energy")
print(f"   Image (premium user): {ENERGY_PER_IMAGE_PREMIUM} energy")
print()

if db_connected:
    try:
        # Get today's date range
        today = datetime.utcnow().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())

        print(f"📅 Analyzing data for: {today}")
        print("-" * 80)

        # 1. Count messages sent today (assistant messages = API calls)
        messages_today = session.query(func.count(Message.id)).filter(
            Message.role == 'assistant',
            Message.created_at >= today_start,
            Message.created_at <= today_end
        ).scalar()

        print(f"\n📨 MESSAGES SENT TODAY:")
        print(f"   Assistant messages (API calls): {messages_today}")

        # 2. Count images generated today
        images_today = session.query(func.count(TgAnalyticsEvent.id)).filter(
            TgAnalyticsEvent.event_name == 'image_generated',
            TgAnalyticsEvent.created_at >= today_start,
            TgAnalyticsEvent.created_at <= today_end
        ).scalar()

        print(f"\n🖼️  IMAGES GENERATED TODAY:")
        print(f"   Total images: {images_today}")

        # 3. Get total users and active users
        total_users = session.query(func.count(User.id)).scalar()
        active_users_today = session.query(func.count(func.distinct(Message.chat_id))).join(
            Message.chat
        ).filter(
            Message.created_at >= today_start,
            Message.created_at <= today_end
        ).scalar()

        print(f"\n👥 USER STATISTICS:")
        print(f"   Total users: {total_users}")
        print(f"   Active users today: {active_users_today}")

        # 4. Calculate actual costs from today's usage
        OPENROUTER_SPEND_TODAY = 26.0  # USD (provided by user)

        print(f"\n💰 TODAY'S ACTUAL COSTS:")
        print(f"   OpenRouter spend: ${OPENROUTER_SPEND_TODAY:.2f}")
        print(f"   Total messages: {messages_today}")
        print(f"   Total images: {images_today}")
        
        if messages_today > 0:
            cost_per_message_actual = OPENROUTER_SPEND_TODAY / messages_today
            print(f"   Actual cost per message: ${cost_per_message_actual:.6f}")
        else:
            cost_per_message_actual = None
            print(f"   Actual cost per message: N/A (no messages)")
        
        total_image_cost_today = images_today * IMAGE_COST
        print(f"   Total image cost today: ${total_image_cost_today:.2f}")
        
        print()
    except Exception as e:
        print(f"\n⚠️  Database query failed: {e}")
        print("📊 Continuing with estimated pricing only...\n")
        messages_today = 0
        images_today = 0
        cost_per_message_actual = None
        db_connected = False
else:
    messages_today = 0
    images_today = 0
    cost_per_message_actual = None

print("=" * 80)
print("ESTIMATED COST PER MESSAGE (Based on Model Pricing)")
print("=" * 80)

# Calculate estimated cost per message using main model (deepseek-v3.2)
main_model = MODEL_PRICING["deepseek/deepseek-v3.2"]
cost_per_message_estimated = (
    (AVG_INPUT_TOKENS_PER_MESSAGE / 1_000_000) * main_model["input"] +
    (AVG_OUTPUT_TOKENS_PER_MESSAGE / 1_000_000) * main_model["output"]
)

print(f"\n💬 TEXT MESSAGE COST BREAKDOWN:")
print(f"   Main model: {main_model['name']}")
print(f"   Avg input tokens: {AVG_INPUT_TOKENS_PER_MESSAGE:,}")
print(f"   Avg output tokens: {AVG_OUTPUT_TOKENS_PER_MESSAGE:,}")
print(f"   Input cost: ${(AVG_INPUT_TOKENS_PER_MESSAGE / 1_000_000) * main_model['input']:.6f}")
print(f"   Output cost: ${(AVG_OUTPUT_TOKENS_PER_MESSAGE / 1_000_000) * main_model['output']:.6f}")
print(f"   TOTAL per message: ${cost_per_message_estimated:.6f}")

if cost_per_message_actual:
    print(f"\n📊 COMPARISON:")
    print(f"   Estimated cost: ${cost_per_message_estimated:.6f}")
    print(f"   Actual cost today: ${cost_per_message_actual:.6f}")
    print(f"   Difference: {((cost_per_message_actual / cost_per_message_estimated - 1) * 100):+.1f}%")
    
    # Use actual cost if available
    cost_per_message = cost_per_message_actual
    print(f"\n✅ Using ACTUAL cost for calculations: ${cost_per_message:.6f}")
else:
    cost_per_message = cost_per_message_estimated
    print(f"\n✅ Using ESTIMATED cost for calculations: ${cost_per_message:.6f}")

print()
print("=" * 80)
print("FREE USER (100 ENERGY) COST CALCULATION")
print("=" * 80)

# Scenario 1: All text messages
max_text_messages = 100 // ENERGY_PER_TEXT_MESSAGE
cost_all_text = max_text_messages * cost_per_message
print(f"\n� SCENARIO 1: All Text Messages")
print(f"   Energy available: 100")
print(f"   Energy per message: {ENERGY_PER_TEXT_MESSAGE}")
print(f"   Messages possible: {max_text_messages}")
print(f"   Cost per message: ${cost_per_message:.6f}")
print(f"   TOTAL COST: ${cost_all_text:.4f}")

# Scenario 2: All images
max_images = 100 // ENERGY_PER_IMAGE_FREE
cost_all_images = max_images * IMAGE_COST
print(f"\n🖼️  SCENARIO 2: All Images")
print(f"   Energy available: 100")
print(f"   Energy per image: {ENERGY_PER_IMAGE_FREE}")
print(f"   Images possible: {max_images}")
print(f"   Cost per image: ${IMAGE_COST:.4f}")
print(f"   TOTAL COST: ${cost_all_images:.4f}")

# Scenario 3: Mixed usage (50/50 energy split)
energy_for_text = 50
energy_for_images = 50
mixed_text = energy_for_text // ENERGY_PER_TEXT_MESSAGE
mixed_images = energy_for_images // ENERGY_PER_IMAGE_FREE
cost_mixed = (mixed_text * cost_per_message) + (mixed_images * IMAGE_COST)
print(f"\n🔀 SCENARIO 3: Mixed Usage (50/50 energy split)")
print(f"   Energy for text: {energy_for_text}")
print(f"   Energy for images: {energy_for_images}")
print(f"   Text messages: {mixed_text} × ${cost_per_message:.6f} = ${mixed_text * cost_per_message:.4f}")
print(f"   Images: {mixed_images} × ${IMAGE_COST:.4f} = ${mixed_images * IMAGE_COST:.4f}")
print(f"   TOTAL COST: ${cost_mixed:.4f}")

# Scenario 4: Typical usage pattern (80% text, 20% images by energy)
energy_for_text_typical = 80
energy_for_images_typical = 20
typical_text = energy_for_text_typical // ENERGY_PER_TEXT_MESSAGE
typical_images = energy_for_images_typical // ENERGY_PER_IMAGE_FREE
cost_typical = (typical_text * cost_per_message) + (typical_images * IMAGE_COST)
print(f"\n📊 SCENARIO 4: Typical Usage (80% text, 20% images)")
print(f"   Energy for text: {energy_for_text_typical}")
print(f"   Energy for images: {energy_for_images_typical}")
print(f"   Text messages: {typical_text} × ${cost_per_message:.6f} = ${typical_text * cost_per_message:.4f}")
print(f"   Images: {typical_images} × ${IMAGE_COST:.4f} = ${typical_images * IMAGE_COST:.4f}")
print(f"   TOTAL COST: ${cost_typical:.4f}")

# Average across scenarios
avg_cost = (cost_all_text + cost_all_images + cost_mixed + cost_typical) / 4
print(f"\n📈 AVERAGE COST ACROSS ALL SCENARIOS: ${avg_cost:.4f}")

print()
print("=" * 80)
print("FINAL SUMMARY")
print("=" * 80)

if db_connected and messages_today > 0:
    print(f"\n📊 TODAY'S ACTUAL DATA:")
    print(f"   OpenRouter spend: ${26.0:.2f}")
    print(f"   Messages sent: {messages_today:,}")
    print(f"   Images generated: {images_today:,}")
    print(f"   Cost per message: ${cost_per_message:.6f}")
    print(f"   Cost per image: ${IMAGE_COST:.4f}")

print(f"\n💡 FREE USER (100 ENERGY) ESTIMATED COSTS:")
print(f"   All text (100 messages):     ${cost_all_text:.4f}")
print(f"   All images (20 images):      ${cost_all_images:.4f}")
print(f"   Mixed 50/50:                 ${cost_mixed:.4f}")
print(f"   Typical 80/20:               ${cost_typical:.4f}")
print(f"   Average:                     ${avg_cost:.4f}")

print(f"\n🎯 RECOMMENDED ESTIMATE:")
print(f"   Based on typical usage pattern (80% text, 20% images):")
print(f"   Cost per free user (100 energy): ${cost_typical:.4f}")
print(f"   Or approximately: ${cost_typical:.2f}")

print()
print("=" * 80)

if db_connected:
    session.close()
