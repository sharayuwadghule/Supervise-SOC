# SAT-SA: Final Implementation Plan
**PS 26157 | Supervisory Analytics Tool for SOC Assessment | NTRO / NCIIPC**

Assumptions: team of 3-4, about 4 weeks, Python, single offline server. A cut-list for shorter timelines is in Section 14.

---

## 1. Solution in one paragraph

SAT-SA is an offline, batch supervisory analytics platform. It ingests periodic SOC alert and case-management submissions from many Critical Sector Entities (CSEs), runs a library of transparent detectors for **execution gaps** and **negative space**, benchmarks entities against peers, and produces an **explainable, audited, prioritised review queue** (entities, processes, cases, samples). Every finding traces to evidence rows and to a tamper-evident audit chain. It is validated against a simulated manual-sampling baseline with planted ground truth. It is not a SIEM, not real-time, and does not collect logs.

## 2. Non-negotiable design principles

1. **Rules and statistics are the backbone; ML is a secondary, explained signal.** No flag exists on an ML score alone.
2. **Every finding is a record:** detector ID and version, entity, scope, effect size, confidence, sample size, peer context, evidence query, rationale template, config hash.
3. **Graceful degradation:** if an optional field is missing (for example analyst_id), dependent detectors are skipped and the report says so.
4. **"Insufficient evidence" is a valid output.** Minimum-sample rules prevent noisy flags.
5. **Batch, supervisory, air-gapped.** Zero outbound network calls (tested).
6. **Validation is built in from day one** via a synthetic generator with ground truth.

## 3. Technology stack (all offline)

| Layer | Choice |
|---|---|
| Storage/query | DuckDB + Parquet (partitioned by entity, month) |
| Processing | Polars/pandas, NumPy, SciPy, scikit-learn, statsmodels |
| Text similarity | TF-IDF + MinHash/LSH (default); optional small local sentence-embedding model shipped as a file |
| Service layer | FastAPI |
| UI | Streamlit (fastest) or React; Plotly charts |
| Reports | Jinja2 + WeasyPrint (PDF/HTML) |
| Audit | SHA-256 hash chain + SQLite audit log; local Ed25519 report signing |
| Auth | Local users, roles (viewer / examiner / admin) |
| Packaging | Docker image tarball or venv + wheelhouse; checksum manifest |

## 4. Repository layout

```
satsa/
  ingest/        connectors, mapping profiles (YAML), data-quality checks
  store/         DuckDB schema, views, materialised aggregates
  detectors/     eg_*.py, ns_*.py, peers.py, ml_signals.py, depth_score.py, gaming_index.py
  scoring/       finding scoring, capability aggregation, attention index, prioritiser, sample optimiser
  explain/       rationale templates, finding cards, score waterfall
  audit/         hash chain, run manifest, signing, verify CLI
  api/           FastAPI routes
  ui/            dashboards, workbench, report generator
  synthetic/     generator, injectors, decoys, exporters
  validation/    ground-truth recovery, sampling simulation, ablations, robustness, benchmark
  config/        detector configs (versioned), weights, allowlist/context registry
  docs/          functional design, methodology, data requirements, validation, deployment
  tests/
  deploy/        offline bundle scripts, smoke test, no-network assertion
```

## 5. Canonical data model

| Table | Key fields | Required? |
|---|---|---|
| entities | entity_id, sector, size_tier, region, soc_model (in-house/MSSP) | Yes |
| assets | asset_id, entity_id, type, criticality, environment/zone, monitored_flag, onboarded_date, decommissioned_date | Optional (enables NS-01/06) |
| alerts | alert_id, entity_id, asset_id, rule_id, category, severity, created_ts, ack_ts, closed_ts, status, disposition, closure_reason, analyst_id, shift | Yes (analyst/shift optional) |
| cases | case_id, alert_ids, opened_ts, closed_ts, severity, owner, root_cause, remediation, reopened_flag | Yes |
| case_events | case_id, ts, event_type (assign, enrich, pivot, note, evidence, handoff, status), actor | Recommended |
| escalations | case_id/alert_id, ts, from_tier, to_tier, recipient, outcome | Yes |
| notes | case_id, ts, text | Recommended |
| kpi_reports | entity_id, period, reported MTTR/MTTA/SLA%/closure rate | Optional (enables Gaming Index) |
| submission_manifest | entity_id, period, file hashes, row counts, received_ts | Yes |

Mapping profiles (YAML) convert source field names, timestamp formats, timezones and severity scales into this model. Ship templates for generic CSV/JSON plus Splunk-, QRadar-, Sentinel- and TheHive-style exports.

