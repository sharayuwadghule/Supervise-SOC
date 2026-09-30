# SAT-SA: Supervisory Analytics Tool for SOC Assessment

**PS 26157 | NTRO / NCIIPC**

SAT-SA is an offline, batch supervisory analytics platform designed to assess Critical Sector Entities (CSEs). It ingests SOC alert and case-management logs, runs a library of transparent detectors to identify **execution gaps** and **negative space**, and benchmarks entities to produce an **explainable, audited, prioritised review queue**.

---

## 🚀 Setup & Installation Instructions

### Prerequisites
*   **Operating System:** Windows, Linux, or macOS.
*   **Python:** Python 3.9 or higher installed and added to PATH.

### 1. Environment Setup
It is highly recommended to run this tool inside a virtual environment to prevent dependency conflicts.

Open a terminal in the root of this project and run:
```powershell
# Create a virtual environment
python -m venv venv

# Activate the environment (Windows PowerShell)
.\venv\Scripts\Activate.ps1
# (On Linux/Mac use: source venv/bin/activate)

# Install the required dependencies
pip install -r satsa/requirements.txt
```

### 2. Configure Python Path
To ensure the scripts can locate the `satsa` module, set your `PYTHONPATH` to the root directory before running any scripts.
```powershell
# Windows PowerShell
$env:PYTHONPATH="."
```

### 3. Generate Synthetic Data
Because this is a batch analytical tool, it needs data to analyze. Run the generator to create baseline SOC data and inject deliberate weaknesses (e.g., fast closures, silent critical assets).
```powershell
python satsa/synthetic/generator.py
```
*This will create Parquet files in the `data/synthetic/` folder.*

### 4. Load Data into DuckDB
Load the generated Parquet files into DuckDB views so they can be queried by our detectors.
```powershell
python satsa/ingest/loader.py
```

### 5. Run the Validation Harness (Optional)
To run the automated test that proves our detectors successfully catch the injected weaknesses, and to simulate the efficiency of the Review-Sample Optimiser:
```powershell
python satsa/validation/harness.py
```

### 6. Launch the Dashboard
Start the Streamlit UI to interact with the data, run assessments, and view the tamper-evident audit chain.
```powershell
streamlit run satsa/ui/app.py
```
*The dashboard will automatically open in your default browser at `http://localhost:8501`.*

---

## 📦 Deployment (Air-Gapped Environments)

To deploy SAT-SA into a strict, zero-network environment, use the provided PowerShell packager.
```powershell
.\satsa\deploy\bundle.ps1
```
This script will extract the source code, simulate downloading the `.whl` packages for offline installation, and generate a cryptographic `manifest.sha256` proving the integrity of the build. The output will be placed in `deploy/offline_bundle/`.

---

## 📚 Documentation
*   [Core Architecture](docs/Architecture.md)
*   [Architecture Diagram & Flow](docs/Architecture_Diagram.md)
*   [Slide Presentation](docs/Presentation.md)

---

## 🌐 Deploying to Streamlit Community Cloud (For Demos)

While SAT-SA is designed to be air-gapped, you can deploy it to Streamlit Community Cloud for web-based demonstrations. Because the synthetic data (`/data` folder) is already committed to the repository, deployment is instantaneous.

1. Create a free account at [share.streamlit.io](https://share.streamlit.io/).
2. Click **"New app"** and authorize your GitHub account.
3. Select this repository (`sharayuwadghule/Supervise-SOC`) and the `main` branch.
4. **Main file path:** Enter `satsa/ui/app.py`.
5. **App URL:** Customize your URL (e.g., `sat-sa-demo`).
6. Click **Deploy!**

*Note: Streamlit Cloud will automatically read the `satsa/requirements.txt` file and install the necessary dependencies.*
