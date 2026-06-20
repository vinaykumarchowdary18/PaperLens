#!/bin/bash
echo ""
echo "============================================"
echo "  PaperLens Backend - Mac/Linux Setup"
echo "============================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 not found. Install from https://python.org"
    exit 1
fi
echo "[OK] Python found: $(python3 --version)"

# Create .env if missing
if [ ! -f .env ]; then
    echo "[SETUP] Creating .env from template..."
    cp .env.example .env
    echo "[ACTION NEEDED] Open .env and fill in your API keys, then run this script again."
    exit 0
fi
echo "[OK] .env file found"

# Install
echo "[INSTALL] Installing packages..."
pip3 install -r requirements.txt --quiet
echo "[OK] Packages installed"

echo ""
echo "============================================"
echo "  Starting PaperLens API on port 8000"
echo "  API Docs: http://localhost:8000/docs"
echo "  Press CTRL+C to stop"
echo "============================================"
echo ""
python3 main.py