## 6. Phased implementation

### Phase 1: Foundations (Days 1-3)
- Freeze schema (Section 5) and field-requirement matrix (which detector needs which field).
- Repo skeleton, config system with versioning, logging, test harness.
- **Exit:** empty pipeline runs end to end.

### Phase 2: Synthetic data generator with ground truth (Days 2-6, parallel)
- 20-25 entities across power, banking, telecom, transport, health; varied size, SOC model and asset mix.
- Healthy baseline: seasonal volumes (Poisson/negative binomial with diurnal and weekly effects), severity mix, sector-specific category mix, lognormal closure times by severity, plausible escalation rates, varied note text (template banks plus paraphrase).
- **Weakness injectors** (each writes a ground-truth record: entity, scope, type, magnitude):
  fast high-severity closure; critical closed without escalation; ack-then-close with no workflow events; templated notes; repeat alerts with no root cause; month-end or shift-end closure bursts; silent critical assets; missing alert categories; unexpected activity drop; escalation deficit; timestamp anomalies (rounding, closed-before-ack, backdating); KPI gaming (MTTR improves while depth falls).
- **Decoys** (benign look-alikes): known-noisy rules auto-closed legitimately, maintenance-window silence, small entities with naturally low volume, newly onboarded assets.
- Exporters: CSV, JSON/NDJSON, Parquet, SQLite dump, vendor-flavoured field names.
- Scale modes: 1M, 10M, 50M rows; seeded and reproducible.
- **Exit:** one command produces a dataset plus `ground_truth.json`.

### Phase 3: Ingestion and data quality (Days 4-7)
- Connectors: CSV, JSON/NDJSON, Parquet, DB dumps, optional configurable REST pull (disabled by default in air-gapped mode).
- Mapping wizard with preview.
- Data-quality report per submission: completeness, duplicate IDs, timestamp sanity, orphan references, optional-field coverage.
- **Data-quality problems are logged as supervisory findings** (a missing escalation file is itself negative space), not just rejections.
- Idempotent, versioned loads; every input file hashed into the manifest and audit chain.
- Chunked loading to partitioned Parquet with DuckDB views.
- **Exit:** 10M rows load in minutes; DQ report renders.

### Phase 4: Detector library (Days 6-14)
Each detector: `id`, `capability_tags`, `required_fields`, `run(entity, period)`, `evidence_query`, config (thresholds, windows, min-n). Output is a Finding record.

**Execution-gap detectors**

| ID | Signal | Method |
|---|---|---|
| EG-01 | Unusually fast closure | Closure-time distribution per (severity, category) vs own history and peers; lower-tail robust z-score and quantile test; report share of high-severity alerts under threshold |
| EG-02 | Critical closed without escalation | Escalation rate by severity vs peers; binomial/Fisher test on the difference |
| EG-03 | Ack-only / no-work closure | Closed alerts or cases with ≤ N case events, no notes, no enrichment |
| EG-04 | Templated investigations | MinHash/LSH near-duplicate clusters of closure notes; Template Concentration Index = share of notes in clusters larger than k; per analyst and entity |
| EG-05 | Repeat alerts, no root-cause remediation | Same asset + rule recurring inside window W with no root cause or remediation recorded and recurrence not decaying |
| EG-06 | Closure bursts | Closure time-series; spike ratio vs rolling median at period-end and shift-end; permutation test |
| EG-07 | Disposition bias | Benign/false-positive share per rule vs peers, cross-checked with reopen rate |
| EG-08 | Temporal integrity | Rounded timestamps, closed-before-ack, uniform durations, edit-after-close patterns; Benford-style and digit-preference tests on minutes/seconds |
| EG-09 | SLA gaming | Closure clustering just before SLA deadlines; reopen-after-close patterns |
| EG-10 | Analyst/shift concentration | Analysts or shifts with abnormal speed, zero escalations, or night-shift deviation (only if fields exist) |
| EG-11 | Workload plausibility | Alerts per analyst per shift vs physically feasible investigation time |

**Negative-space detectors**

