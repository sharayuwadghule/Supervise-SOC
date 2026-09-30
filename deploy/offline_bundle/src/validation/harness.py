import json
from pathlib import Path
from satsa.detectors.eg_01 import run_eg_01
from satsa.detectors.ns_01 import run_ns_01

# ---------------------------------------------------------
# SAT-SA Validation Harness (Phase 8)
# ---------------------------------------------------------

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "synthetic"
GT_FILE = DATA_DIR / "ground_truth.json"

def evaluate_detectors():
    """
    Runs detectors and cross-references their findings with ground truth.
    Calculates simple recall.
    """
    if not GT_FILE.exists():
        print("Ground truth file not found. Run generator first.")
        return

    with open(GT_FILE, 'r') as f:
        ground_truth = json.load(f)

    # Group ground truth by finding ID
    gt_map = {}
    for gt in ground_truth:
        fid = gt['finding_id']
        tid = gt['target_id']
        if fid not in gt_map:
            gt_map[fid] = set()
        gt_map[fid].add(tid)
        
    print("\n--- Validation Harness ---")
    print(f"Total ground truth injected weaknesses: {len(ground_truth)}")
    
    # Run EG-01
    eg01_findings = run_eg_01()
    eg01_targets = {f['target_id'] for f in eg01_findings}
    gt_eg01 = gt_map.get("EG-01", set())
    
    eg01_recall = len(eg01_targets.intersection(gt_eg01)) / len(gt_eg01) if gt_eg01 else 1.0
    print(f"[Validation] EG-01 Recall: {eg01_recall*100:.1f}% ({len(eg01_targets.intersection(gt_eg01))}/{len(gt_eg01)})")

    # Run NS-01
    ns01_findings = run_ns_01()
    ns01_targets = {f['target_id'] for f in ns01_findings}
    gt_ns01 = gt_map.get("NS-01", set())
    
    ns01_recall = len(ns01_targets.intersection(gt_ns01)) / len(gt_ns01) if gt_ns01 else 1.0
    print(f"[Validation] NS-01 Recall: {ns01_recall*100:.1f}% ({len(ns01_targets.intersection(gt_ns01))}/{len(gt_ns01)})")
    
    print("\n--- Entity Prioritisation (Attention Index) ---")
    from satsa.scoring.prioritiser import aggregate_capability_scores, calculate_attention_index
    from satsa.scoring.optimiser import calculate_lift_over_random, optimize_review_sample
    
    all_findings = eg01_findings + ns01_findings
    if all_findings:
        cap_scores = aggregate_capability_scores(all_findings)
        ranking = calculate_attention_index(cap_scores)
        
        for rank, entity in enumerate(ranking[:5], 1):  # Show top 5
            print(f"{rank}. {entity['entity_id']} - Index: {entity['attention_index']}")
            
        print("\n--- Review-Sample Optimiser (Simulation) ---")
        # All ground truth targets we want to catch
        all_gt_targets = set()
        for s in gt_map.values():
            all_gt_targets.update(s)
            
        # Simulate an examiner with time to look at only 5 cases
        budget = 5
        lift_metrics = calculate_lift_over_random(all_findings, ranking, all_gt_targets, budget_k=budget)
        
        print(f"Examiner Budget: {budget} cases/alerts")
        print(f"Expected True Weaknesses found (Random): {lift_metrics['random_yield']}")
        print(f"Expected True Weaknesses found (Optimised): {lift_metrics['optimized_yield']}")
        print(f"Lift (Efficiency Gain): {lift_metrics['lift_multiplier']}x")
        
        print("\nExample Optimised Sample (Top 3):")
        sample = optimize_review_sample(all_findings, ranking, budget_k=budget)
        for i, s in enumerate(sample[:3], 1):
            print(f"  {i}. {s['target_id']} (Entity: {s['entity_id']}) - Reason: {s['selection_reason']}")
            
    else:
        print("No findings generated to score.")
        
    print("--------------------------")

if __name__ == "__main__":
    # Ensure data is loaded (this requires the loader to be run beforehand or we can run it here,
    # but for modularity we assume DuckDB views are established).
    # You should run loader.py before this script.
    evaluate_detectors()
