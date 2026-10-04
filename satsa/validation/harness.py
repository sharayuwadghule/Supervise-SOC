import json
from pathlib import Path
from satsa.detectors.eg_01 import run_eg_01
from satsa.detectors.ns_01 import run_ns_01
from satsa.detectors.eg_03 import run_eg_03
from satsa.detectors.ns_03 import run_ns_03
from satsa.detectors.eg_02 import run_eg_02
from satsa.detectors.eg_04 import run_eg_04
from satsa.detectors.eg_05 import run_eg_05
from satsa.detectors.eg_06 import run_eg_06
from satsa.detectors.ns_02 import run_ns_02
from satsa.detectors.ns_04 import run_ns_04
from satsa.detectors.ns_05 import run_ns_05
from satsa.detectors.ns_06 import run_ns_06
from satsa.ml.ex_01 import run_ex_01
from satsa.ml.ex_02 import run_ex_02
from satsa.ml.ex_03 import run_ex_03
from satsa.ml.ex_04 import run_ex_04
from satsa.ml.ex_05 import run_ex_05
from satsa.ml.ex_06 import run_ex_06
from satsa.ml.ex_07 import run_ex_07
from satsa.ml.ex_08 import run_ex_08

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
    
    # Run EG-03
    eg03_findings = run_eg_03()
    eg03_targets = {f['target_id'] for f in eg03_findings}
    gt_eg03 = gt_map.get("EG-03", set())
    
    eg03_recall = len(eg03_targets.intersection(gt_eg03)) / len(gt_eg03) if gt_eg03 else 1.0
    print(f"[Validation] EG-03 Recall: {eg03_recall*100:.1f}% ({len(eg03_targets.intersection(gt_eg03))}/{len(gt_eg03)})")

    # Run NS-03
    ns03_findings = run_ns_03()
    ns03_targets = {f['target_id'] for f in ns03_findings}
    gt_ns03 = gt_map.get("NS-03", set())
    
    ns03_recall = len(ns03_targets.intersection(gt_ns03)) / len(gt_ns03) if gt_ns03 else 1.0
    print(f"[Validation] NS-03 Recall: {ns03_recall*100:.1f}% ({len(ns03_targets.intersection(gt_ns03))}/{len(gt_ns03)})")

    eg02_findings = run_eg_02()
    gt_eg02 = gt_map.get("EG-02", set())
    eg02_targets = {f['target_id'] for f in eg02_findings}
    eg02_recall = len(eg02_targets.intersection(gt_eg02)) / len(gt_eg02) if gt_eg02 else 1.0
    print(f"[Validation] EG-02 Recall: {eg02_recall*100:.1f}% ({len(eg02_targets.intersection(gt_eg02))}/{len(gt_eg02)})")
    
    eg04_findings = run_eg_04()
    gt_eg04 = gt_map.get("EG-04", set())
    eg04_targets = {f['target_id'] for f in eg04_findings}
    eg04_recall = len(eg04_targets.intersection(gt_eg04)) / len(gt_eg04) if gt_eg04 else 1.0
    print(f"[Validation] EG-04 Recall: {eg04_recall*100:.1f}% ({len(eg04_targets.intersection(gt_eg04))}/{len(gt_eg04)})")
    
    eg05_findings = run_eg_05()
    gt_eg05 = gt_map.get("EG-05", set())
    eg05_targets = {f['target_id'] for f in eg05_findings}
    eg05_recall = len(eg05_targets.intersection(gt_eg05)) / len(gt_eg05) if gt_eg05 else 1.0
    print(f"[Validation] EG-05 Recall: {eg05_recall*100:.1f}% ({len(eg05_targets.intersection(gt_eg05))}/{len(gt_eg05)})")
    
    eg06_findings = run_eg_06()
    gt_eg06 = gt_map.get("EG-06", set())
    eg06_targets = {f['target_id'] for f in eg06_findings}
    eg06_recall = len(eg06_targets.intersection(gt_eg06)) / len(gt_eg06) if gt_eg06 else 1.0
    print(f"[Validation] EG-06 Recall: {eg06_recall*100:.1f}% ({len(eg06_targets.intersection(gt_eg06))}/{len(gt_eg06)})")

    ns02_findings = run_ns_02()
    gt_ns02 = gt_map.get("NS-02", set())
    ns02_targets = {f['target_id'] for f in ns02_findings}
    ns02_recall = len(ns02_targets.intersection(gt_ns02)) / len(gt_ns02) if gt_ns02 else 1.0
    print(f"[Validation] NS-02 Recall: {ns02_recall*100:.1f}% ({len(ns02_targets.intersection(gt_ns02))}/{len(gt_ns02)})")
    
    ns04_findings = run_ns_04()
    gt_ns04 = gt_map.get("NS-04", set())
    ns04_targets = {f['target_id'] for f in ns04_findings}
    ns04_recall = len(ns04_targets.intersection(gt_ns04)) / len(gt_ns04) if gt_ns04 else 1.0
    print(f"[Validation] NS-04 Recall: {ns04_recall*100:.1f}% ({len(ns04_targets.intersection(gt_ns04))}/{len(gt_ns04)})")
    
    ns05_findings = run_ns_05()
    gt_ns05 = gt_map.get("NS-05", set())
    ns05_targets = {f['target_id'] for f in ns05_findings}
    ns05_recall = len(ns05_targets.intersection(gt_ns05)) / len(gt_ns05) if gt_ns05 else 1.0
    print(f"[Validation] NS-05 Recall: {ns05_recall*100:.1f}% ({len(ns05_targets.intersection(gt_ns05))}/{len(gt_ns05)})")
    
    ns06_findings = run_ns_06()
    gt_ns06 = gt_map.get("NS-06", set())
    ns06_targets = {f['target_id'] for f in ns06_findings}
    ns06_recall = len(ns06_targets.intersection(gt_ns06)) / len(gt_ns06) if gt_ns06 else 1.0
    print(f"[Validation] NS-06 Recall: {ns06_recall*100:.1f}% ({len(ns06_targets.intersection(gt_ns06))}/{len(gt_ns06)})")
    
    ex01_findings = run_ex_01()
    gt_ex01 = gt_map.get("EX-01", set())
    ex01_targets = {f['target_id'] for f in ex01_findings}
    ex01_recall = len(ex01_targets.intersection(gt_ex01)) / len(gt_ex01) if gt_ex01 else 1.0
    print(f"[Validation] EX-01 Recall: {ex01_recall*100:.1f}% ({len(ex01_targets.intersection(gt_ex01))}/{len(gt_ex01)})")

    ex02_findings = run_ex_02()
    gt_ex02 = gt_map.get("EX-02", set())
    ex02_targets = {f['target_id'] for f in ex02_findings}
    ex02_recall = len(ex02_targets.intersection(gt_ex02)) / len(gt_ex02) if gt_ex02 else 1.0
    print(f"[Validation] EX-02 Recall: {ex02_recall*100:.1f}% ({len(ex02_targets.intersection(gt_ex02))}/{len(gt_ex02)})")
    
    ex03_findings = run_ex_03()
    gt_ex03 = gt_map.get("EX-03", set())
    ex03_targets = {f['target_id'] for f in ex03_findings}
    ex03_recall = len(ex03_targets.intersection(gt_ex03)) / len(gt_ex03) if gt_ex03 else 1.0
    print(f"[Validation] EX-03 Recall: {ex03_recall*100:.1f}% ({len(ex03_targets.intersection(gt_ex03))}/{len(gt_ex03)})")

    ex04_findings = run_ex_04()
    gt_ex04 = gt_map.get("EX-04", set())
    ex04_targets = {f['target_id'] for f in ex04_findings}
    ex04_recall = len(ex04_targets.intersection(gt_ex04)) / len(gt_ex04) if gt_ex04 else 1.0
    print(f"[Validation] EX-04 Recall: {ex04_recall*100:.1f}% ({len(ex04_targets.intersection(gt_ex04))}/{len(gt_ex04)})")

    ex05_findings = run_ex_05()
    gt_ex05 = gt_map.get("EX-05", set())
    ex05_targets = {f['target_id'] for f in ex05_findings}
    ex05_recall = len(ex05_targets.intersection(gt_ex05)) / len(gt_ex05) if gt_ex05 else 1.0
    print(f"[Validation] EX-05 Recall: {ex05_recall*100:.1f}% ({len(ex05_targets.intersection(gt_ex05))}/{len(gt_ex05)})")

    ex06_findings = run_ex_06()
    gt_ex06 = gt_map.get("EX-06", set())
    ex06_targets = {f['target_id'] for f in ex06_findings}
    ex06_recall = len(ex06_targets.intersection(gt_ex06)) / len(gt_ex06) if gt_ex06 else 1.0
    print(f"[Validation] EX-06 Recall: {ex06_recall*100:.1f}% ({len(ex06_targets.intersection(gt_ex06))}/{len(gt_ex06)})")

    ex07_findings = run_ex_07()
    gt_ex07 = gt_map.get("EX-07", set())
    ex07_targets = {f['target_id'] for f in ex07_findings}
    ex07_recall = len(ex07_targets.intersection(gt_ex07)) / len(gt_ex07) if gt_ex07 else 1.0
    print(f"[Validation] EX-07 Recall: {ex07_recall*100:.1f}% ({len(ex07_targets.intersection(gt_ex07))}/{len(gt_ex07)})")
    
    ex08_findings = run_ex_08()
    gt_ex08 = gt_map.get("EX-08", set())
    ex08_targets = {f['target_id'] for f in ex08_findings}
    ex08_recall = len(ex08_targets.intersection(gt_ex08)) / len(gt_ex08) if gt_ex08 else 1.0
    print(f"[Validation] EX-08 Recall: {ex08_recall*100:.1f}% ({len(ex08_targets.intersection(gt_ex08))}/{len(gt_ex08)})")

    print("\n--- Entity Prioritisation (Attention Index) ---")
    from satsa.scoring.prioritiser import aggregate_capability_scores, calculate_attention_index
    from satsa.scoring.optimiser import calculate_lift_over_random, optimize_review_sample
    
    all_findings = (eg01_findings + ns01_findings + eg03_findings + ns03_findings + 
                    eg02_findings + eg04_findings + eg05_findings + eg06_findings + 
                    ns02_findings + ns04_findings + ns05_findings + ns06_findings + 
                    ex01_findings + ex02_findings + ex03_findings + ex04_findings +
                    ex05_findings + ex06_findings + ex07_findings + ex08_findings)
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
