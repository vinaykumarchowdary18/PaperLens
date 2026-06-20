# PaperLens Backend — AI Detection + Plagiarism API

**A production-ready FastAPI backend for detecting AI-generated content and plagiarism in research papers.**

Built for Indian students and researchers. Plug in your API keys and go live in under 10 minutes.

---

## What's included

| File | Purpose |
|------|---------|
| `main.py` | FastAPI app entry point |
| `database.py` | SQLite schema — auto-creates on first run |
| `config.py` | All settings loaded from `.env` |
| `routers/auth.py` | Google OAuth login → JWT tokens |
| `routers/analysis.py` | Upload PDF/DOCX → AI + plagiarism detection |
| `routers/payment.py` | Cashfree credit purchases (UPI + cards) |
| `services/ai_detector.py` | 7-agent ensemble AI detector |
| `services/plagiarism.py` | 6-agent plagiarism checker |
| `utils/extractor.py` | PDF, DOCX, TXT text extraction |

---

## Quick start

### Windows
```
Double-click setup_windows.bat
```

### Mac / Linux
```bash
chmod +x setup_mac_linux.sh
./setup_mac_linux.sh
```

Both scripts will:
1. Check Python is installed
2. Create `.env` from the template on first run
3. Install all packages
4. Start the server at `http://localhost:8000`

API docs open at: **http://localhost:8000/docs**

---

## API keys you need

### Required for login
**Google OAuth** — https://console.cloud.google.com/apis/credentials
- Create Project → OAuth 2.0 Client ID → Web Application
- Redirect URI: `http://localhost:5173/auth/callback`
- Gives you: `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`

### Required for payments
**Cashfree** — https://merchant.cashfree.com
- Individual PAN accepted — no GST, no business registration
- KYC done in ~15 minutes
- Use TEST keys during development, LIVE keys for production
- Gives you: `CASHFREE_APP_ID` and `CASHFREE_SECRET_KEY`

### For AI detection (add as many as you can — they cover each other)

| Service | Free limit | Get key at |
|---------|-----------|------------|
| GPTZero | 10,000 words/day | https://gptzero.me/api |
| ZeroGPT | 10,000 chars/day | https://zerogpt.com/api |
| Sapling | 50 req/day | https://sapling.ai/user/settings |
| Writer.com | 100 req/day | https://dev.writer.com |

Even with **zero API keys**, 3 local analysis agents (burstiness, perplexity, lexical pattern) always run — you'll always get a result.

### For plagiarism (all free, zero setup)
OpenAlex, Semantic Scholar, CrossRef, Wikipedia — no keys needed, already configured.

**CORE.ac.uk** (optional) — free key at https://core.ac.uk/services/api — gives higher rate limits.

---

## How the detection works

### AI Detection — 7-agent ensemble
```
Tier 1 (API)     → GPTZero + Sapling + ZeroGPT + Writer.com
Tier 2 (Local)   → Burstiness + Perplexity analysis
Tier 3 (Local)   → Lexical pattern fingerprinting
                          ↓
              Weighted voting orchestrator
                          ↓
           Disagreement check (if API vs local gap > 0.35)
                          ↓
        Final score + confidence + per-agent breakdown
```

If one API hits its rate limit, the others keep running. The system never returns an error — it degrades gracefully to lower confidence.

### Plagiarism — 6-agent ensemble
```
Academic DBs     → Semantic Scholar (200M papers)
                   OpenAlex (240M works)
                   CrossRef (150M DOIs)
                   CORE (30M open access)
Web              → Wikipedia API
Local            → Self-plagiarism detector (repeated paragraphs)
                          ↓
         Cross-validate: matches from 2+ sources get boosted
                          ↓
              Final score + top matching sources
```

---

## Endpoints

### Auth
| Method | Route | Description |
|--------|-------|-------------|
| GET | `/auth/google/login` | Redirect to Google |
| POST | `/auth/google/callback` | Code → JWT token |
| GET | `/auth/me` | Current user profile |

### Analysis
| Method | Route | Description |
|--------|-------|-------------|
| POST | `/analysis/upload` | Upload PDF/DOCX/TXT |
| GET | `/analysis/{id}` | Poll for results |
| GET | `/analysis/history` | Past analyses |

### Payment
| Method | Route | Description |
|--------|-------|-------------|
| GET | `/payment/packages` | Credit packages |
| POST | `/payment/create-order` | Create Cashfree order |
| POST | `/payment/verify` | Verify and credit account |
| POST | `/payment/webhook` | Cashfree auto-webhook |
| GET | `/payment/transactions` | Transaction history |

**Auth header:** `Authorization: Bearer <JWT_TOKEN>`

---

## Credit system

| Event | Credits |
|-------|---------|
| New signup | 1 free credit |
| First document | Free |
| Each document after | 1 credit |

### Packages
| Package | Price | Credits |
|---------|-------|---------|
| Starter | ₹25 | 1 |
| Standard | ₹150 | 5 |
| Pro | ₹500 | 20 |

---

## Production deployment

### Railway (recommended — free tier available)
```bash
npm install -g @railway/cli
railway login
railway init
railway up
```
Add your `.env` variables in the Railway dashboard.

### Render
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Add env vars in the Render dashboard

### Switch to production
1. In `.env`: set `APP_ENV=production`
2. Update `FRONTEND_URL` and `BACKEND_URL` to your real domain
3. Switch Cashfree to LIVE keys
4. Add production redirect URI in Google Cloud Console

---

## Tech stack

- **FastAPI** — async Python web framework
- **aiosqlite** — async SQLite (zero infra, swap to Postgres for scale)
- **pdfplumber** — PDF text extraction
- **python-jose** — JWT auth
- **httpx** — async HTTP for API calls
- **slowapi** — rate limiting
- **Cashfree** — payments via plain REST (no heavy SDK)

---

## Support

This is a clean, well-commented codebase. Every service file has a full architecture comment at the top explaining what it does and why.

For questions, open the file — the answer is usually in the docstring.

