import yaml
from pathlib import Path

# ---------------------------------------------------------
# SAT-SA Configuration & Weights (Phase 1 / Phase 5)
# ---------------------------------------------------------

# Define the 8 PS Capability Areas
CAPABILITY_AREAS = [
    "Threat Detection",
    "Investigation",
    "Escalation",
    "Incident Response",
    "Security Operations",
    "Governance and Oversight",
    "Operational Discipline",
    "Cyber Resilience"
]

# Mapping of Detectors to Capability Areas
DETECTOR_CAPABILITY_MAP = {
    "EG-01": ["Investigation", "Operational Discipline"],  # Fast closure
    "NS-01": ["Threat Detection", "Security Operations"],  # Silent critical assets
}

# Base weights for Attention Index calculation
CAPABILITY_WEIGHTS = {
    "Threat Detection": 1.5,
    "Investigation": 1.2,
    "Escalation": 1.0,
    "Incident Response": 1.5,
    "Security Operations": 1.0,
    "Governance and Oversight": 0.8,
    "Operational Discipline": 1.0,
    "Cyber Resilience": 1.2
}

def get_config():
    """
    Returns the loaded configuration.
    In the final product, this would read from versioned YAML files.
    """
    return {
        "capability_areas": CAPABILITY_AREAS,
        "detector_mappings": DETECTOR_CAPABILITY_MAP,
        "capability_weights": CAPABILITY_WEIGHTS
    }
