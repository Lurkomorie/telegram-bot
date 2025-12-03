"""
Dialogue Evaluator
Evaluates AI dialogue responses for quality, character consistency, and engagement.
"""
from app.core.evaluators.base import BaseEvaluator


class DialogueEvaluator(BaseEvaluator):
    """Evaluator for dialogue/response generation quality"""
    
    name = "dialogue"
    description = "Evaluates dialogue responses for quality and character consistency"
    
    def get_criteria(self) -> list[dict]:
        return [
            {
                "name": "language_consistency",
                "description": "Response uses ONE language consistently throughout. No mixing of English/Russian/etc.",
                "weight": 2.0
            },
            {
                "name": "in_character",
                "description": "Response matches the persona's personality, speaking style, and traits",
                "weight": 2.0
            },
            {
                "name": "responds_to_user",
                "description": "Response directly addresses what the user said/asked, not generic",
                "weight": 2.0
            },
            {
                "name": "no_repetition",
                "description": "Response doesn't repeat phrases from previous messages or itself",
                "weight": 1.5
            },
            {
                "name": "formatting",
                "description": "Uses correct formatting (italics for actions, bold for speech)",
                "weight": 1.0
            },
            {
                "name": "engagement",
                "description": "Response encourages continued conversation with hooks/questions",
                "weight": 1.5
            },
        ]
    
    def get_evaluation_prompt(
        self,
        user_message: str,
        assistant_response: str,
        persona_name: str,
        persona_prompt: str,
        context_messages: list = None,
        **kwargs
    ) -> str:
        # Format context if available
        context_str = ""
        if context_messages:
            context_str = "RECENT CONVERSATION CONTEXT:\n"
            for msg in context_messages[-5:]:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")[:200]
                context_str += f"  {role.upper()}: {content}...\n"
            context_str += "\n"
        
        return f"""EVALUATE THIS DIALOGUE RESPONSE:

PERSONA:
  Name: {persona_name}
  Personality: {persona_prompt[:500] if persona_prompt else "Not specified"}...

{context_str}USER MESSAGE:
{user_message}

ASSISTANT RESPONSE (to evaluate):
{assistant_response}

Evaluate the assistant response against all criteria. Focus on:
1. Is it in one language only? (Critical for non-English users)
2. Does it feel like the persona would say this?
3. Does it directly address what the user said?
4. Is there any repetition from context?
5. Is formatting correct (actions in italics, speech in bold)?
6. Does it end with a hook to continue conversation?"""

