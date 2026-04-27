@echo off
REM Script pour relancer le serveur avec les fixes appliquées

cd /d C:\Users\User\OneDrive\Bureau\PFE_Master\back_EMP

echo =========================================
echo 🔧 Fixing NumPy Compatibility...
echo =========================================

pip uninstall -y numpy
pip install "numpy<2" --quiet

echo.
echo =========================================
echo 🚀 Starting Server...
echo =========================================
echo.

uvicorn app.main:app --reload --port 8000

pause
