# Evaluation Comparison Report

Generated: 2025-12-03T11:10:46.723838

Runs compared: test_baseline, test_second

## Summary Scores

| Brain | test_baseline | test_second | Change |
|-------|--------|--------|--------|
| DIALOGUE | 7.55 (2) | 8.15 (2) | +0.60 🟢 |
| STATE | 6.50 (2) | 7.50 (2) | +1.00 🟢 |

## Detailed Analysis

### Dialogue

**test_baseline**: 7.55/10 (n=2)

Criteria breakdown:
  - engagement: 7.50
  - formatting: 6.00
  - in_character: 6.50
  - language_consistency: 9.50
  - no_repetition: 8.50
  - responds_to_user: 8.50

**test_second**: 8.15/10 (n=2)

Criteria breakdown:
  - engagement: 6.50
  - formatting: 7.00
  - in_character: 8.50
  - language_consistency: 10.00
  - no_repetition: 9.50
  - responds_to_user: 9.50

### State

**test_baseline**: 6.50/10 (n=2)

Criteria breakdown:
  - all_fields_present: 10.00
  - clothing_specificity: 8.50
  - format_correct: 10.00
  - logical_progression: 6.00
  - no_hallucination: 4.00
  - unchanged_preserved: 8.00

**test_second**: 7.50/10 (n=2)

Criteria breakdown:
  - all_fields_present: 10.00
  - clothing_specificity: 10.00
  - format_correct: 8.50
  - logical_progression: 7.00
  - no_hallucination: 5.00
  - unchanged_preserved: 9.50


## Notable Changes

Comparing test_baseline → test_second:

### Top Improvements

- **state** +2.0 (exchange #1)
  - 4.5 → 6.5
  - Message: "Покажи киску и я помогу тебе с машиной..."
