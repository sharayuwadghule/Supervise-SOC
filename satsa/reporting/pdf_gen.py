import os
from pathlib import Path
from fpdf import FPDF
import pandas as pd
from datetime import datetime

class SATReport(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 15)
        self.cell(0, 10, 'SAT-SA Examiner Report', border=False, align='C', new_x="LMARGIN", new_y="NEXT")
        self.set_font('helvetica', 'I', 10)
        self.cell(0, 10, f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}', border=False, align='C', new_x="LMARGIN", new_y="NEXT")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')

def generate_pdf_report(rankings: list, findings: list):
    pdf = SATReport()
    pdf.add_page()
    
    # Title
    pdf.set_font("helvetica", "B", 14)
    pdf.cell(0, 10, "1. Executive Summary", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 11)
    pdf.multi_cell(0, 8, f"This report contains the findings of the offline SAT-SA anomaly detection engine. A total of {len(findings)} potential weaknesses were detected across {len(rankings)} entities.")
    pdf.ln(5)
    
    # Portfolio Ranking
    pdf.set_font("helvetica", "B", 14)
    pdf.cell(0, 10, "2. Entity Risk Ranking", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 10)
    
    # Table header
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(60, 10, "Entity ID", border=1, fill=True)
    pdf.cell(60, 10, "Attention Index", border=1, fill=True)
    pdf.cell(60, 10, "Risk Level", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
    
    for r in sorted(rankings, key=lambda x: x['attention_index'], reverse=True):
        idx = r['attention_index']
        risk = "Critical" if idx > 0.3 else ("Warning" if idx > 0.1 else "Good")
        pdf.cell(60, 10, r['entity_id'], border=1)
        pdf.cell(60, 10, f"{idx:.3f}", border=1)
        pdf.cell(60, 10, risk, border=1, new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(10)
    
    # Top Findings
    pdf.add_page()
    pdf.set_font("helvetica", "B", 14)
    pdf.cell(0, 10, "3. Critical Findings (Top 50)", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 10)
    
    df_find = pd.DataFrame(findings)
    if not df_find.empty:
        top_findings = df_find.sort_values('severity', ascending=False).head(50)
        for _, row in top_findings.iterrows():
            pdf.set_font("helvetica", "B", 11)
            pdf.cell(0, 8, f"[{row['detector_id']}] Entity: {row['entity_id']} (Sev: {row['severity']})", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("helvetica", "", 10)
            pdf.multi_cell(0, 6, row['rationale'])
            pdf.ln(4)
            
    out_dir = Path(__file__).parent.parent.parent / "data" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"SAT_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    
    pdf.output(str(out_path))
    return str(out_path)