| ID | Signal | Method |
|---|---|---|
| NS-01 | Silent critical assets | Inventory left-join to alerts; critical assets with zero or very low alert rate over the period, adjusted for asset type |
| NS-02 | Missing expected alert categories | Expected-evidence model: per (sector, asset type) category presence across peers; flag categories present at ≥ X% of peers but absent here |
| NS-03 | Unexpected silence or drop | Seasonal baseline per entity/asset; lower-tail Poisson/NB test on windows and gaps |
| NS-04 | Escalation deficit | Expected escalations = Σ over severity of (alert count × peer conversion rate); compare with actual |
| NS-05 | Investigation deficit | High-severity alerts with no case record vs peer expectation |
| NS-06 | Coverage by tier | Monitored share by criticality tier, zone and asset type |
| NS-07 | Referential and period gaps | Alerts referencing missing cases or escalations; missing submission periods |
| NS-08 | Low-activity plausibility | Volume per asset vs comparable environments |

Every NS finding carries an **absence confidence** and an **innocent-explanations checklist** (decommissioned asset, maintenance window, late onboarding, MSSP boundary) for the supervisor.

**Cross-entity layer**
- Peer groups by clustering on sector, size, asset profile and alert mix; groups are visible and editable.
- Benchmarking: robust z-scores, percentile ranks, Mahalanobis distance on a metric vector.
- **ML signal (secondary):** Isolation Forest / LOF over case-level features to rank within an entity and to populate an "unexplained anomalies" view. Every ML flag has per-feature attribution. It never stands alone.

**Novel analytics**
- **Investigation Depth Score (case level):** weighted composite of workflow events, time-on-task relative to alert complexity, note length and uniqueness, enrichment or pivot actions, linked artefacts, handoffs, root cause recorded. Scaled 0-1; weights in config. Feeds EG-03/04 and the sample optimiser.
- **Metric-Gaming Divergence Index (entity level):** compare the trend of reported KPIs (MTTR, SLA %, closure rate) with behavioural trends (depth score, template ratio, burst score, escalation rate). Index = signed slope divergence, normalised, with bootstrap confidence interval. High when KPIs improve while behaviour worsens.
- **Expected-Evidence Model:** the peer-derived model behind NS-02/04/05/08.

**Governance**
- Versioned per-detector configs; minimum-sample rule; editable allowlist/context registry (noisy rules, maintenance windows) with audited edits; unit test per detector against injected ground truth.
- **Exit:** all detectors run, are tested, and recover their injected weaknesses.

### Phase 5: Scoring and prioritisation (Days 12-17)
1. **Capability mapping:** each finding maps to one or more of the 8 PS areas (Threat Detection, Investigation, Escalation, Incident Response, Security Operations, Governance and Oversight, Operational Discipline, Cyber Resilience). Mapping table is in config and docs.
2. **Finding score** = severity weight × normalised effect size × confidence.
3. **Capability score** (per entity) = noisy-OR: `1 − Π(1 − s_i)`. Avoids one finding dominating and avoids linear double counting.
4. **Attention Index** = weighted mean of capability scores (weights in config). Waterfall shows which findings drove it.
5. **Four-level prioritisation:** entities, controls/processes (weakest capability areas), investigations (case ranking), alert samples.
6. **Review-sample optimiser:**
   - Input: budget K (cases or hours), per entity or total.
   - Allocation stratified by entity attention, severity and detector hits; expected yield estimated from detector-hit patterns.
   - About 20% reserved as random exploration to surface unknown weaknesses and keep yield estimates unbiased.
   - Output: sample list with a "why selected" tag per case and estimated lift over random.
7. **Unknown-unknowns channel:** ML outliers and rare pattern clusters that no rule explains.
8. **Supervisor feedback loop:** examiners mark findings confirmed / not useful / needs context. Feedback proposes offline weight and threshold changes; an admin approves them and each change creates a new versioned config entry in the audit chain. No silent auto-tuning.
- **Exit:** ranked entities, processes, cases and samples from one run; optimiser beats random on synthetic data.

### Phase 6: Explainability and audit (Days 14-19)
- **Finding cards:** deterministic templated rationale (for example "37 of 52 critical alerts (71%) were closed without escalation; peer median is 9%"), metric vs peer distribution vs threshold, confidence, sample size, evidence rows with drill-down, innocent-explanations list, detector ID/version/config hash.
- **Run manifest:** data hashes, detector versions, config hash, code version, model hashes, seeds. Re-running a manifest must reproduce identical findings (automated test).
- **Tamper-evident audit chain:** append-only; each entry stores the SHA-256 of the previous entry plus the event (ingest, run, finding set, config change, feedback, export). Verify via UI button and CLI. Reports are signed with a local key and embed the run hash.
- **ML specification (mandatory in PS):**

