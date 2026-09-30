import random
import pandas as pd
from typing import List, Dict, Any

# ---------------------------------------------------------
# SAT-SA Review-Sample Optimiser (Phase 5)
# ---------------------------------------------------------

def optimize_review_sample(findings: List[Dict[str, Any]], ranking: List[Dict[str, Any]], budget_k: int = 10) -> List[Dict[str, Any]]:
    """
    Selects an optimal sample of findings (cases/alerts) for manual review.
    Instead of randomly sampling, it stratifies based on the entity's Attention Index
    and finding severity.
    Reserves ~20% for random exploration.
    """
    if not findings:
        return []
        
    df_findings = pd.DataFrame(findings)
    df_ranking = pd.DataFrame(ranking)
    
    # 20% Random Exploration (Unknown Unknowns)
    n_explore = max(1, int(budget_k * 0.2))
    n_targeted = max(0, budget_k - n_explore)
    
    sample = []
    
    # 1. Targeted Sampling based on Attention Index
    if n_targeted > 0 and not df_ranking.empty:
        # Give higher probability to entities with higher Attention Index
        weights = df_ranking['attention_index'] / df_ranking['attention_index'].sum()
        
        # Sample entities (with replacement to allow multiple findings per bad entity)
        chosen_entities = df_ranking.sample(n=n_targeted, weights=weights, replace=True)['entity_id'].tolist()
        
        for e_id in chosen_entities:
            # Get findings for this entity, sort by severity
            entity_findings = df_findings[df_findings['entity_id'] == e_id].sort_values(by='severity', ascending=False)
            
            # Avoid picking the exact same finding twice if possible
            available = entity_findings[~entity_findings['target_id'].isin([s['target_id'] for s in sample])]
            
            if not available.empty:
                chosen = available.iloc[0].to_dict()
                chosen['selection_reason'] = "Targeted (High Attention Index & Severity)"
                sample.append(chosen)

    # 2. Random Exploration
    available_for_explore = df_findings[~df_findings['target_id'].isin([s['target_id'] for s in sample])]
    if not available_for_explore.empty:
        n_actual_explore = min(n_explore, len(available_for_explore))
        explore_sample = available_for_explore.sample(n=n_actual_explore).to_dict('records')
        for ex in explore_sample:
            ex['selection_reason'] = "Exploration (Random Baseline)"
            sample.append(ex)
            
    return sample

def calculate_lift_over_random(findings: List[Dict[str, Any]], ranking: List[Dict[str, Any]], ground_truth_targets: set, budget_k: int = 10, iterations: int = 50) -> Dict[str, float]:
    """
    Simulates examiners reviewing random samples vs optimized samples.
    Reports the expected "lift" (improvement in finding actual injected weaknesses).
    """
    if not findings or not ground_truth_targets:
        return {"random_yield": 0.0, "optimized_yield": 0.0, "lift_multiplier": 1.0}
        
    df_findings = pd.DataFrame(findings)
    total_findings = len(df_findings)
    
    if total_findings < budget_k:
        budget_k = total_findings
        
    # Simulate Random Baseline
    random_hits = []
    for _ in range(iterations):
        rand_sample = df_findings.sample(n=budget_k)['target_id'].tolist()
        hits = len(set(rand_sample).intersection(ground_truth_targets))
        random_hits.append(hits)
        
    avg_random_yield = sum(random_hits) / iterations
    
    # Simulate Optimized Baseline
    opt_hits = []
    for _ in range(iterations):
        opt_sample = optimize_review_sample(findings, ranking, budget_k=budget_k)
        opt_targets = [s['target_id'] for s in opt_sample]
        hits = len(set(opt_targets).intersection(ground_truth_targets))
        opt_hits.append(hits)
        
    avg_opt_yield = sum(opt_hits) / iterations
    
    lift = avg_opt_yield / avg_random_yield if avg_random_yield > 0 else 0.0
    
    return {
        "random_yield": round(avg_random_yield, 2),
        "optimized_yield": round(avg_opt_yield, 2),
        "lift_multiplier": round(lift, 2)
    }
