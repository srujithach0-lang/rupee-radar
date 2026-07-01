# RupeeRadar

AI-powered personal finance assistant that analyzes Indian bank statements and surfaces spending insights.

## Stack

| Layer | Technology |
|-------|------------|
| Backend | Python, FastAPI, SQLAlchemy, SQLite / PostgreSQL |
| Frontend | React, TypeScript, Vite, Tailwind CSS |
| LLM | [Groq](https://groq.com/) (`llama-3.3-70b-versatile`) |
| Deploy | [Railway](https://railway.app/) (API) + [Vercel](https://vercel.com/) (frontend) |

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+
- Docker & Docker Compose (optional)

### 1. Environment

```bash
cp .env.example .env
# Optional: set GROQ_API_KEY for LLM categorization and narrative insights
```

### 2. Docker Compose (recommended)

```bash
docker compose up --build
```

- API: http://localhost:8000
- Frontend: http://localhost:5173
- Health: http://localhost:8000/api/v1/health

### 3. Local development (without Docker)

**Backend:**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
mkdir -p data
uvicorn app.main:app --reload --port 8000
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

Set `VITE_API_URL=http://localhost:8000` in `frontend/.env.local` if the API is not on the default.

## Supported Statement Formats

| Format | Notes |
|--------|-------|
| HDFC CSV | Native export with `Narration`, `Withdrawal Amt.`, `Deposit Amt.` |
| ICICI CSV | `Transaction Remarks`, `Withdrawal/Deposit Amount (INR)` |
| Generic CSV | Auto-detects `Date`, `Description`, `Debit`/`Credit` columns |
| Excel (.xlsx) | First sheet converted to CSV internally |

Download a starter template: [docs/sample-statement-template.csv](docs/sample-statement-template.csv)

## Features

- Upload → parse → clean → categorize (rules + LLM fallback)
- Recurring payment detection (subscriptions, EMIs)
- Dashboard with category charts, monthly trends, insights
- Category overrides with live metric refresh
- PDF / HTML report export
- Privacy: 72-hour TTL, delete endpoint, no persistent raw files

## Project Structure

```
rupee-radar/
├── backend/          # FastAPI API + processing pipeline
├── frontend/         # React dashboard
├── docs/             # Context, architecture, implementation plan
└── docker-compose.yml
```

## Conventions

- **Amounts:** debits are negative, credits positive
- **Dates:** ISO 8601 (`YYYY-MM-DD`)
- **Categories:** Food, Travel, Shopping, Bills, EMI, Subscriptions, Salary, Rent, Investments, Other

## Sample Data

| Fixture | Description |
|---------|-------------|
| `backend/tests/fixtures/hdfc_messy.csv` | HDFC with messy UPI strings |
| `backend/tests/fixtures/hdfc_with_emi.csv` | EMI + Netflix + rent |
| `backend/tests/fixtures/icici_sample.csv` | ICICI bank format |
| `backend/tests/fixtures/generic_columns.csv` | Generic column headers |

## Deployment

### Architecture

```
Vercel (React SPA)  ──VITE_API_URL──►  Railway (FastAPI)
                                              │
                                    Railway PostgreSQL
```

### Backend on Railway

1. Create a new Railway project from this repo; set **Root Directory** = `backend/`
2. Add the **PostgreSQL** plugin (recommended)
3. Set environment variables:

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | From Railway Postgres plugin |
| `CORS_ORIGINS` | `https://your-app.vercel.app` (+ preview URLs) |
| `GROQ_API_KEY` | Your Groq API key (secret) |
| `SESSION_TTL_HOURS` | `72` |
| `MAX_UPLOAD_SIZE_MB` | `10` |

4. Deploy; confirm `GET /api/v1/health` returns 200

### Frontend on Vercel

1. Import repo; set **Root Directory** = `frontend/`
2. Framework: Vite; build: `npm run build`; output: `dist`
3. Set `VITE_API_URL` to your Railway API URL (Production + Preview)
4. `vercel.json` handles SPA routing for `/analysis/:id`

After deploy, update Railway `CORS_ORIGINS` with your Vercel production URL.

### Demo URLs

| Service | URL |
|---------|-----|
| Frontend | _Set after Vercel deploy_ |
| API | _Set after Railway deploy_ |

## Documentation

- [context.md](docs/context.md) — project overview
- [architecture.md](docs/architecture.md) — system design
- [implementation-plan.md](docs/implementation-plan.md) — phased build plan
- [edge-cases.md](docs/edge-cases.md) — corner cases catalog

## Phase Status

- [x] **Phase 0** — Repo scaffold, health check, Groq config, sample fixture
- [x] **Phase 1** — Upload, parse, categorize, dashboard MVP
- [x] **Phase 2** — Groq categorization, recurring detection, charts, overrides
- [x] **Phase 3** — Multi-format, export, privacy, Railway + Vercel deploy configs

## License

MIT
