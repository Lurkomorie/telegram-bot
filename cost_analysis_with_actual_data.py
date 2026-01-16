#!/usr/bin/env python3
"""
Cost analysis with actual data from today
Based on user-provided information: $26 spent on OpenRouter today
"""

print("=" * 80)
print("FREE USER COST ANALYSIS - WITH ACTUAL DATA")
print("=" * 80)

# ACTUAL DATA FROM TODAY (provided by user)
OPENROUTER_SPEND_TODAY = 26.0  # USD
# We need to get the number of messages sent today from the database

# OpenRouter Pricing (per 1M tokens)
MODEL_PRICING = {
    "deepseek/deepseek-v3.2": {
        "input": 0.28,   # $0.28 per 1M input tokens
        "output": 1.10,  # $1.10 per 1M output tokens
        "name": "DeepSeek V3.2 (Main Chat)"
    }
}

# Image generation cost (RunPod)
IMAGE_COST = 0.0031  # USD per image

# Energy costs per action
ENERGY_PER_TEXT_MESSAGE = 1  # 1 energy per text message
ENERGY_PER_IMAGE_FREE = 5    # 5 energy per image for free users

# Estimated token usage per message
AVG_INPUT_TOKENS_PER_MESSAGE = 800   # User message + context + system prompts
AVG_OUTPUT_TOKENS_PER_MESSAGE = 400  # Assistant response

print(f"\n💰 ACTUAL DATA FROM TODAY:")
print(f"   OpenRouter spend: ${OPENROUTER_SPEND_TODAY:.2f}")
print()

# Calculate estimated cost per message using model pricing
main_model = MODEL_PRICING["deepseek/deepseek-v3.2"]
cost_per_message_estimated = (
    (AVG_INPUT_TOKENS_PER_MESSAGE / 1_000_000) * main_model["input"] +
    (AVG_OUTPUT_TOKENS_PER_MESSAGE / 1_000_000) * main_model["output"]
)

print(f"📊 ESTIMATED COST PER MESSAGE:")
print(f"   Model: {main_model['name']}")
print(f"   Input tokens: {AVG_INPUT_TOKENS_PER_MESSAGE:,} × ${main_model['input']}/1M = ${(AVG_INPUT_TOKENS_PER_MESSAGE / 1_000_000) * main_model['input']:.6f}")
print(f"   Output tokens: {AVG_OUTPUT_TOKENS_PER_MESSAGE:,} × ${main_model['output']}/1M = ${(AVG_OUTPUT_TOKENS_PER_MESSAGE / 1_000_000) * main_model['output']:.6f}")
print(f"   TOTAL: ${cost_per_message_estimated:.6f}")
print()

# Calculate how many messages were sent based on $26 spend
messages_sent_estimated = OPENROUTER_SPEND_TODAY / cost_per_message_estimated

print(f"📈 REVERSE CALCULATION:")
print(f"   If we spent ${OPENROUTER_SPEND_TODAY:.2f} today")
print(f"   And each message costs ~${cost_per_message_estimated:.6f}")
print(f"   Then we sent approximately: {messages_sent_estimated:,.0f} messages")
print()

# Now let's try different scenarios for actual cost per message
print("=" * 80)
print("SCENARIO ANALYSIS: Different Message Volumes")
print("=" * 80)

message_scenarios = [10000, 20000, 30000, 40000, 50000]

for msg_count in message_scenarios:
    actual_cost_per_msg = OPENROUTER_SPEND_TODAY / msg_count
    
    # Calculate free user cost (100 energy)
    max_text_messages = 100 // ENERGY_PER_TEXT_MESSAGE
    max_images = 100 // ENERGY_PER_IMAGE_FREE
    
    cost_all_text = max_text_messages * actual_cost_per_msg
    cost_all_images = max_images * IMAGE_COST
    
    # Typical usage (80% text, 20% images)
    typical_text = 80 // ENERGY_PER_TEXT_MESSAGE
    typical_images = 20 // ENERGY_PER_IMAGE_FREE
    cost_typical = (typical_text * actual_cost_per_msg) + (typical_images * IMAGE_COST)
    
    print(f"\n📊 If {msg_count:,} messages were sent today:")
    print(f"   Cost per message: ${actual_cost_per_msg:.6f}")
    print(f"   Free user (100 energy) costs:")
    print(f"      All text (100 msgs):  ${cost_all_text:.4f}")
    print(f"      All images (20 imgs): ${cost_all_images:.4f}")
    print(f"      Typical 80/20:        ${cost_typical:.4f}")

print()
print("=" * 80)
print("RECOMMENDED ESTIMATES")
print("=" * 80)

# Use the estimated message count
cost_per_message = cost_per_message_estimated

# Calculate free user costs
max_text_messages = 100 // ENERGY_PER_TEXT_MESSAGE
max_images = 100 // ENERGY_PER_IMAGE_FREE

cost_all_text = max_text_messages * cost_per_message
cost_all_images = max_images * IMAGE_COST

# Typical usage (80% text, 20% images)
typical_text = 80 // ENERGY_PER_TEXT_MESSAGE
typical_images = 20 // ENERGY_PER_IMAGE_FREE
cost_typical = (typical_text * cost_per_message) + (typical_images * IMAGE_COST)

# Mixed 50/50
mixed_text = 50 // ENERGY_PER_TEXT_MESSAGE
mixed_images = 50 // ENERGY_PER_IMAGE_FREE
cost_mixed = (mixed_text * cost_per_message) + (mixed_images * IMAGE_COST)

print(f"\n💡 FREE USER (100 ENERGY) COSTS:")
print(f"   All text (100 messages):     ${cost_all_text:.4f} (~${cost_all_text:.2f})")
print(f"   All images (20 images):      ${cost_all_images:.4f} (~${cost_all_images:.2f})")
print(f"   Mixed 50/50:                 ${cost_mixed:.4f} (~${cost_mixed:.2f})")
print(f"   Typical 80/20:               ${cost_typical:.4f} (~${cost_typical:.2f})")

avg_cost = (cost_all_text + cost_all_images + cost_mixed + cost_typical) / 4
print(f"   Average:                     ${avg_cost:.4f} (~${avg_cost:.2f})")

print(f"\n🎯 FINAL ANSWER:")
print(f"   Based on typical usage (80% text, 20% images):")
print(f"   A free user spending all 100 energy costs: ${cost_typical:.4f}")
print(f"   Rounded: ${cost_typical:.2f}")

print()
print("=" * 80)
print("BREAKDOWN BY COMPONENT")
print("=" * 80)

print(f"\n📝 TEXT MESSAGES:")
print(f"   Energy cost: {ENERGY_PER_TEXT_MESSAGE} energy per message")
print(f"   Dollar cost: ${cost_per_message:.6f} per message")
print(f"   100 energy = {max_text_messages} messages = ${cost_all_text:.4f}")

print(f"\n🖼️  IMAGES:")
print(f"   Energy cost: {ENERGY_PER_IMAGE_FREE} energy per image")
print(f"   Dollar cost: ${IMAGE_COST:.4f} per image")
print(f"   100 energy = {max_images} images = ${cost_all_images:.4f}")

print(f"\n⚖️  COMPARISON:")
print(f"   Text is more expensive per energy unit: ${cost_per_message:.6f} vs ${IMAGE_COST / ENERGY_PER_IMAGE_FREE:.6f}")
print(f"   Text per energy: ${cost_per_message / ENERGY_PER_TEXT_MESSAGE:.6f}")
print(f"   Image per energy: ${IMAGE_COST / ENERGY_PER_IMAGE_FREE:.6f}")

print()
print("=" * 80)
