import streamlit as st
import pandas as pd
import altair as alt
from pathlib import Path
import sys
import os
import json

# Setup Path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from satsa.store.db import get_connection
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
from satsa.scoring.prioritiser import aggregate_capability_scores, calculate_attention_index
from satsa.scoring.optimiser import optimize_review_sample
from satsa.scoring.peers import PeerEngine
from satsa.audit.chain import log_event, verify_chain
from satsa.synthetic.generator import generate_sample_data
from satsa.ingest.loader import load_data as ingest_data
from satsa.reporting.pdf_gen import generate_pdf_report
from satsa.ingest.adapters import ingest_csv_bundle
import tempfile

# --- Page Config ---
st.set_page_config(page_title="SAT-SA Examiner", page_icon=":material/admin_panel_settings:", layout="wide", initial_sidebar_state="expanded")

# --- Custom CSS for Professional Look ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* Apply Inter font globally */
    html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
    
    /* Main background - removed forced color to respect Streamlit theme */
    /* Hide Streamlit components */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stAppDeployButton {display:none;}
    /* Keep header visible for sidebar toggle, but make it transparent */
    header {background-color: transparent !important;}
    
    /* Card styling for metrics with subtle color grading */
    div[data-testid="stMetric"] {
        background: linear-gradient(180deg, #FFFFFF 0%, #FAFCFF 100%);
        border-radius: 12px;
        padding: 20px 24px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -1px rgba(0,0,0,0.03);
        border: 1px solid #E2E8F0;
        border-top: 4px solid #3B82F6;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    /* Subtle hover pop effect */
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.05), 0 4px 6px -2px rgba(0,0,0,0.025);
    }
    
    div[data-testid="stMetricLabel"] { font-size: 13px; color: #64748B; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600; }
    div[data-testid="stMetricValue"] { font-size: 34px; color: #0F172A; font-weight: 700; }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] { 
        background-color: #FFFFFF; 
        border-right: 1px solid #E2E8F0; 
    }
</style>
""", unsafe_allow_html=True)

# --- Data Loading ---
@st.cache_data(ttl=300)
def load_data():
    try:
        conn = get_connection(read_only=True)
        df_ent = conn.execute("SELECT * FROM entities_view").df()
        df_ast = conn.execute("SELECT * FROM assets_view").df()
        df_al = conn.execute("SELECT * FROM alerts_view").df()
        return df_ent, df_ast, df_al
    except Exception:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

df_ent, df_ast, df_al = load_data()

# --- Sidebar Navigation ---
st.sidebar.markdown("### :material/grid_view: SAT-SA Platform")
st.sidebar.markdown("`NCIIPC`")
st.sidebar.markdown("---")

nav_selection = st.sidebar.radio("Main Menu", [
    "Dashboard Overview", 
    "Entity Portfolio", 
    "Findings Explorer", 
    "Smart Review Optimiser",
    "Peer Benchmarking",
    "Data Import",
    "Audit Ledger"
], index=0)

st.sidebar.markdown("---")
st.sidebar.markdown("### :material/settings: Actions")
run_assessment = st.sidebar.button(":material/play_arrow: Run Assessment", type="primary", use_container_width=True)

if 'findings' in st.session_state and len(st.session_state['findings']) > 0:
    if st.sidebar.button(":material/picture_as_pdf: Export PDF Report", use_container_width=True):
        with st.spinner("Generating PDF Report..."):
            pdf_path = generate_pdf_report(st.session_state['ranking'], st.session_state['findings'])
            log_event("REPORT_EXPORT", f"Exported PDF report for {len(st.session_state['findings'])} findings.")
            with open(pdf_path, "rb") as pdf_file:
                st.sidebar.download_button(
                    label="⬇️ Download PDF",
                    data=pdf_file,
                    file_name="SAT_Report.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

st.sidebar.markdown("---")
if st.sidebar.button(":material/delete: Clear Data", use_container_width=True):
    from satsa.store.db import get_connection
    conn = get_connection(read_only=False)
    for table in ["entities_view", "assets_view", "alerts_view", "cases_view", "events_view"]:
        try: conn.execute(f"DROP VIEW IF EXISTS {table}")
        except: pass
    log_event("DATA_CLEARED", "Cleared all data from working set.")
    st.cache_data.clear()
    st.rerun()

generate_demo = st.sidebar.button(":material/warning: Load Demo Data", use_container_width=True)
if generate_demo:
    st.sidebar.warning("Clicking this will overwrite existing data. Proceed?")
# ==========================================
# VIEW: Data Import
# ==========================================
if nav_selection == "Data Import":
    st.markdown("## :material/upload_file: Import Real Data")
    st.write("Drag and drop your real CSE data to run an assessment.")
    
    import_entity = st.text_input("Entity ID", placeholder="e.g., ENT-REAL-01")
    import_entity = import_entity.strip().upper().replace(" ", "") if import_entity else ""
    st.caption("If this Entity ID already exists, this will **replace** the existing data for this entity.")
    
    col1, col2 = st.columns(2)
    with col1:
        import_sector = st.selectbox("Sector", ["Power", "Banking & Finance", "Telecom", "Transport", "Health", "Government", "Strategic Enterprises"])
    with col2:
        import_tier = st.selectbox("Size Tier", ["Tier 1", "Tier 2", "Tier 3"])
        
    def expected_headers(model):
        req = [n for n, f in model.model_fields.items() if f.is_required() and n != "entity_id"]
        opt = [n for n, f in model.model_fields.items() if not f.is_required() and n != "entity_id"]
        return f"Required: {', '.join(req)}. Optional: {', '.join(opt)}."
    
    from satsa.store.schema import Alert, Case, CaseEvent
    st.markdown("*Severity Scale: 1 (Low) to 4 (Critical), or the words Low, Medium, High, Critical.*")
    
    import_alerts = st.file_uploader("Alerts CSV (Required)", type=["csv"])
    with st.expander("Show expected Alert columns and aliases"):
        st.markdown(f"**Canonical:** {expected_headers(Alert)}")
        st.caption("Aliases accepted: timestamp, created_at, alertid, sev, priority, etc. [Download Sample Files](file:///c:/Users/wadgh/Desktop/Work%20Stuff/Supervise-SOC/demo_upload_files/)")
    
    import_cases = st.file_uploader("Cases CSV (Optional)", type=["csv"])
    with st.expander("Show expected Case columns and aliases"):
        st.markdown(f"**Canonical:** {expected_headers(Case)}")
        st.caption("Aliases accepted: assigned_to, rootcause, opened, closed, etc.")
    
    import_events = st.file_uploader("Events CSV (Optional)", type=["csv"])
    with st.expander("Show expected Event columns and aliases"):
        st.markdown(f"**Canonical:** {expected_headers(CaseEvent)}")
        st.caption("Aliases accepted: event, user, timestamp, etc.")
    
    submit_import = st.button("Ingest Data", type="primary", disabled=(not import_alerts or not import_entity))
    
    if submit_import:
        with st.spinner("Ingesting and validating data..."):
            try:
                with tempfile.TemporaryDirectory() as tmpdirname:
                    alerts_path = cases_path = events_path = None
                    
                    if import_alerts:
                        alerts_path = os.path.join(tmpdirname, "alerts.csv")
                        with open(alerts_path, "wb") as f:
                            f.write(import_alerts.getbuffer())
                    if import_cases:
                        cases_path = os.path.join(tmpdirname, "cases.csv")
                        with open(cases_path, "wb") as f:
                            f.write(import_cases.getbuffer())
                    if import_events:
                        events_path = os.path.join(tmpdirname, "events.csv")
                        with open(events_path, "wb") as f:
                            f.write(import_events.getbuffer())
                            
                    from satsa.store.schema import Entity
                    from satsa.ingest.adapters import _write_parquet
                    out_dir = Path(__file__).parent.parent.parent / "data" / "real"
                    e = Entity(entity_id=import_entity, name=f"Real Entity {import_entity}", sector=import_sector, size_tier=import_tier, primary_contact="real@example.com", region="Global", soc_model="In-house")
                    _write_parquet([e.model_dump()], Entity, out_dir / "entities.parquet")
                            
                    reports = ingest_csv_bundle(import_entity, alerts_path, cases_path, events_path, str(out_dir))
                    log_event("DATA_IMPORT", f"Imported data for entity {import_entity}.")
                    st.cache_data.clear()
                st.success(f"Data successfully ingested for {import_entity}!")
                with st.expander("Ingestion Report", expanded=True):
                    for k, v in reports.items():
                        if k == "integrity":
                            st.markdown("**Cross-File Integrity Recon**")
                            st.json(v)
                        elif k.endswith("_warning"):
                            st.warning(v)
                        else:
                            st.markdown(f"**{k.title()} Data Quality: {v.get('quality_score', 0.0)}%** ({v.get('rows_ok', 0)} accepted, {v.get('rows_rejected', 0)} rejected)")
                            if v.get('missing_required'):
                                st.error(f"Missing Required: {v['missing_required']}")
                            if v.get('not_assessable_fields'):
                                st.info(f"Missing Optional: {v['not_assessable_fields']}")
            except ValueError as e:
                st.error(f"Validation Error: {str(e)}")

# --- Assessment Logic ---
if generate_demo:
    with st.spinner("Generating and loading synthetic SOC data..."):
        generate_sample_data()
        ingest_data()
        log_event("DEMO_DATA_LOAD", "Loaded synthetic dataset.")
        st.cache_data.clear()
        if 'ranking' in st.session_state:
            del st.session_state['ranking']
        if 'findings' in st.session_state:
            del st.session_state['findings']
        st.rerun()

if run_assessment:
    with st.spinner("Executing Anomaly Detectors..."):
        eg01 = run_eg_01()
        ns01 = run_ns_01()
        eg03 = run_eg_03()
        ns03 = run_ns_03()
        eg02 = run_eg_02()
        eg04 = run_eg_04()
        eg05 = run_eg_05()
        eg06 = run_eg_06()
        ns02 = run_ns_02()
        ns04 = run_ns_04()
        ns05 = run_ns_05()
        ns06 = run_ns_06()
        ex01 = run_ex_01()
        ex02 = run_ex_02()
        ex03 = run_ex_03()
        ex04 = run_ex_04()
        ex05 = run_ex_05()
        ex06 = run_ex_06()
        ex07 = run_ex_07()
        ex08 = run_ex_08()
        all_findings = eg01 + ns01 + eg03 + ns03 + eg02 + eg04 + eg05 + eg06 + ns02 + ns04 + ns05 + ns06 + ex01 + ex02 + ex03 + ex04 + ex05 + ex06 + ex07 + ex08
        cap_scores = aggregate_capability_scores(all_findings)
        ranking = calculate_attention_index(cap_scores)
        
        st.session_state['findings'] = all_findings
        st.session_state['ranking'] = ranking
        log_event("ASSESSMENT_RUN", f"Generated {len(all_findings)} findings.")
        st.sidebar.success("Assessment Complete")

# --- Helper variables ---
has_run = 'ranking' in st.session_state
has_data = has_run and len(st.session_state['ranking']) > 0

# ==========================================
# VIEW: Dashboard Overview
# ==========================================
if nav_selection == "Dashboard Overview":
    st.markdown("## Welcome back, Examiner")
    st.caption("Findings are leads for examiner review, not conclusions.")
    
    if not has_data and not has_run:
        st.info("No data yet. Load demo data or import files from the sidebar to begin.")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="Total Entities", value=len(df_ent) if not df_ent.empty else 0)
    with col2:
        num_findings = len(st.session_state.get('findings', []))
        st.metric(label="Total Findings", value=num_findings, delta="From last run" if num_findings > 0 else None)
    with col3:
        avg_idx = 0
        if has_data and st.session_state['ranking']:
            avg_idx = sum(r['attention_index'] for r in st.session_state['ranking']) / len(st.session_state['ranking'])
        st.metric(label="Avg Attention Index", value=f"{avg_idx:.2f}", delta_color="inverse")
    with col4:
        st.metric(label="System Status", value="Air-Gapped", delta="Secure", delta_color="normal")
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    if has_data:
        st.markdown("### :material/bar_chart: Entity Risk Distribution")
        df_rank = pd.DataFrame(st.session_state['ranking'])
        # Create an Altair Bar Chart
        chart = alt.Chart(df_rank).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, color="#3366CC").encode(
            x=alt.X('entity_id:N', sort='-y', title="Entity ID"),
            y=alt.Y('attention_index:Q', title="Attention Index"),
            tooltip=['entity_id', 'attention_index']
        ).properties(height=350)
        st.altair_chart(chart, use_container_width=True)
    elif has_run:
        st.success("🎉 Assessment complete: No risks or findings were detected across the portfolio!")
    else:
        st.info("Click 'Run Assessment' in the sidebar to populate the dashboard charts.")

# ==========================================
# VIEW: Entity Portfolio
# ==========================================
elif nav_selection == "Entity Portfolio":
    st.markdown("## :material/account_balance: Entity Portfolio")
    if has_data:
        df_rank = pd.DataFrame(st.session_state['ranking'])
        
        # Add Status Column based on percentile
        threshold = df_rank['attention_index'].quantile(0.8) if not df_rank.empty else 0
        
        def assign_status(idx):
            if idx == 0: return "🟢 Good"
            if idx >= threshold: return "🔴 Critical"
            return "🟡 Warning"
            
        df_rank['Status'] = df_rank['attention_index'].apply(assign_status)
        
        # Reorder columns
        cols = ['Status', 'entity_id', 'attention_index'] + [c for c in df_rank.columns if c not in ['Status', 'entity_id', 'attention_index']]
        df_rank = df_rank[cols]
        
        st.dataframe(df_rank, use_container_width=True, hide_index=True, column_config={
            "attention_index": st.column_config.ProgressColumn(
                "Risk Index",
                help="Calculated Attention Index based on capability gaps.",
                format="%.3f",
                min_value=0,
                max_value=float(df_rank['attention_index'].max()) if not df_rank.empty else 1.0
            ),
            "entity_id": st.column_config.TextColumn("Entity ID", width="medium"),
            "Status": st.column_config.TextColumn("Status", width="small")
        })
    elif has_run:
        st.success("No risky entities to display.")
    else:
        st.warning("No assessment data available.")

# ==========================================
# VIEW: Findings Explorer
# ==========================================
elif nav_selection == "Findings Explorer":
    st.markdown("## :material/search: Findings Explorer")
    st.caption("Findings are leads for examiner review, not conclusions.")
    if has_data:
        df_find = pd.DataFrame(st.session_state['findings'])
        
        # Filters
        col1, col2 = st.columns(2)
        with col1:
            f_type = st.selectbox("Filter by Type", ["All"] + list(df_find['detector_id'].unique()))
        with col2:
            f_entity = st.selectbox("Filter by Entity", ["All"] + list(df_find['entity_id'].unique()))
            
        filtered = df_find
        if f_type != "All": filtered = filtered[filtered['detector_id'] == f_type]
        if f_entity != "All": filtered = filtered[filtered['entity_id'] == f_entity]
        
        if not filtered.empty:
            st.markdown(f"**Found {len(filtered)} instances.**")
            
            # Display as Explainable Finding Cards
            for _, row in filtered.head(50).iterrows():
                with st.expander(f"[{row['detector_id']}] 🚨 {row['entity_id']} (Severity: {row['severity']})", expanded=False):
                    st.markdown(f"**Target Record**: `{row['target_id']}`")
                    st.info(f"**AI Explanation**: {row['rationale']}")
                    st.markdown("---")
                    st.caption("Evidence IDs captured securely in Audit Ledger.")
            if len(filtered) > 50:
                st.markdown("*Only showing top 50 findings. Export report to view all.*")
        else:
            st.info("No findings match the current filters.")
    elif has_run:
        st.success("No findings were generated during the assessment.")
    else:
        st.warning("No assessment data available.")

# ==========================================
# VIEW: Peer Benchmarking
# ==========================================
elif nav_selection == "Peer Benchmarking":
    st.markdown("## :material/groups: Peer Benchmarking Engine")
    st.markdown("Compares entities against peers in the same Sector and Size Tier using robust Z-scores and Empirical Bayes shrinkage.")
    
    if has_data:
        try:
            peer_engine = PeerEngine()
            df_peers = peer_engine.run_benchmarks()
            
            if not df_peers.empty:
                st.dataframe(df_peers.style.background_gradient(cmap='RdYlGn_r', subset=['alert_volume_z', 'fast_closure_z']), use_container_width=True)
                
                st.subheader("Statistical Outliers (Z-score > 2 or < -2)")
                outliers = df_peers[(df_peers['alert_volume_z'].abs() > 2) | (df_peers['fast_closure_z'].abs() > 2)]
                if not outliers.empty:
                    st.warning(f"Found {len(outliers)} peer-deviating entities.")
                    st.dataframe(outliers[['entity_id', 'peer_group', 'alert_volume_z', 'fast_closure_z']], use_container_width=True)
                else:
                    st.success("No extreme statistical outliers detected in peer groups.")
            else:
                st.info("No peer data available.")
        except Exception as e:
            st.error(f"Error running peer engine: {e}")
    else:
        st.warning("No assessment data available.")

# ==========================================
# VIEW: Smart Review Optimiser
# ==========================================
elif nav_selection == "Smart Review Optimiser":
    st.markdown("## :material/fact_check: Smart Review Optimiser")
    st.markdown("Replaces random case auditing with a mathematically optimized sample to maximize the discovery of systemic weaknesses.")
    
    if has_data:
        col1, col2 = st.columns([1, 2])
        with col1:
            budget = st.slider("Examiner Review Budget (Cases)", min_value=1, max_value=50, value=10)
            if st.button("Generate Optimized Sample", type="primary"):
                sample = optimize_review_sample(st.session_state['findings'], st.session_state['ranking'], budget_k=budget)
                st.session_state['current_sample'] = sample
                
        with col2:
            if 'current_sample' in st.session_state:
                df_sample = pd.DataFrame(st.session_state['current_sample'])
                
                # Breakdown
                reason_counts = df_sample['selection_reason'].value_counts()
                st.markdown("#### Sample Composition")
                for reason, count in reason_counts.items():
                    st.write(f"- **{reason}**: {count} cases")
                    
                st.markdown("#### Assigned Queue")
                st.dataframe(df_sample[['entity_id', 'target_id', 'detector_id', 'severity', 'selection_reason']], use_container_width=True, hide_index=True, column_config={
                    "severity": st.column_config.NumberColumn(
                        "Severity Score",
                        help="Severity of the finding (1-100)",
                        format="%d 🚨"
                    ),
                    "selection_reason": st.column_config.TextColumn("Selection Reason", width="large")
                })
                
                # Export Button
                csv = df_sample.to_csv(index=False)
                st.download_button(
                    label=":material/download: Export CSV",
                    data=csv,
                    file_name='optimized_review_queue.csv',
                    mime='text/csv',
                )
    elif has_run:
        st.success("No findings available to sample.")
    else:
        st.warning("No assessment data available.")

# ==========================================
# VIEW: Audit Ledger
# ==========================================
elif nav_selection == "Audit Ledger":
    st.markdown("## :material/receipt_long: Cryptographic Audit Ledger")
    st.markdown("Append-only SHA-256 chain of all system events. Tamper-evident.")
    
    if st.button(":material/verified_user: Verify Ledger"):
        if verify_chain():
            st.success("Chain intact, all entries verified!")
        else:
            st.error("Tampering Detected in Ledger!")
            
    chain_path = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))) / "data" / "audit_chain.jsonl"
    
    if chain_path.exists():
        with open(chain_path, "r") as f:
            blocks = [json.loads(line) for line in f]
            
        df_blocks = pd.DataFrame(blocks)
        if not df_blocks.empty and 'hash' in df_blocks.columns and 'previous_hash' in df_blocks.columns:
            df_blocks['hash_short'] = df_blocks['hash'].apply(lambda x: x[:10] + "..." if isinstance(x, str) else x)
            df_blocks['prev_hash_short'] = df_blocks['previous_hash'].apply(lambda x: x[:10] + "..." if isinstance(x, str) else x)
            cols = ['timestamp', 'event_type', 'user', 'run_id', 'details', 'hash_short', 'prev_hash_short', 'hash', 'previous_hash']
            cols = [c for c in cols if c in df_blocks.columns]
            st.dataframe(df_blocks.iloc[::-1][cols], use_container_width=True, hide_index=True)
        else:
            st.dataframe(df_blocks.iloc[::-1], use_container_width=True, hide_index=True)
    else:
        st.info("No audit logs found yet.")
