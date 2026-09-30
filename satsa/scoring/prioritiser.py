from typing import List, Dict, Any
from satsa.config.settings import get_config
import math

# ---------------------------------------------------------
# SAT-SA Scoring & Prioritisation (Phase 5)
# ---------------------------------------------------------

def calculate_finding_score(finding: Dict[str, Any]) -> float:
    """
    Finding score = severity weight * normalized effect size * confidence
    (simplified for this stub).
    """
    # Base severity from the finding itself (1-5), defaulted to 3
    sev = finding.get("severity", 3)
    
    # Simple normalization mapping severity (1-5) to (0.2-1.0)
    sev_weight = sev / 5.0
    
    # In a full implementation, effect size and confidence would be calculated by the detector
    effect_size = finding.get("effect_size", 0.8) 
    confidence = finding.get("confidence", 0.9)
    
    return sev_weight * effect_size * confidence

def aggregate_capability_scores(findings: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    """
    Aggregates finding scores into entity-level Capability Scores using noisy-OR.
    Returns: { entity_id: { capability_name: score } }
    """
    config = get_config()
    mappings = config["detector_mappings"]
    
    # entity_id -> capability -> list of scores
    raw_scores = {}
    
    for finding in findings:
        e_id = finding["entity_id"]
        d_id = finding["detector_id"]
        
        score = calculate_finding_score(finding)
        
        if e_id not in raw_scores:
            raw_scores[e_id] = {cap: [] for cap in config["capability_areas"]}
            
        caps = mappings.get(d_id, ["Security Operations"]) # default
        for cap in caps:
            raw_scores[e_id][cap].append(score)
            
    # Apply noisy-OR: 1 - product(1 - s_i)
    # This prevents linear double counting if an entity has 50 findings in one capability
    entity_capability_scores = {}
    for e_id, cap_dict in raw_scores.items():
        entity_capability_scores[e_id] = {}
        for cap, scores in cap_dict.items():
            if not scores:
                entity_capability_scores[e_id][cap] = 0.0
                continue
            
            product_term = 1.0
            for s in scores:
                # clamp score to avoid negative or >1 issues
                clamped_s = max(0.0, min(s, 0.99))
                product_term *= (1.0 - clamped_s)
            
            entity_capability_scores[e_id][cap] = 1.0 - product_term
            
    return entity_capability_scores

def calculate_attention_index(capability_scores: Dict[str, Dict[str, float]]) -> List[Dict[str, Any]]:
    """
    Calculates the final Attention Index per entity.
    Returns a sorted list of entities by priority.
    """
    config = get_config()
    weights = config["capability_weights"]
    
    results = []
    
    for e_id, caps in capability_scores.items():
        total_weight = sum(weights.values())
        weighted_sum = sum(caps[cap] * weights[cap] for cap in caps)
        
        attention_index = (weighted_sum / total_weight) if total_weight > 0 else 0
        
        results.append({
            "entity_id": e_id,
            "attention_index": round(attention_index, 4),
            "capability_scores": caps
        })
        
    # Sort descending (highest attention index first)
    results.sort(key=lambda x: x["attention_index"], reverse=True)
    return results

if __name__ == "__main__":
    # Test stub
    dummy_findings = [
        {"detector_id": "EG-01", "entity_id": "ENT-123", "severity": 5, "effect_size": 1.0, "confidence": 1.0},
        {"detector_id": "NS-01", "entity_id": "ENT-123", "severity": 4, "effect_size": 0.8, "confidence": 0.9},
        {"detector_id": "EG-01", "entity_id": "ENT-456", "severity": 3, "effect_size": 0.5, "confidence": 0.8}
    ]
    
    cap_scores = aggregate_capability_scores(dummy_findings)
    ranking = calculate_attention_index(cap_scores)
    
    print("--- Entity Ranking (Attention Index) ---")
    for rank, entity in enumerate(ranking, 1):
        print(f"{rank}. {entity['entity_id']} - Index: {entity['attention_index']}")
