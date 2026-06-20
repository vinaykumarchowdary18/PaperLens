# PaperLens — Complete Package

AI Detection + Plagiarism Checking SaaS — Full Stack (Backend + Frontend)

## Structure

```
paperlens_COMPLETE/
├── backend/    → FastAPI Python backend
├── frontend/   → React + Vite frontend
└── README.md   → This file
```

## Quick Start

### 1. Start the backend
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Fill in .env with your API keys
python main.py
```
Backend runs at: http://localhost:8000
API docs at: http://localhost:8000/docs

### 2. Start the frontend
```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```
Frontend runs at: http://localhost:5173

## What's included

### Backend (FastAPI)
- 7-agent AI detection ensemble (GPTZero, Sapling, ZeroGPT, Writer.com + 3 local agents)
- 6-agent plagiarism detection (Semantic Scholar, OpenAlex, CrossRef, CORE, Wikipedia, self-check)
- Google OAuth login + JWT auth
- Cashfree payments (UPI, Cards, NetBanking — individual PAN accepted, no GST needed)
- Credit system (1 free on signup, then ₹25–500 packages)
- SQLite database (swap to Postgres in one line)
- Rate limiting, CORS, background tasks, async throughout

### Frontend (React + Vite)
- Landing page with pricing
- Google OAuth sign-in
- File upload (PDF, DOCX, TXT)
- Live polling results page with score rings and agent breakdown
- Credits purchase with Cashfree SDK
- Transaction and analysis history
- Fully responsive, dark theme

## API Keys needed

| Key | Where to get | Free tier |
|-----|-------------|-----------|
| GOOGLE_CLIENT_ID + SECRET | console.cloud.google.com | Free |
| GPTZERO_API_KEY | gptzero.me/api | 10,000 words/day |
| SAPLING_API_KEY | sapling.ai/user/settings | 50 req/day |
| ZEROGPT_API_KEY | zerogpt.com/api | 10,000 chars/day |
| WRITER_API_KEY | dev.writer.com | 100 req/day |
| CASHFREE_APP_ID + SECRET | merchant.cashfree.com | Test keys instant |

Plagiarism sources (OpenAlex, Semantic Scholar, CrossRef, Wikipedia) need no keys.

## Support
All files are fully commented. Read the file — the answer is usually in the docstring.
