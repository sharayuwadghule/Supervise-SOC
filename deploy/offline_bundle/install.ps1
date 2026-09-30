Write-Host "Installing SAT-SA offline..."
python -m venv venv
.\venv\Scripts\Activate.ps1
# Install from local wheelhouse without hitting PyPI
pip install --no-index --find-links=.\wheelhouse -r .\src\requirements.txt
Write-Host "Installation complete. Run 'streamlit run src\ui\app.py' to start."