| Item | Content |
|---|---|
| Model architecture | Isolation Forest (n_estimators, contamination in config); optional MiniLM-class embedding model (name, size, file hash) |
| Hardware | CPU only; state cores/RAM; GPU optional and not required |
| Offline training / inference | Trained on synthetic plus locally available submissions; inference batch-only on the same server |
| Update mechanism | Signed model bundle on removable media, checksum verified, version pinned, rollback supported |
| Explainability controls | Per-feature attribution on every ML flag; no ML-only findings |
| Auditability controls | Model hash and parameters in run manifest; retraining events in audit chain |

- **Exit:** pick any flagged entity, click to raw rows, verify chain and reproducibility.

### Phase 7: UI, dashboards, reports (Days 14-21, parallel)
1. Portfolio overview: entities × 8 capability heatmap, ranked Attention list.
2. Entity profile: capability radar, peer comparison, trends, top findings.
3. Findings explorer: filter by detector, capability, confidence.
4. Negative-space view: asset-vs-telemetry coverage matrix; expected-vs-observed categories.
5. Execution-gap view: closure-time distributions, escalation funnel, note-similarity clusters, burst timeline.
6. Trend analysis across entities and periods.
7. Review workbench: optimised sample with evidence and examiner verdict buttons.
8. Data quality, audit and config history.
9. Report generator: entity report and portfolio summary (PDF/HTML) with finding appendix and run hash.
- Every chart drills to underlying rows.
- **Exit:** load → run → overview → entity → finding → evidence → report in under 2 minutes.

### Phase 8: Validation harness (Days 16-24)
1. **Ground-truth recovery:** recall per injected weakness type; false-positive rate on decoys.
2. **Manual-sampling baseline:** simulate examiners reviewing random and stratified samples of N cases; compare with SAT-SA top-N at equal effort. Report precision@k, recall@k and lift with confidence intervals over many seeds.
3. **Entity-ranking quality:** Spearman/Kendall between Attention Index and true injected severity; top-k hit rate.
4. **Ablations:** rules only vs rules + peer layer vs full (with ML).
5. **Robustness:** noise levels, missing optional fields, small entities, threshold sensitivity, weight-perturbation stability (do top-5 entities persist?).
6. **Negative-space test:** remove telemetry from selected assets and measure recovery.
7. **Real-world protocol (documented):** blind study where NCIIPC examiners review a mix of tool-selected and random cases; measure finding yield, Cohen's kappa, time saved; back-test against past manual findings as labels.
8. **Public data sanity check** (prepared offline) for ingestion and detector behaviour, stated as not validating supervisory findings.
- **Exit:** one command produces the validation report with headline numbers for the slides.

### Phase 9: Scalability (Days 18-24)
- Benchmarks at 1M / 10M / 50M rows: ingest time, full-run time, memory, UI query latency; publish with hardware used.
- Techniques: Parquet partitioning, materialised entity-period aggregates, vectorised SQL detectors, MinHash instead of pairwise comparison, subsampling for ML training.
- Incremental runs: recompute only entity-periods whose data changed.

### Phase 10: Deployment packaging (Days 22-26)
- Offline bundle (image tar or venv + wheelhouse) with models, fonts and checksum manifest; install script; smoke test.
- **Zero-network proof:** test that fails on any DNS or socket call during a full run.
- Runbook: install, config, backup/restore, retention, user management.
- Infrastructure: minimum and recommended specs (CPU, RAM, storage per 100M rows), isolated LAN with browser-only access, local auth, optional encryption at rest.
- Operating model: roles (admin, examiner), monthly cycle (receive submissions → ingest → run → review → report), effort estimate.

### Phase 11: Documentation and submission (Days 24-28)

| Deliverable | Content |
|---|---|
| GitHub repo + README | Offline setup, quick start, synthetic data command, demo walkthrough |
| Architecture doc (max 2 pages) | One diagram, data flow, components, ML spec table, air-gap model, infrastructure |
| Demo video (max 2 min) | Script below |
| Presentation (max 5 slides) | Plan below |
| `docs/` | Functional design, analytics methodology (formulas), data requirements, validation methodology, deployment and operations estimate |

**Slides**
1. Problem and insight: KPIs and audits miss execution gaps and negative space.
2. Solution and architecture: offline pipeline, detectors, explainable prioritisation.
3. Novelty: Metric-Gaming Divergence Index, Investigation Depth Score, Expected-Evidence Model, sample optimiser, audit chain.
4. Validation: lift over manual sampling, recall, false-positive control, scale benchmarks.
5. Deployment and roadmap: air-gap packaging, infra, ML controls, fit to NCIIPC workflow.

