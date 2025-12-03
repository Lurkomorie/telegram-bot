"""
Base evaluator class and result types.
"""
import json
import httpx
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Any
from app.settings import settings


@dataclass
class EvaluationResult:
    """Result of a single evaluation"""
    evaluator: str
    score: float  # 0-10
    reasoning: str
    criteria_scores: dict = field(default_factory=dict)  # Individual criterion scores
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "evaluator": self.evaluator,
            "score": self.score,
            "reasoning": self.reasoning,
            "criteria_scores": self.criteria_scores,
            "metadata": self.metadata,
        }


class BaseEvaluator(ABC):
    """Base class for all evaluators"""
    
    name: str = "base"
    description: str = "Base evaluator"
    
    # GPT-4o for evaluation
    EVAL_MODEL = "gpt-4o"
    EVAL_API_URL = "https://openrouter.ai/api/v1/chat/completions"
    
    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
    
    @abstractmethod
    def get_evaluation_prompt(self, **kwargs) -> str:
        """
        Build the evaluation prompt for GPT-4o.
        Each evaluator implements their specific criteria.
        """
        pass
    
    @abstractmethod
    def get_criteria(self) -> list[dict]:
        """
        Return list of evaluation criteria.
        Each criterion: {"name": str, "description": str, "weight": float}
        """
        pass
    
    async def evaluate(self, **kwargs) -> EvaluationResult:
        """
        Run evaluation using GPT-4o.
        
        Returns:
            EvaluationResult with score, reasoning, and per-criterion scores
        """
        prompt = self.get_evaluation_prompt(**kwargs)
        criteria = self.get_criteria()
        
        # Build system message with scoring instructions
        system_message = f"""You are an expert evaluator for AI chatbot responses. 
You will evaluate outputs based on specific criteria and provide structured scores.

OUTPUT FORMAT (JSON only, no other text):
{{
    "overall_score": <0-10 float>,
    "reasoning": "<1-2 sentence summary>",
    "criteria_scores": {{
        "<criterion_name>": {{
            "score": <0-10 float>,
            "note": "<brief note>"
        }}
    }}
}}

CRITERIA TO EVALUATE:
{json.dumps(criteria, indent=2)}

SCORING GUIDE:
- 0-2: Completely fails the criterion
- 3-4: Major issues, barely acceptable
- 5-6: Adequate but with notable flaws
- 7-8: Good quality, minor issues
- 9-10: Excellent, meets all expectations

Be strict but fair. Provide actionable feedback in your reasoning."""

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = await self._call_gpt4o(messages)
            result = self._parse_response(response)
            return result
        except Exception as e:
            # Return error result
            return EvaluationResult(
                evaluator=self.name,
                score=0,
                reasoning=f"Evaluation error: {str(e)}",
                metadata={"error": str(e)}
            )
    
    async def _call_gpt4o(self, messages: list) -> str:
        """Call GPT-4o via OpenRouter"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://telegram-bot-eval",
            "X-Title": "Bot Evaluation"
        }
        
        body = {
            "model": self.EVAL_MODEL,
            "messages": messages,
            "temperature": 0.3,  # Low temperature for consistent scoring
            "max_tokens": 1000,
            "response_format": {"type": "json_object"}  # Request JSON response
        }
        
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                self.EVAL_API_URL,
                json=body,
                headers=headers
            )
            response.raise_for_status()
            
            data = response.json()
            return data["choices"][0]["message"]["content"]
    
    def _parse_response(self, response: str) -> EvaluationResult:
        """Parse GPT-4o JSON response into EvaluationResult"""
        try:
            # Clean response (remove markdown if present)
            clean = response.strip()
            if clean.startswith("```json"):
                clean = clean[7:]
            if clean.startswith("```"):
                clean = clean[3:]
            if clean.endswith("```"):
                clean = clean[:-3]
            clean = clean.strip()
            
            data = json.loads(clean)
            
            return EvaluationResult(
                evaluator=self.name,
                score=float(data.get("overall_score", 0)),
                reasoning=data.get("reasoning", "No reasoning provided"),
                criteria_scores=data.get("criteria_scores", {}),
            )
        except json.JSONDecodeError as e:
            return EvaluationResult(
                evaluator=self.name,
                score=0,
                reasoning=f"Failed to parse evaluation response: {e}",
                metadata={"raw_response": response[:500]}
            )

