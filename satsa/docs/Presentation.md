# SAT-SA: Supervisory Analytics Tool for SOC Assessment
**Presentation Deck Content**

---

### Slide 1: The Problem & Our Insight
*   **The Status Quo:** Current supervisory audits rely on self-reported KPIs (like MTTR or closure rates). 
*   **The Insight:** KPIs are easily gamed. They completely miss *Execution Gaps* (doing things poorly to meet quotas) and *Negative Space* (missing coverage).
*   **The Solution:** SAT-SA. A batch, offline analytics tool that targets the raw underlying data to find what the SOC isn't telling you.

---

### Slide 2: Architecture & Workflow
*   **Air-Gapped & Secure:** Entirely offline stack utilizing DuckDB, Polars, and Streamlit. Zero internet access required.
*   **Data Flow:** Multi-entity data is ingested → run through our suite of modular Detectors → scored → and output to a Review Workbench.
*   **Not a SIEM:** We do not collect live telemetry. We analyze post-incident case management logs to assess *capability* rather than *immediate threat*.

---

### Slide 3: Novel Analytics
*   **Negative Space Detection:** We explicitly quantify silence. If a Tier-1 Critical Asset produces zero alerts in 30 days, we flag it as an operational failure.
*   **Review-Sample Optimiser:** We replace random case auditing with a mathematically optimized sample, ensuring examiners spend time only on high-yield, suspicious cases.
*   **Noisy-OR Prioritisation:** We map findings to the 8 PS capability areas and mathematically prevent linear double-counting to produce a fair **Attention Index** per entity.

---

### Slide 4: Validation & Results
*   **Ground Truth Testing:** We built a Synthetic Data Generator that injects deliberate weaknesses into healthy baselines.
*   **100% Recall:** Our detectors (like EG-01 Fast Closure) successfully recovered 100% of injected flaws.
*   **Efficiency Lift:** Our Review-Sample Optimiser yielded an **87% improvement (1.87x lift)** in finding real weaknesses compared to manual random sampling during our simulations.

---

### Slide 5: Deployment, ML Controls & Roadmap
*   **Deployment:** Shipped as a zero-network, self-contained offline bundle with a SHA-256 cryptographic manifest.
*   **ML Controls:** Machine Learning is strictly secondary. We use Isolation Forests to rank anomalies, but *every single finding* must be grounded in explainable statistical rules. No "black-box" flagging.
*   **Tamper-Evident:** Every assessment generates a cryptographic block in an append-only Audit Chain, ensuring findings cannot be deleted by audited entities.

---

### Video Demo Script (2 Minutes)
*   **0:00 - 0:15:** Define the problem: KPIs miss negative space.
*   **0:15 - 0:45:** Open UI. Load the multi-entity synthetic data. Show the Attention Index ranking the worst entities first.
*   **0:45 - 1:15:** Click into the Review Workbench. Show an *Execution Gap* finding (Critical alert closed in 5 seconds). Show a *Negative Space* finding (Critical asset with 0 alerts).
*   **1:15 - 1:35:** Explain the Review-Sample Optimiser output and the 1.87x lift over random sampling.
*   **1:35 - 2:00:** Show the Verify Audit Chain button passing the SHA-256 check. Reiterate the zero-network, air-gapped nature of the tool.