**Video (2:00)**
- 0:00-0:15 problem in one sentence
- 0:15-0:45 load multi-entity data; portfolio heatmap; top entity
- 0:45-1:15 negative-space finding (silent critical assets) then execution-gap finding (criticals closed without escalation) with evidence drill-down
- 1:15-1:35 optimised review sample and lift over random
- 1:35-1:50 verify audit chain; export signed report
- 1:50-2:00 air-gapped and scale claims

## 7. Requirements traceability

| PS requirement | Covered by |
|---|---|
| Multi-CSE ingest, CSV/JSON/DB/API, large scale | Phases 3, 9 |
| Detection/investigation/escalation weaknesses | EG-01/02/03, NS-04/05 |
| Execution gaps | EG-01 to EG-11 |
| Negative space | NS-01 to NS-08, Expected-Evidence Model |
| Anomalies and outliers | ML signal, unknown-unknowns view |
| Peer comparison and benchmarking | Peer layer |
| Entity-level risk indicators | Attention Index, capability scores |
| Prioritise entities, controls, processes, samples | Phase 5 |
| Rationale, evidence, traceability, "why flagged" | Phase 6 |
| Dashboards, reports, trends, drill-down | Phase 7 |
| Offline, no cloud/SaaS/external AI | Phase 10, ML spec |
| ML specification (six items) | Phase 6 table |
| Validation against expert review | Phase 8 |
| Additional supervisory insights | Depth Score, Gaming Index, optimiser, feedback loop, temporal integrity |
| All deliverables | Phase 11 |

**Nine illustrative use cases:** (i) EG-01, (ii) EG-05, (iii) EG-02, (iv) NS-01, (v) peer layer, (vi) NS-06, (vii) EG-04, (viii) Gaming Index, (ix) NS-04/05/08.

## 8. Team split (4 people)
- **A. Data:** schema, generator, connectors, scale benchmarks
- **B. Analytics:** detectors, peer models, scoring, sample optimiser
- **C. Platform/UI:** finding cards, audit chain, dashboards, reports, packaging
- **D. Validation/docs:** harness, methodology, slides, video; also plays "sceptical examiner" reviewing every finding card

For 3 people, merge D's data-side work into A. For 2, apply the cut-list.

## 9. Weekly milestones

| Week | Milestone |
|---|---|
| 1 | Schema, generator v1, ingestion, first detectors (EG-01/02/03, NS-01/02), skeleton UI |
| 2 | All detectors, peer benchmarking, scoring, finding cards |
| 3 | Sample optimiser, audit chain, dashboards/reports, validation v1, scale tests |
| 4 | Ablations, robustness, packaging, docs, video, slides, dry run on a clean offline machine |

## 10. Risks and mitigations

| Risk | Mitigation |
|---|---|
| No real data | Realistic generator plus mapping layer for common tool exports; documented expert-study protocol |
| False positives erode trust | Min-sample rule, context registry, innocent-explanations lists, decoy testing |
| Overclaiming ML | Rules first; ML labelled secondary with attributions; ablation shows its contribution honestly |
| Drift into SIEM territory | Batch only, no telemetry collection, stated in README and slides |
| Demo fragility | Frozen seeded demo dataset; dry run on clean offline machine |
| Peer groups too small | Fall back to sector-level or own-history baselines; flag lower confidence |

## 11. Quality gates
- Unit test per detector against ground truth
- Reproducibility test (manifest re-run yields identical findings)
- Audit-chain tamper test (edit one entry, verification fails)
- Zero-network test
- Validation report regenerated from a clean checkout

## 12. Definition of done
- Clean offline machine installs from the bundle and runs the demo with no network
- Every PS requirement above is demonstrable
- Validation report shows lift over manual sampling with confidence intervals
- Any finding traces to raw rows and the chain verifies
- 10M+ rows run within stated time and memory
- Architecture doc is 2 pages, slides 5, video at most 2 minutes

## 13. What makes it stand out
1. Negative space treated as a first-class, quantified problem (absence confidence, expected-evidence model)
2. Metric-Gaming Divergence Index addressing "satisfies metrics without reducing risk"
3. Review-sample optimiser with measured lift and built-in exploration
4. Fully deterministic explanations and a verifiable audit chain
5. Honest, reproducible validation with decoys and ablations

## 14. Cut-list (drop in this order if time is short)
1. Optional embedding model (keep TF-IDF/MinHash)
2. REST connector
3. Analyst and shift detectors (EG-10, EG-11)
4. Report signing (keep chain verification)
5. Incremental runs

**Never cut:** negative-space detectors, explainability cards, validation harness, sample optimiser, air-gap packaging, ML specification table.
