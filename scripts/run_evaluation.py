"""
Run evaluation on a dataset using the current prompts.
Tests dialogue, state, image prompt, and image decision quality.

Usage:
    python scripts/run_evaluation.py --dataset eval_dataset.json --name "baseline_v1"
    python scripts/run_evaluation.py --dataset eval_dataset.json --name "improved_v2" --brains dialogue,state
"""
import sys
import os
import json
import argparse
import asyncio
from datetime import datetime
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.settings import load_configs
from app.core.evaluators import (
    DialogueEvaluator,
    StateEvaluator,
    ImagePromptEvaluator,
    ImageDecisionEvaluator,
)
from app.core.brains.dialogue_specialist import generate_dialogue
from app.core.brains.state_resolver import resolve_state
from app.core.brains.image_prompt_engineer import generate_image_plan
from app.core.brains.image_decision_specialist import should_generate_image


async def run_evaluation(
    dataset_path: str,
    run_name: str,
    brains: list[str] = None,
    max_exchanges: int = None,
    save_outputs: bool = True
) -> dict:
    """
    Run evaluation on dataset.
    
    Args:
        dataset_path: Path to evaluation dataset JSON
        run_name: Name for this evaluation run
        brains: List of brains to evaluate (default: all)
        max_exchanges: Maximum exchanges to evaluate per chat
        save_outputs: Whether to save generated outputs
    
    Returns:
        Evaluation results dictionary
    """
    # Default to all brains
    if brains is None:
        brains = ["dialogue", "state", "image_prompt", "image_decision"]
    
    # Load dataset
    full_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "eval_data",
        dataset_path
    )
    
    if not os.path.exists(full_path):
        print(f"❌ Dataset not found: {full_path}")
        return None
    
    with open(full_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)
    
    print(f"\n🧪 Running evaluation: {run_name}")
    print(f"   Dataset: {dataset_path}")
    print(f"   Chats: {dataset['metadata']['num_chats']}")
    print(f"   Brains: {', '.join(brains)}")
    print(f"   Max exchanges: {max_exchanges or 'all'}\n")
    
    # Initialize evaluators
    evaluators = {
        "dialogue": DialogueEvaluator(),
        "state": StateEvaluator(),
        "image_prompt": ImagePromptEvaluator(),
        "image_decision": ImageDecisionEvaluator(),
    }
    
    # Results structure
    results = {
        "run_name": run_name,
        "timestamp": datetime.utcnow().isoformat(),
        "dataset": dataset_path,
        "brains_evaluated": brains,
        "summary": {
            brain: {"total_score": 0, "count": 0, "avg_score": 0}
            for brain in brains
        },
        "evaluations": [],
        "generated_outputs": [] if save_outputs else None,
    }
    
    total_exchanges = 0
    
    for chat_idx, chat in enumerate(dataset["chats"]):
        persona = chat["persona"]
        memory = chat.get("memory")
        
        print(f"\n📋 Chat {chat_idx + 1}/{len(dataset['chats'])}: {persona['name']}")
        
        exchanges_to_eval = chat["exchanges"]
        if max_exchanges:
            exchanges_to_eval = exchanges_to_eval[:max_exchanges]
        
        for ex_idx, exchange in enumerate(exchanges_to_eval):
            total_exchanges += 1
            
            print(f"   Exchange {ex_idx + 1}/{len(exchanges_to_eval)}...", end=" ", flush=True)
            
            user_message = exchange["user_message"]
            original_response = exchange["assistant_response"]
            context = exchange.get("context_messages", [])
            state = exchange.get("state_after", {})
            state_str = state.get("state") if isinstance(state, dict) else str(state)
            
            exchange_results = {
                "chat_id": chat["chat_id"],
                "exchange_idx": ex_idx,
                "user_message": user_message[:100],
                "evaluations": {}
            }
            
            generated_outputs = {}
            
            # === Dialogue Evaluation ===
            if "dialogue" in brains:
                try:
                    # Generate new response
                    new_response = await generate_dialogue(
                        state=state_str,
                        chat_history=context,
                        user_message=user_message,
                        persona=persona,
                        memory=memory
                    )
                    generated_outputs["dialogue"] = new_response
                    
                    # Evaluate
                    eval_result = await evaluators["dialogue"].evaluate(
                        user_message=user_message,
                        assistant_response=new_response,
                        persona_name=persona["name"],
                        persona_prompt=persona.get("prompt", ""),
                        context_messages=context
                    )
                    
                    exchange_results["evaluations"]["dialogue"] = eval_result.to_dict()
                    results["summary"]["dialogue"]["total_score"] += eval_result.score
                    results["summary"]["dialogue"]["count"] += 1
                except Exception as e:
                    print(f"dialogue error: {e}", end=" ")
            
            # === State Evaluation ===
            if "state" in brains:
                try:
                    # Get previous state from context
                    prev_state = None
                    for msg in reversed(context):
                        if msg.get("state_snapshot"):
                            prev_state = msg["state_snapshot"].get("state")
                            break
                    
                    # Generate new state
                    new_state = await resolve_state(
                        previous_state=prev_state,
                        chat_history=context,
                        user_message=user_message,
                        persona_name=persona["name"]
                    )
                    generated_outputs["state"] = new_state
                    
                    # Evaluate
                    eval_result = await evaluators["state"].evaluate(
                        previous_state=prev_state,
                        new_state=new_state,
                        user_message=user_message,
                        assistant_response=original_response
                    )
                    
                    exchange_results["evaluations"]["state"] = eval_result.to_dict()
                    results["summary"]["state"]["total_score"] += eval_result.score
                    results["summary"]["state"]["count"] += 1
                except Exception as e:
                    print(f"state error: {e}", end=" ")
            
            # === Image Prompt Evaluation ===
            if "image_prompt" in brains:
                try:
                    # Generate image prompt
                    image_prompt = await generate_image_plan(
                        state=state_str or "",
                        dialogue_response=original_response,
                        user_message=user_message,
                        persona=persona,
                        chat_history=context
                    )
                    generated_outputs["image_prompt"] = image_prompt
                    
                    # Evaluate
                    eval_result = await evaluators["image_prompt"].evaluate(
                        dialogue_response=original_response,
                        user_message=user_message,
                        image_prompt=image_prompt,
                        state=state_str
                    )
                    
                    exchange_results["evaluations"]["image_prompt"] = eval_result.to_dict()
                    results["summary"]["image_prompt"]["total_score"] += eval_result.score
                    results["summary"]["image_prompt"]["count"] += 1
                except Exception as e:
                    print(f"image_prompt error: {e}", end=" ")
            
            # === Image Decision Evaluation ===
            if "image_decision" in brains:
                try:
                    # Get previous state
                    prev_state = None
                    for msg in reversed(context):
                        if msg.get("state_snapshot"):
                            prev_state = msg["state_snapshot"].get("state")
                            break
                    
                    # Make decision
                    decision, reason = await should_generate_image(
                        previous_state=prev_state or "",
                        user_message=user_message,
                        chat_history=context,
                        persona_name=persona["name"]
                    )
                    generated_outputs["image_decision"] = {"decision": decision, "reason": reason}
                    
                    # Evaluate
                    eval_result = await evaluators["image_decision"].evaluate(
                        user_message=user_message,
                        previous_state=prev_state,
                        decision=decision,
                        decision_reason=reason,
                        context_messages=context
                    )
                    
                    exchange_results["evaluations"]["image_decision"] = eval_result.to_dict()
                    results["summary"]["image_decision"]["total_score"] += eval_result.score
                    results["summary"]["image_decision"]["count"] += 1
                except Exception as e:
                    print(f"image_decision error: {e}", end=" ")
            
            results["evaluations"].append(exchange_results)
            
            if save_outputs:
                results["generated_outputs"].append({
                    "chat_id": chat["chat_id"],
                    "exchange_idx": ex_idx,
                    "outputs": generated_outputs
                })
            
            print("✓")
    
    # Calculate averages
    for brain in brains:
        if results["summary"][brain]["count"] > 0:
            results["summary"][brain]["avg_score"] = (
                results["summary"][brain]["total_score"] / 
                results["summary"][brain]["count"]
            )
    
    # Save results
    results_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "eval_data",
        "results"
    )
    os.makedirs(results_dir, exist_ok=True)
    
    results_path = os.path.join(results_dir, f"{run_name}.json")
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print(f"\n" + "="*50)
    print(f"📊 EVALUATION RESULTS: {run_name}")
    print("="*50)
    
    for brain in brains:
        summary = results["summary"][brain]
        avg = summary["avg_score"]
        count = summary["count"]
        
        # Color-coded score
        if avg >= 7:
            emoji = "🟢"
        elif avg >= 5:
            emoji = "🟡"
        else:
            emoji = "🔴"
        
        print(f"   {emoji} {brain.upper()}: {avg:.2f}/10 ({count} evaluations)")
    
    print(f"\n   📁 Results saved to: {results_path}")
    print("="*50)
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Run evaluation on dataset"
    )
    parser.add_argument(
        "--dataset", "-d",
        type=str,
        required=True,
        help="Dataset filename (in eval_data/)"
    )
    parser.add_argument(
        "--name", "-n",
        type=str,
        required=True,
        help="Name for this evaluation run"
    )
    parser.add_argument(
        "--brains", "-b",
        type=str,
        default=None,
        help="Comma-separated list of brains to evaluate (default: all)"
    )
    parser.add_argument(
        "--max-exchanges", "-m",
        type=int,
        default=None,
        help="Maximum exchanges per chat (default: all)"
    )
    parser.add_argument(
        "--no-outputs",
        action="store_true",
        help="Don't save generated outputs"
    )
    
    args = parser.parse_args()
    
    # Parse brains
    brains = None
    if args.brains:
        brains = [b.strip() for b in args.brains.split(",")]
    
    # Load configs
    load_configs()
    
    # Run evaluation
    asyncio.run(run_evaluation(
        dataset_path=args.dataset,
        run_name=args.name,
        brains=brains,
        max_exchanges=args.max_exchanges,
        save_outputs=not args.no_outputs
    ))


if __name__ == "__main__":
    main()

