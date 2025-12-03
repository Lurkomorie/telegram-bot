"""
Image Decision Evaluator
Evaluates the image generation decision logic.
"""
from app.core.evaluators.base import BaseEvaluator


class ImageDecisionEvaluator(BaseEvaluator):
    """Evaluator for image generation decision quality"""
    
    name = "image_decision"
    description = "Evaluates image generation decision accuracy"
    
    def get_criteria(self) -> list[dict]:
        return [
            {
                "name": "location_change_detected",
                "description": "Correctly identifies when location has changed (should generate image)",
                "weight": 2.0
            },
            {
                "name": "visual_request_detected",
                "description": "Correctly identifies explicit visual requests ('show me', 'let me see')",
                "weight": 2.0
            },
            {
                "name": "action_significance",
                "description": "Correctly identifies significant physical actions worth depicting",
                "weight": 1.5
            },
            {
                "name": "clothing_change_detected",
                "description": "Correctly identifies clothing changes (should generate image)",
                "weight": 1.5
            },
            {
                "name": "pure_dialogue_skipped",
                "description": "Correctly skips image for pure dialogue with no visual changes",
                "weight": 1.5
            },
            {
                "name": "consistent_reasoning",
                "description": "Decision reasoning is clear and matches the rules",
                "weight": 1.5
            },
        ]
    
    def get_evaluation_prompt(
        self,
        user_message: str,
        previous_state: str,
        decision: bool,
        decision_reason: str,
        context_messages: list = None,
        **kwargs
    ) -> str:
        # Format context
        context_str = ""
        if context_messages:
            context_str = "RECENT CONTEXT:\n"
            for msg in context_messages[-3:]:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")[:150]
                context_str += f"  {role.upper()}: {content}...\n"
            context_str += "\n"
        
        decision_str = "YES (generate image)" if decision else "NO (skip image)"
        
        return f"""EVALUATE THIS IMAGE GENERATION DECISION:

PREVIOUS STATE:
{previous_state[:400] if previous_state else "(No previous state)"}...

{context_str}USER MESSAGE:
{user_message}

DECISION MADE: {decision_str}
REASON GIVEN: {decision_reason}

Rules for when to generate images (YES):
- Location change detected
- User explicitly asks to see something
- Significant action/movement scene
- Clothing/appearance change
- Sexual activity initiation or position change
- Dramatic/emotional peak moment

Rules for when to skip images (NO):
- Pure dialogue/conversation
- No visual changes from previous state
- Abstract/internal thoughts
- Repetitive scenarios

Was this decision correct given the rules?"""

