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
from satsa.scoring.prioritiser import aggregate_capability_scores, calculate_attention_index
from satsa.scoring.optimiser import optimize_review_sample
from satsa.audit.chain import log_event, verify_chain
from satsa.synthetic.generator import generate_sample_data
from satsa.ingest.loader import load_data

# --- Page Config ---
st.set_page_config(page_title="SAT-SA Examiner", page_icon=":material/admin_panel_settings:", layout="wide", initial_sidebar_state="expanded")

# --- Custom CSS for Professional Look ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* Apply Inter font globally */
    html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
    
    /* Main background */
    .stApp { background-color: #F4F6F9; }
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
st.sidebar.markdown("`Supervise-SOC | NTRO`")
st.sidebar.markdown("---")

nav_selection = st.sidebar.radio("Main Menu", [
    "Dashboard Overview", 
    "Entity Portfolio", 
    "Findings Explorer", 
    "Smart Review Optimiser",
    "Audit Ledger"
], index=0)

st.sidebar.markdown("---")
st.sidebar.markdown("### :material/settings: Actions")
run_assessment = st.sidebar.button(":material/play_arrow: Run Assessment", type="primary", use_container_width=True)
verify_ledger = st.sidebar.button(":material/verified_user: Verify Ledger", use_container_width=True)
generate_demo = st.sidebar.button(":material/database: Load Demo Data", use_container_width=True)

# --- Assessment Logic ---
if generate_demo:
    with st.spinner("Generating and loading synthetic SOC data..."):
        generate_sample_data()
        load_data()
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
        all_findings = eg01 + ns01
        cap_scores = aggregate_capability_scores(all_findings)
        ranking = calculate_attention_index(cap_scores)
        
        st.session_state['findings'] = all_findings
        st.session_state['ranking'] = ranking
        log_event("ASSESSMENT_RUN", f"Generated {len(all_findings)} findings.")
        st.sidebar.success("Assessment Complete")

if verify_ledger:
    if verify_chain():
        st.sidebar.success("Ledger is Cryptographically Valid!")
    else:
        st.sidebar.error("Tampering Detected in Ledger!")

# --- Helper variables ---
has_run = 'ranking' in st.session_state
has_data = has_run and len(st.session_state['ranking']) > 0

# ==========================================
# VIEW: Dashboard Overview
# ==========================================
if nav_selection == "Dashboard Overview":
    st.markdown("## Welcome back, Examiner")
    
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
            st.dataframe(filtered, use_container_width=True, hide_index=True)
        else:
            st.info("No findings match the current filters.")
    elif has_run:
        st.success("No findings were generated during the assessment.")
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
    st.markdown("Append-only SHA-256 chain of all system events. Tamper-evident and secure.")
    
    chain_path = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))) / "data" / "audit_chain.jsonl"
    
    if chain_path.exists():
        with open(chain_path, "r") as f:
            blocks = [json.loads(line) for line in f]
            
        df_blocks = pd.DataFrame(blocks)
        st.dataframe(df_blocks.iloc[::-1], use_container_width=True, hide_index=True)
    else:
        st.info("No audit logs found yet.")
