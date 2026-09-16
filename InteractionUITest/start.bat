@echo off
setlocal
cd /d "%~dp0"
if defined UI_TEST_PYTHON (
    "%UI_TEST_PYTHON%" main.py
) else (
    python main.py
)
if errorlevel 1 (
    echo.
    echo Launch failed. Use a Python environment with PyQt5 installed.
    echo Run: python -m pip install -r requirements.txt
    echo Or set UI_TEST_PYTHON to your Python executable path.
    pause
)
endlocal
