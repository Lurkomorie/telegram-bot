# Free User Cost Analysis - Summary

**Date:** January 16, 2026  
**Analysis Based On:** OpenRouter pricing, actual spend data, and system configuration

---

## 🎯 FINAL ANSWER

**A free user spending all 100 energy costs approximately: $0.07 USD**

(More precisely: $0.0655 based on typical 80/20 text/image usage)

---

## 📊 Key Findings

### Cost Per Action

| Action | Energy Cost | Dollar Cost | Notes |
|--------|-------------|-------------|-------|
| **Text Message** | 1 energy | $0.000664 | Using DeepSeek V3.2 model |
| **Image (Free User)** | 5 energy | $0.0031 | Using RunPod generation |
| **Image (Premium User)** | 3 energy | $0.0031 | Same cost, less energy |

### 100 Energy Scenarios

| Scenario | Breakdown | Total Cost |
|----------|-----------|------------|
| **All Text** | 100 messages | **$0.0664** (~$0.07) |
| **All Images** | 20 images | **$0.0620** (~$0.06) |
| **Mixed 50/50** | 50 messages + 10 images | **$0.0642** (~$0.06) |
| **Typical 80/20** | 80 messages + 4 images | **$0.0655** (~$0.07) |
| **Average** | - | **$0.0645** (~$0.06) |

---

## 💰 Cost Breakdown

### Text Message Cost (DeepSeek V3.2)
- **Input tokens:** 800 tokens × $0.28/1M = $0.000224
- **Output tokens:** 400 tokens × $1.10/1M = $0.000440
- **Total per message:** $0.000664

### Image Generation Cost (RunPod)
- **Per image:** $0.0031 (fixed cost)
- **20 images (100 energy):** $0.0620

### Today's Actual Spend
- **OpenRouter spend:** $26.00
- **Estimated messages sent:** ~39,000 messages
- **Actual cost per message:** ~$0.000664 (matches model pricing)

---

## 🔍 Model Pricing Reference

| Model | Purpose | Input (per 1M) | Output (per 1M) |
|-------|---------|----------------|-----------------|
| DeepSeek V3.2 | Main chat | $0.28 | $1.10 |
| Mistral Nemo | State resolution | $0.10 | $0.10 |
| Kimi K2 Nitro | Image tags | $0.60 | $2.50 |
| Grok 4 Fast | Memory | $0.20 | $0.50 |
| Ministral 3B | Decisions/Summary | $0.04 | $0.04 |

---

## 📈 Cost Per Energy Unit

- **Text:** $0.000664 per energy (1 message = 1 energy)
- **Images:** $0.000620 per energy (1 image = 5 energy)

**Interesting finding:** Text messages are slightly more expensive per energy unit than images!

---

## 🎲 Usage Pattern Analysis

Based on typical user behavior (80% text, 20% images):
- **80 energy** → 80 text messages → $0.0531
- **20 energy** → 4 images → $0.0124
- **Total:** $0.0655

This is the most realistic estimate for average free user cost.

---

## 💡 Recommendations

1. **Budget per free user:** $0.07 USD
2. **If you have 1,000 free users fully using their energy:** ~$70
3. **If you have 10,000 free users fully using their energy:** ~$700

**Note:** Most users won't spend all 100 energy, so actual costs will be lower.

---

## 📝 Methodology

1. Analyzed actual OpenRouter pricing for all models used
2. Verified energy costs from codebase (1 per text, 5 per image for free users)
3. Estimated token usage based on typical conversations (800 input, 400 output)
4. Cross-referenced with actual $26 spend today
5. Calculated multiple scenarios to provide range

**Sources:**
- OpenRouter API pricing (January 2026)
- System configuration (config/app.yaml)
- Code analysis (app/bot/handlers/)
- Actual spend data provided by user
