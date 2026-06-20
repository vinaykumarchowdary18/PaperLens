#!/bin/bash
# ════════════════════════════════════════════
#  PaperLens Backend — Quick Start
# ════════════════════════════════════════════

set -e

echo "🔍 PaperLens API starting..."

# Check .env exists
if [ ! -f .env ]; then
  echo "⚠️  No .env file found. Copying from .env.example..."
  cp .env.example .env
  echo "✏️  Edit .env and add your API keys, then run this script again."
  exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt --quiet

# Start server
echo "🚀 Starting FastAPI server on http://localhost:8000"
echo "📖 API docs: http://localhost:8000/docs"
python main.py
