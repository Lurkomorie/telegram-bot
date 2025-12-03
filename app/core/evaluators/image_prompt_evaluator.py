"""
Image Prompt Evaluator
Evaluates SDXL image prompt generation quality.
"""
from app.core.evaluators.base import BaseEvaluator


class ImagePromptEvaluator(BaseEvaluator):
    """Evaluator for image prompt generation quality"""
    
    name = "image_prompt"
    description = "Evaluates SDXL image prompt accuracy and quality"
    
    def get_criteria(self) -> list[dict]:
        return [
            {
                "name": "matches_dialogue",
                "description": "Image prompt depicts what is ACTUALLY happening in the dialogue, not what user requested",
                "weight": 3.0
            },
            {
                "name": "valid_sdxl_tags",
                "description": "Uses proper SDXL/Danbooru tag format (comma-separated, descriptive tags)",
                "weight": 1.5
            },
            {
                "name": "correct_intensity",
                "description": "Intensity tag (sensual/erotic/explicit NSFW) matches actual scene content",
                "weight": 2.0
            },
            {
                "name": "solo_vs_couple",
                "description": "Correctly uses 'solo' tags for single person or couple tags for sexual scenes",
                "weight": 1.5
            },
            {
                "name": "no_forbidden_tags",
                "description": "Avoids forbidden tags like 'wicked smile', 'teasing smile', 'sparkling eyes'",
                "weight": 1.0
            },
            {
                "name": "hand_protection",
                "description": "Includes hand protection tags when hands are visible",
                "weight": 1.0
            },
        ]
    
    def get_evaluation_prompt(
        self,
        dialogue_response: str,
        user_message: str,
        image_prompt: str,
        state: str = None,
        **kwargs
    ) -> str:
        return f"""EVALUATE THIS IMAGE PROMPT:

DIALOGUE RESPONSE (what is ACTUALLY happening):
{dialogue_response}

USER MESSAGE (what user requested - may NOT be what's happening):
{user_message}

CURRENT STATE:
{state[:500] if state else "(No state)"}...

GENERATED IMAGE PROMPT (to evaluate):
{image_prompt}

Critical evaluation points:
1. Does the image show what the DIALOGUE describes, or what the USER requested? 
   (Should match DIALOGUE - if AI refused/hesitated, image should show that)
2. Are the tags in proper SDXL format?
3. Is the intensity tag (sensual/erotic/explicit) appropriate for the actual scene?
4. If only one person in scene, are solo tags present? If sex, are couple tags present?
5. Does it avoid forbidden tags (wicked smile, teasing smile, sparkling eyes)?
6. Are hand protection tags included when hands would be visible?"""

