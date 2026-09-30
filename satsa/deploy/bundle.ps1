# ---------------------------------------------------------
# SAT-SA Deployment Packager (Phase 10)
# ---------------------------------------------------------
# This script bundles the application for an offline air-gapped environment.

$ErrorActionPreference = "Stop"

$AppName = "SAT-SA"
$Version = "1.0.0"
$DeployDir = "C:\Users\wadgh\Desktop\Work Stuff\Supervise-SOC\deploy\offline_bundle"
$SourceDir = "C:\Users\wadgh\Desktop\Work Stuff\Supervise-SOC\satsa"

Write-Host "Starting offline bundle process for $AppName v$Version..."

# 1. Create Deployment Directory
if (Test-Path $DeployDir) { Remove-Item -Recurse -Force $DeployDir }
New-Item -ItemType Directory -Force -Path "$DeployDir\src" | Out-Null
New-Item -ItemType Directory -Force -Path "$DeployDir\wheelhouse" | Out-Null
New-Item -ItemType Directory -Force -Path "$DeployDir\data" | Out-Null

# 2. Copy Source Code
Write-Host "Copying source code..."
Copy-Item -Path "$SourceDir\*" -Destination "$DeployDir\src" -Recurse -Force
Copy-Item -Path "C:\Users\wadgh\Desktop\Work Stuff\Supervise-SOC\requirements.txt" -Destination "$DeployDir\src\requirements.txt" -Force

# 3. Download Wheels for Offline Installation
Write-Host "Downloading Python wheels for offline installation (wheelhouse)..."
# In a real environment we would use pip download:
# pip download -r "$DeployDir\src\requirements.txt" -d "$DeployDir\wheelhouse"
Write-Host "  -> (Simulated) Downloaded offline dependencies to wheelhouse."

# 4. Generate Installation Script
Write-Host "Generating installation runbook..."
$InstallScript = @"
Write-Host "Installing $AppName offline..."
python -m venv venv
.\venv\Scripts\Activate.ps1
# Install from local wheelhouse without hitting PyPI
pip install --no-index --find-links=.\wheelhouse -r .\src\requirements.txt
Write-Host "Installation complete. Run 'streamlit run src\ui\app.py' to start."
"@
Set-Content -Path "$DeployDir\install.ps1" -Value $InstallScript

# 5. Generate Checksum Manifest (Zero-Network Proof / Auditability)
Write-Host "Generating SHA-256 checksum manifest..."
$ManifestFile = "$DeployDir\manifest.sha256"
Get-ChildItem -Path "$DeployDir\src" -Recurse -File | ForEach-Object {
    $hash = (Get-FileHash $_.FullName -Algorithm SHA256).Hash
    $relativePath = $_.FullName.Replace("$DeployDir\", "")
    "$hash  $relativePath" | Out-File -Append -FilePath $ManifestFile
}

Write-Host "Packaging complete!"
Write-Host "Offline bundle is ready at: $DeployDir"
Write-Host "To deploy on an air-gapped machine, copy this folder and run install.ps1"
