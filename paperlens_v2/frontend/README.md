# PaperLens Frontend

React + Vite frontend for the PaperLens AI detection and plagiarism checking platform.

## Setup

```bash
npm install
cp .env.example .env
npm run dev
```

Frontend runs at: http://localhost:5173

Backend must be running at: http://localhost:8000 (or set VITE_API_URL in .env)

## Pages

| Route | Description |
|-------|-------------|
| `/` | Landing / marketing page |
| `/login` | Google OAuth sign-in |
| `/auth/callback` | OAuth callback handler |
| `/dashboard` | Upload + history |
| `/results/:id` | Analysis results with agent breakdown |
| `/credits` | Buy credits via Cashfree |
| `/payment/success` | Payment confirmation |

## Production build

```bash
npm run build
```

Outputs to `dist/`. Deploy to Vercel, Netlify, or Firebase Hosting.

For Vercel:
```bash
npx vercel --prod
```

Set `VITE_API_URL` environment variable in your hosting dashboard to point to your deployed backend.

## Tech stack

- React 18
- React Router v6
- Axios
- Vite
- Google Fonts (Inter + JetBrains Mono)
- Cashfree JS SDK (loaded dynamically at payment time)
