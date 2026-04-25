# Aminus MVP

Invoice screening demo with:
- Stage 1 security check (Factur-X extraction vs vision extraction)
- Stage 2 ERP reconciliation (Claude API)
- Persistence fallback to Postgres table

## Tech Stack

- Frontend: Next.js (`frontend`)
- Backend: FastAPI (`backend`)
- AI APIs: Anthropic (Claude), optional Google Gemini
- DB: Supabase Postgres (via `DATABASE_URL`)

## Required Environment Variables

Create `backend/.env`:

```env
ANTHROPIC_API_KEY=your_anthropic_key
DATABASE_URL=postgresql://...
```

Optional:

```env
GOOGLE_API_KEY=...
ANTHROPIC_MODEL=claude-sonnet-4-20250514
BACKEND_PUBLIC_URL=http://localhost:8000
INVOICES_TABLE=aminus_invoices
```

## One-command MVP Start

From project root:

```bash
./scripts/start_mvp.sh
```

This will:
- install backend/frontend dependencies
- build frontend
- start backend on `:8000`
- start frontend on `:3000`

Open:
- Frontend: `http://127.0.0.1:3000`
- Backend health: `http://127.0.0.1:8000/health`

## Stop MVP

```bash
./scripts/stop_mvp.sh
```

## Quick API Test

```bash
curl -X POST -F "file=@demo-data/test.pdf" http://127.0.0.1:8000/invoices/screen
```

Expected (working) signal in response:
- `"stage": "done"`
- `"reconciliation": {"status":"ok", ...}` (if Claude configured)

## Notes

- If `GOOGLE_API_KEY` is not configured, stage 1 uses a local stub for visual extraction.
- If storage is not configured, persistence falls back to DB insertion.
- If Claude model alias is unavailable, backend auto-falls back across available models.
