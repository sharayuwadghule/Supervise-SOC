# SAT-SA Architecture & Design Document

## 1. Executive Summary
SAT-SA operates as a strict, offline batch processing platform. It is explicitly **not a SIEM**; it does not collect real-time telemetry. Instead, it ingests periodic SOC alert and case management data from CSEs to run statistical, rules-based detectors that surface systemic failures. 

## 2. Data Flow & Components
1. **Ingestion & Data Quality:** CSV/JSON/Parquet files are ingested, validated, and normalized into a standard schema (Entities, Assets, Alerts, Cases) using **Polars** and **DuckDB**. A Data Quality report flags missing fields as negative space findings.
2. **Detector Library:** A suite of modular Python scripts query DuckDB to flag anomalies:
    *   **Execution Gaps (EG):** E.g., high-severity alerts closed in < 60 seconds without escalation.
    *   **Negative Space (NS):** E.g., assets flagged as "Critical" producing zero alerts over a 30-day window.
3. **Prioritisation Engine:** Findings are mapped to 8 PS Capability Areas. A "noisy-OR" mathematical function prevents linear double-counting, yielding a balanced **Attention Index** per entity.
4. **Explainability & UI:** Findings are formatted into deterministic "Finding Cards" in a **Streamlit** dashboard, explaining precisely *why* an entity was flagged using plain text and statistical context.

## 3. Air-Gap & Infrastructure Model
*   **Hardware:** Runs on a single offline server (minimum 16GB RAM, standard CPUs). GPU is not required.
*   **Zero-Network Guarantee:** The deployment bundle packages the Python runtime and all wheels natively. A checksum manifest (`manifest.sha256`) is generated at build-time to prove no internet-dependent modules were injected.
*   **Audit Chain:** Every run of the platform generates a block in an append-only, SHA-256 chained ledger, proving that findings have not been retroactively deleted by audited entities.

## 4. Machine Learning Specification (PS 26157 Compliance)
| Item | Specification |
|---|---|
| **Architecture** | Rules and Statistics first. Isolation Forest (LOF) used only as a secondary signal for anomaly clustering. No LLMs or generative models. |
| **Hardware** | CPU only; designed for state-level standard servers. |
| **Offline Inference** | ML runs entirely batch-mode on the local server. Zero API calls. |
| **Update Mechanism** | Signed model bundle via removable media with checksum verification. |
| **Explainability** | Per-feature attribution required on every ML flag; an ML score cannot trigger a finding on its own. |
| **Auditability** | Model parameters and seeds are hashed into the Run Manifest. |
