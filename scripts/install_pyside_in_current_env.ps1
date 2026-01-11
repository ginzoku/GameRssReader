# Install PySide6 into the currently active Python environment (no venv activation)
Write-Host "Installing PySide6 into current Python"
python -m pip install --upgrade pip
python -m pip install PySide6
Write-Host "PySide6 install attempted; verify by running: python -c \"from PySide6 import QtCore; print('OK')\""