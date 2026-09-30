import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# ---------------------------------------------------------
# SAT-SA Audit Chain (Phase 6)
# ---------------------------------------------------------

AUDIT_FILE = Path(__file__).parent.parent.parent / "data" / "audit_chain.jsonl"

def _hash_data(data: str) -> str:
    return hashlib.sha256(data.encode('utf-8')).hexdigest()

def init_chain():
    """Initializes the audit chain if it doesn't exist."""
    if not AUDIT_FILE.parent.exists():
        AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not AUDIT_FILE.exists():
        genesis_event = {
            "index": 0,
            "timestamp": datetime.now().isoformat(),
            "event_type": "CHAIN_INIT",
            "data": "Genesis Block",
            "prev_hash": "0" * 64
        }
        # Self-hash includes everything except the hash itself
        genesis_event["hash"] = _hash_data(json.dumps(genesis_event, sort_keys=True))
        
        with open(AUDIT_FILE, 'w') as f:
            f.write(json.dumps(genesis_event) + "\n")

def get_last_block() -> Dict[str, Any]:
    init_chain()
    last_line = ""
    with open(AUDIT_FILE, 'r') as f:
        for line in f:
            if line.strip():
                last_line = line
    return json.loads(last_line)

def log_event(event_type: str, data: Any):
    """
    Appends a new event to the tamper-evident audit chain.
    """
    last_block = get_last_block()
    
    new_event = {
        "index": last_block["index"] + 1,
        "timestamp": datetime.now().isoformat(),
        "event_type": event_type,
        "data": data,
        "prev_hash": last_block["hash"]
    }
    
    new_event["hash"] = _hash_data(json.dumps(new_event, sort_keys=True))
    
    with open(AUDIT_FILE, 'a') as f:
        f.write(json.dumps(new_event) + "\n")
        
    return new_event["hash"]

def verify_chain() -> bool:
    """
    Reads the entire chain and verifies that no entries have been tampered with.
    """
    if not AUDIT_FILE.exists():
        print("No audit chain exists.")
        return True
        
    with open(AUDIT_FILE, 'r') as f:
        prev_hash = "0" * 64
        for line in f:
            if not line.strip():
                continue
            block = json.loads(line)
            
            # Check linkage
            if block["prev_hash"] != prev_hash:
                print(f"CHAIN BROKEN at block {block['index']}: prev_hash mismatch.")
                return False
                
            # Check internal consistency
            reported_hash = block.pop("hash")
            calculated_hash = _hash_data(json.dumps(block, sort_keys=True))
            if reported_hash != calculated_hash:
                print(f"CHAIN BROKEN at block {block['index']}: block contents modified.")
                return False
                
            # Restore for next iteration
            prev_hash = reported_hash
            
    print("Audit chain verified successfully. No tampering detected.")
    return True

if __name__ == "__main__":
    init_chain()
    log_event("TEST_EVENT", {"message": "Testing the audit chain"})
    verify_chain()
