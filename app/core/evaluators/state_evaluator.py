"""
State Evaluator
Evaluates conversation state resolution for consistency and accuracy.
"""
from app.core.evaluators.base import BaseEvaluator


class StateEvaluator(BaseEvaluator):
    """Evaluator for state resolution quality"""
    
    name = "state"
    description = "Evaluates conversation state resolution accuracy"
    
    def get_criteria(self) -> list[dict]:
        return [
            {
                "name": "all_fields_present",
                "description": "State contains all required fields: relationshipStage, emotions, moodNotes, location, description, aiClothing, userClothing, terminateDialog",
                "weight": 2.0
            },
            {
                "name": "unchanged_preserved",
                "description": "Fields that weren't mentioned in conversation are preserved from previous state (especially location, clothing)",
                "weight": 2.5
            },
            {
                "name": "logical_progression",
                "description": "Changes to state make sense given what happened in the conversation",
                "weight": 2.0
            },
            {
                "name": "clothing_specificity",
                "description": "aiClothing is specific with colors, not vague like 'casual outfit'",
                "weight": 1.5
            },
            {
                "name": "format_correct",
                "description": "State follows the exact format: key=\"value\" | key=\"value\"",
                "weight": 1.0
            },
            {
                "name": "no_hallucination",
                "description": "State only reflects what was actually said/done, no invented changes",
                "weight": 1.0
            },
        ]
    
    def get_evaluation_prompt(
        self,
        previous_state: str,
        new_state: str,
        user_message: str,
        assistant_response: str,
        **kwargs
    ) -> str:
        return f"""EVALUATE THIS STATE RESOLUTION:

PREVIOUS STATE:
{previous_state if previous_state else "(No previous state - new conversation)"}

USER MESSAGE:
{user_message}

ASSISTANT RESPONSE:
{assistant_response[:500]}...

NEW STATE (to evaluate):
{new_state}

Evaluate the state update. Key questions:
1. Does it contain all required fields?
2. Were unchanged values preserved? (Critical: If location/clothing wasn't mentioned, it should stay the same)
3. Do the changes make logical sense given the conversation?
4. Is aiClothing specific (e.g., "red dress" not "casual outfit")?
5. Is the format correct (key="value" | key="value")?
6. Did the resolver invent any changes not supported by conversation?"""

