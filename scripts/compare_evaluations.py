"""
Compare evaluation runs and generate a report.

Usage:
    python scripts/compare_evaluations.py --runs baseline_v1 improved_v2
    python scripts/compare_evaluations.py --runs baseline improved --output report.md
"""
import sys
import os
import json
import argparse
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_evaluation_results(run_name: str) -> dict:
    """Load evaluation results from file"""
    results_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "eval_data",
        "results",
        f"{run_name}.json"
    )
    
    if not os.path.exists(results_path):
        print(f"❌ Results not found: {results_path}")
        return None
    
    with open(results_path, "r", encoding="utf-8") as f:
        return json.load(f)


def compare_evaluations(run_names: list[str], output_file: str = None) -> str:
    """
    Compare multiple evaluation runs and generate a markdown report.
    
    Args:
        run_names: List of evaluation run names to compare
        output_file: Optional output file path for the report
    
    Returns:
        Markdown report string
    """
    # Load all results
    results = {}
    for name in run_names:
        data = load_evaluation_results(name)
        if data:
            results[name] = data
        else:
            print(f"⚠️  Skipping {name} - not found")
    
    if len(results) < 2:
        print("❌ Need at least 2 valid runs to compare")
        return None
    
    # Generate report
    report = []
    report.append("# Evaluation Comparison Report")
    report.append(f"\nGenerated: {datetime.utcnow().isoformat()}")
    report.append(f"\nRuns compared: {', '.join(results.keys())}")
    
    # Summary table
    report.append("\n## Summary Scores\n")
    
    # Get all brains across all runs
    all_brains = set()
    for data in results.values():
        all_brains.update(data["summary"].keys())
    
    # Table header
    header = "| Brain |"
    divider = "|-------|"
    for name in results.keys():
        header += f" {name} |"
        divider += "--------|"
    header += " Change |"
    divider += "--------|"
    
    report.append(header)
    report.append(divider)
    
    # Table rows
    first_run = list(results.keys())[0]
    last_run = list(results.keys())[-1]
    
    for brain in sorted(all_brains):
        row = f"| {brain.upper()} |"
        scores = []
        
        for name in results.keys():
            summary = results[name]["summary"].get(brain, {})
            avg = summary.get("avg_score", 0)
            count = summary.get("count", 0)
            scores.append(avg)
            row += f" {avg:.2f} ({count}) |"
        
        # Calculate change from first to last
        if len(scores) >= 2:
            change = scores[-1] - scores[0]
            if change > 0:
                row += f" +{change:.2f} 🟢 |"
            elif change < 0:
                row += f" {change:.2f} 🔴 |"
            else:
                row += " 0.00 ⚪ |"
        else:
            row += " - |"
        
        report.append(row)
    
    # Per-brain analysis
    report.append("\n## Detailed Analysis\n")
    
    for brain in sorted(all_brains):
        report.append(f"### {brain.title()}\n")
        
        for name, data in results.items():
            summary = data["summary"].get(brain, {})
            avg = summary.get("avg_score", 0)
            count = summary.get("count", 0)
            
            # Get criteria breakdown if available
            criteria_summary = {}
            for eval_item in data.get("evaluations", []):
                brain_eval = eval_item.get("evaluations", {}).get(brain, {})
                criteria_scores = brain_eval.get("criteria_scores", {})
                for criterion, details in criteria_scores.items():
                    if criterion not in criteria_summary:
                        criteria_summary[criterion] = []
                    score = details.get("score", 0) if isinstance(details, dict) else details
                    criteria_summary[criterion].append(score)
            
            report.append(f"**{name}**: {avg:.2f}/10 (n={count})")
            
            if criteria_summary:
                report.append("\nCriteria breakdown:")
                for criterion, scores in sorted(criteria_summary.items()):
                    avg_criterion = sum(scores) / len(scores) if scores else 0
                    report.append(f"  - {criterion}: {avg_criterion:.2f}")
            
            report.append("")
    
    # Examples of improvements/regressions
    if len(results) >= 2:
        report.append("\n## Notable Changes\n")
        
        first_data = results[first_run]
        last_data = results[last_run]
        
        report.append(f"Comparing {first_run} → {last_run}:\n")
        
        # Find biggest improvements and regressions
        changes = []
        
        for i, (first_eval, last_eval) in enumerate(zip(
            first_data.get("evaluations", []),
            last_data.get("evaluations", [])
        )):
            for brain in all_brains:
                first_score = first_eval.get("evaluations", {}).get(brain, {}).get("score", 0)
                last_score = last_eval.get("evaluations", {}).get(brain, {}).get("score", 0)
                change = last_score - first_score
                
                if abs(change) >= 2:  # Significant change
                    changes.append({
                        "index": i,
                        "brain": brain,
                        "change": change,
                        "first_score": first_score,
                        "last_score": last_score,
                        "user_message": first_eval.get("user_message", "")[:50],
                    })
        
        # Sort by absolute change
        changes.sort(key=lambda x: abs(x["change"]), reverse=True)
        
        # Top improvements
        improvements = [c for c in changes if c["change"] > 0][:3]
        if improvements:
            report.append("### Top Improvements\n")
            for c in improvements:
                report.append(f"- **{c['brain']}** +{c['change']:.1f} (exchange #{c['index']})")
                report.append(f"  - {c['first_score']:.1f} → {c['last_score']:.1f}")
                report.append(f"  - Message: \"{c['user_message']}...\"")
                report.append("")
        
        # Top regressions
        regressions = [c for c in changes if c["change"] < 0][:3]
        if regressions:
            report.append("### Top Regressions\n")
            for c in regressions:
                report.append(f"- **{c['brain']}** {c['change']:.1f} (exchange #{c['index']})")
                report.append(f"  - {c['first_score']:.1f} → {c['last_score']:.1f}")
                report.append(f"  - Message: \"{c['user_message']}...\"")
                report.append("")
    
    # Join report
    report_text = "\n".join(report)
    
    # Save to file if specified
    if output_file:
        output_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "eval_data",
            "reports",
            output_file
        )
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report_text)
        
        print(f"📁 Report saved to: {output_path}")
    
    return report_text


def main():
    parser = argparse.ArgumentParser(
        description="Compare evaluation runs"
    )
    parser.add_argument(
        "--runs", "-r",
        type=str,
        nargs="+",
        required=True,
        help="Names of evaluation runs to compare"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Output filename for report (in eval_data/reports/)"
    )
    
    args = parser.parse_args()
    
    report = compare_evaluations(args.runs, args.output)
    
    if report:
        print("\n" + "="*50)
        print(report)
        print("="*50)


if __name__ == "__main__":
    main()

