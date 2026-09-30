import streamlit as st
import pandas as pd
from pathlib import Path
from satsa.store.db import get_connection
from satsa.detectors.eg_01 import run_eg_01
from satsa.detectors.ns_01 import run_ns_01
from satsa.scoring.prioritiser import aggregate_capability_scores, calculate_attention_index
from satsa.audit.chain import log_event, verify_chain

# ---------------------------------------------------------
# SAT-SA Streamlit UI (Phase 7)
# ---------------------------------------------------------

st.set_page_config(page_title="SAT-SA Examiner", layout="wide")

st.title("🛡️ Supervisory Analytics Tool for SOC Assessment (SAT-SA)")
st.markdown("---")

def get_entities():
    try:
        conn = get_connection(read_only=True)
        return conn.execute("SELECT * FROM entities_view").df()
    except Exception:
        return pd.DataFrame()

# Sidebar
st.sidebar.header("Controls")
if st.sidebar.button("Verify Audit Chain"):
    if verify_chain():
        st.sidebar.success("Audit Chain Intact!")
    else:
        st.sidebar.error("Tampering Detected!")

st.sidebar.markdown("---")
if st.sidebar.button("Run Full Assessment"):
    with st.spinner("Running Execution Gap and Negative Space Detectors..."):
        # Run detectors
        eg01 = run_eg_01()
        ns01 = run_ns_01()
        all_findings = eg01 + ns01
        
        # Prioritize
        cap_scores = aggregate_capability_scores(all_findings)
        ranking = calculate_attention_index(cap_scores)
        
        # Store in session
        st.session_state['findings'] = all_findings
        st.session_state['ranking'] = ranking
        
        log_event("FULL_ASSESSMENT_RUN", f"Generated {len(all_findings)} findings.")
        st.sidebar.success("Assessment Complete")

# Main View
tab1, tab2, tab3 = st.tabs(["📊 Portfolio Overview", "🎯 Findings Explorer", "⚙️ Data Quality"])

with tab1:
    st.header("Entity Prioritisation")
    if 'ranking' in st.session_state and st.session_state['ranking']:
        df_ranking = pd.DataFrame(st.session_state['ranking'])
        st.dataframe(df_ranking, use_container_width=True)
    else:
        st.info("Click 'Run Full Assessment' in the sidebar to generate rankings.")

with tab2:
    st.header("Review Workbench (Finding Cards)")
    if 'findings' in st.session_state and st.session_state['findings']:
        df_findings = pd.DataFrame(st.session_state['findings'])
        st.dataframe(df_findings, use_container_width=True)
    else:
        st.info("No findings to display.")

with tab3:
    st.header("Data Sources")
    df_ent = get_entities()
    if not df_ent.empty:
        st.dataframe(df_ent)
    else:
        st.warning("No data found. Ensure Parquet files are loaded into DuckDB.")
