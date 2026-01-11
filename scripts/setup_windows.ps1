# PowerShell setup script for GameRssReader
# Usage: Run in PowerShell as Administrator or as current user:
#   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
#   .\scripts\setup_windows.ps1

param(
    [string]$VenvPath = ".venv"
)

Write-Host "Creating virtual environment at: $VenvPath"
python -m venv $VenvPath
& "$VenvPath\Scripts\Activate.ps1"
Write-Host "Upgrading pip/setuptools/wheel"
python -m pip install --upgrade pip setuptools wheel
Write-Host "Installing required packages from requirements.txt"
python -m pip install -r requirements.txt

Write-Host "If you want to prefer CEF (cefpython3), ensure your Python version is compatible (recommended: 3.9)."
Write-Host "To run the Tk app: python main.py"
Write-Host "To run the Qt app: python qt_app.py (requires PySide6)"
Write-Host "Setup complete. Activated venv remains active in this session."