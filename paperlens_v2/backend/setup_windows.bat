@echo off
title PaperLens Backend Setup
color 0A

echo.
echo  ============================================
echo   PaperLens Backend - Windows Setup
echo  ============================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found.
    echo  Download from: https://www.python.org/downloads/
    echo  Make sure to check "Add Python to PATH" during install.
    pause
    exit /b 1
)

echo  [OK] Python found
echo.

REM Check if .env exists
if not exist .env (
    echo  [SETUP] Creating .env from template...
    copy .env.example .env >nul
    echo  [ACTION NEEDED] Open .env in Notepad and fill in your API keys.
    echo  Then run this script again.
    echo.
    notepad .env
    pause
    exit /b 0
)

echo  [OK] .env file found
echo.

REM Install dependencies
echo  [INSTALL] Installing Python packages...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo  [ERROR] Package installation failed. Check your internet connection.
    pause
    exit /b 1
)

echo  [OK] All packages installed
echo.

REM Start server
echo  ============================================
echo   Starting PaperLens API on port 8000
echo   API Docs: http://localhost:8000/docs
echo   Press CTRL+C to stop
echo  ============================================
echo.

python main.py
pause
