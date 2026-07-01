# RupeeRadar — Phase-Wise Implementation Plan

This document is the execution plan for building RupeeRadar, derived from [architecture.md](./architecture.md) and [context.md](./context.md). Work is organized into **three phases**, each delivering a demoable increment. Tasks within a phase are ordered by dependency; parallel work is noted where possible.

---

## Summary

| Phase | Name | Goal | Est. Duration |
|-------|------|------|---------------|
| **1** | Vertical Slice (MVP) | Upload → clean → categorize → metrics → basic dashboard | 1–2 weeks |
| **2** | Intelligence & Detection | LLM fallback, recurring detection, richer charts, user overrides | 1 week |
| **3** | Polish & Deliverable | Multi-format support, export, privacy, **Railway (API) + Vercel (frontend)** | 1 week |

**Total estimate:** 3–4 weeks for a solo developer working part-time; 1.5–2 weeks full-time.

---

## Cross-Cutting Setup (Before Phase 1)

Complete once before writing feature code.

| # | Task | Details | Owner |
|---|------|---------|-------|
| 0.1 | Initialize repo structure | `backend/`, `frontend/`, `docs/`, `.gitignore`, `README.md` | — |
| 0.2 | Backend scaffold | FastAPI app, `uvicorn`, folder layout per architecture §15 | — |
| 0.3 | Frontend scaffold | Vite + React + TypeScript + Tailwind | — |
| 0.4 | Docker Compose (optional) | API + frontend dev services; SQLite volume | — |
| 0.5 | Environment config | `.env.example`: `DATABASE_URL`, `CORS_ORIGINS`, `MAX_UPLOAD_SIZE_MB` | — |
| 0.6 | Lock conventions | Debits = negative amounts; ISO dates; category enum | — |
| 0.7 | Sample fixtures | 1 anonymized HDFC-style CSV with messy UPI strings (50–100 rows) | — |

**Exit criteria:** `docker compose up` or equivalent starts API and frontend; health check returns 200.

---

## Phase 1 — Vertical Slice (MVP)

### Goal

Prove the full pipeline end-to-end with one bank CSV format, rule-based categorization, basic metrics, a transaction table, and three template insights. No LLM, no recurring detection yet.

### Requirements Covered

- Accept bank statement data
- Extract and clean transactions
- Categorize (rules only)
- Calculate income, spend, savings, top categories
- Simple dashboard
- ≥ 3 insights (template-based)

---

### Milestone 1.1 — Backend Foundation

**Target:** Days 1–2

| # | Task | Files / Modules | Depends On |
|---|------|-----------------|------------|
| 1.1.1 | Database models | `models/upload_session.py`, `models/transaction.py`, `models/analysis_result.py` | 0.2 |
| 1.1.2 | SQLAlchemy setup + migrations (or `create_all` for prototype) | `db.py` | 1.1.1 |
| 1.1.3 | Pydantic schemas for API request/response | `schemas/` | 1.1.1 |
| 1.1.4 | Category enum | `models/enums.py` — 10 categories from architecture §3.3 | 0.6 |
| 1.1.5 | Pipeline orchestrator skeleton | `services/pipeline.py` — chains stages, updates session status | 1.1.2 |

**Acceptance criteria:**
- [ ] Tables created on startup
- [ ] `UploadSession` status transitions: `pending` → `parsing` → `processing` → `ready` | `failed`

---

### Milestone 1.2 — Ingestion & Parsing

**Target:** Days 2–3

| # | Task | Files / Modules | Depends On |
|---|------|-----------------|------------|
| 1.2.1 | `StatementParser` protocol | `parsers/base.py` | — |
| 1.2.2 | HDFC CSV parser (first bank) | `parsers/hdfc.py` | 1.2.1 |
| 1.2.3 | Parser registry — pick first matching parser | `parsers/registry.py` | 1.2.2 |
| 1.2.4 | Upload validation | Max size, empty file, unsupported extension | 1.2.3 |
| 1.2.5 | `POST /api/v1/upload` | `api/routes/upload.py` — save file, run pipeline, return `session_id` | 1.1.5, 1.2.3 |
| 1.2.6 | `GET /api/v1/sessions/{id}` | Return status, filename, row count, errors | 1.1.5 |

**Acceptance criteria:**
- [ ] Upload fixture CSV → session status `ready`
- [ ] Transactions persisted with `description_raw`, `date`, `amount`, `type`
- [ ] Parse warnings returned for skipped/ambiguous rows
- [ ] Raw upload file deleted after successful parse

**Tests:**
- [ ] Unit: HDFC parser on fixture
- [ ] Integration: upload endpoint → DB rows

---

### Milestone 1.3 — Cleaning & Normalization

**Target:** Day 3

| # | Task | Files / Modules | Depends On |
|---|------|-----------------|------------|
| 1.3.1 | Description cleaner | `pipeline/cleaner.py` — strip UPI noise, normalize whitespace | 1.2.5 |
| 1.3.2 | Merchant dictionary (initial set) | `data/merchants.json` — Swiggy, Zomato, Amazon, Netflix, etc. | 1.3.1 |
| 1.3.3 | Payment mode detection | UPI, NEFT, IMPS, card keywords in `cleaner.py` | 1.3.1 |
| 1.3.4 | Date normalization | Handle `DD-MM-YYYY`, `DD/MM/YY` → ISO | 1.3.1 |
| 1.3.5 | Duplicate detection | Hash `(date, amount, description_raw)` within session | 1.3.1 |

**Acceptance criteria:**
- [ ] `UPI/DR/123456/SWIGGY` → `description_clean` = `SWIGGY`
- [ ] All dates stored as `YYYY-MM-DD`
- [ ] Duplicates flagged or deduplicated with warning

**Tests:**
- [ ] Unit: 10+ messy description fixtures

---

### Milestone 1.4 — Rule-Based Categorization

**Target:** Days 4–5

| # | Task | Files / Modules | Depends On |
|---|------|-----------------|------------|
| 1.4.1 | Rule engine | `pipeline/categorizer.py` — keyword/pattern → category | 1.3.1 |
| 1.4.2 | Merchant → category map | Extend `data/merchants.json` with categories | 1.4.1 |
| 1.4.3 | Confidence scoring | Rules = 0.9+, dictionary = 0.8+, unmatched = 0.0 → `Other` | 1.4.1 |
| 1.4.4 | Wire categorizer into pipeline | Update transactions before metrics step | 1.1.5 |

**Rule coverage (minimum):**

| Patterns | Category |
|----------|----------|
| SALARY, PAYROLL | Salary |
| SWIGGY, ZOMATO, DOMINOS | Food |
| UBER, OLA, IRCTC | Travel |
| AMAZON, FLIPKART, MYNTRA | Shopping |
| BESCOM, AIRTEL, JIO | Bills |
| NETFLIX, SPOTIFY | Subscriptions |
| HOME LOAN, EMI | EMI |
| RENT, NOBROKER | Rent |
| ZERODHA, GROWW, SIP | Investments |

**Acceptance criteria:**
- [ ] ≥ 70% of fixture transactions categorized (non-Other) with rules alone
- [ ] Every transaction has `category` and `category_confidence`

**Tests:**
- [ ] Unit: rule matching per category
- [ ] Golden file: expected categories for fixture CSV

---

### Milestone 1.5 — Metrics & Template Insights

**Target:** Day 5

| # | Task | Files / Modules | Depends On |
|---|------|-----------------|------------|
| 1.5.1 | Metrics calculator | `pipeline/metrics.py` | 1.4.4 |
| 1.5.2 | Persist `AnalysisResult` | Store metrics JSON on session complete | 1.5.1 |
| 1.5.3 | Template insight generator | `pipeline/insights.py` — ≥ 3 insights with real ₹ amounts | 1.5.1 |
| 1.5.4 | `GET /api/v1/sessions/{id}/analytics` | Return metrics + top categories + biggest txn | 1.5.2 |
| 1.5.5 | `GET /api/v1/sessions/{id}/insights` | Return insight strings | 1.5.3 |
| 1.5.6 | `GET /api/v1/sessions/{id}/transactions` | Paginated, sortable by date/amount/category | 1.4.4 |

**Metrics to implement:**

- Total income, total spend, savings, savings rate
- Top categories (debit totals, sorted)
- Biggest debit transaction

**Template insights (minimum 3):**

1. Largest spending category with amount
2. Biggest single transaction with merchant and date
3. Total spend for the statement period

**Acceptance criteria:**
- [ ] Analytics endpoint returns correct totals for fixture (manual verification)
- [ ] Insights cite actual amounts from transactions

**Tests:**
- [ ] Unit: metrics on known transaction set

---

### Milestone 1.6 — Frontend MVP

**Target:** Days 6–8

| # | Task | Files / Modules | Depends On |
|---|------|-----------------|------------|
| 1.6.1 | API client | `frontend/src/api/client.ts` | 1.2.5 |
| 1.6.2 | Landing page + `FileUpload` | Drag-drop, file type hint, upload progress | 1.6.1 |
| 1.6.3 | `ProcessingStatus` | Loading state while session processes | 1.6.2 |
| 1.6.4 | Analysis page route | `/analysis/:sessionId` | 1.6.2 |
| 1.6.5 | `SummaryCards` | Income, spend, savings, savings rate | 1.5.4 |
| 1.6.6 | `TransactionTable` | Date, raw + clean description, amount, category badge | 1.5.6 |
| 1.6.7 | `InsightCards` | Display ≥ 3 insights | 1.5.5 |
| 1.6.8 | Basic styling | Tailwind layout, INR formatting (`₹1,23,456`) | — |
| 1.6.9 | Error states | Unsupported file, empty statement, API errors | 1.6.2 |

**Acceptance criteria:**
- [ ] User can upload fixture CSV and land on dashboard
- [ ] Summary cards show correct numbers
- [ ] Transaction table shows cleaned descriptions alongside raw
- [ ] Three insight cards visible
- [ ] Works on desktop Chrome; readable on mobile

---

### Phase 1 — Exit Criteria (Demo Checklist)

- [ ] End-to-end: upload HDFC CSV → dashboard in < 30 seconds
- [ ] Cleaned transaction data visible in table
- [ ] Categorized expenses with category badges
- [ ] Income, spend, savings displayed
- [ ] Top categories identifiable from data (table or simple list)
- [ ] ≥ 3 personalized insights with real amounts
- [ ] README with local run instructions

### Phase 1 — Out of Scope

- LLM categorization
- Recurring detection
- Charts (beyond summary numbers)
- PDF export
- Multi-bank support
- Authentication

---

## Phase 2 — Intelligence & Detection

### Goal

Improve categorization accuracy with LLM fallback, detect recurring payments, add visual charts, and let users override categories.

### Requirements Covered

- Recurring subscriptions / EMIs detection
- Better categorization for messy descriptions
- Monthly spend visibility
- Improved UX (charts, overrides)

---

### Milestone 2.1 — LLM Categorization Fallback

**Target:** Days 1–2

| # | Task | Files / Modules | Depends On |
|---|------|-----------------|------------|
| 2.1.1 | LLM client abstraction | `services/llm.py` — provider-agnostic interface | Phase 1 |
| 2.1.2 | Batch categorization prompt | Send unmatched txns (id, description_clean, amount, type) | 2.1.1 |
| 2.1.3 | Structured JSON response parsing | Validate category enum + confidence | 2.1.2 |
| 2.1.4 | Integrate into categorizer | Rules → dictionary → LLM → Other | 1.4.1 |
| 2.1.5 | Graceful degradation | If no API key or LLM fails, skip to `Other` | 2.1.4 |
| 2.1.6 | `LLM_API_KEY` env var | Document in `.env.example` | 2.1.1 |

**Acceptance criteria:**
- [ ] Unmatched transactions sent to LLM in batches of 20–50
- [ ] No account numbers or full raw statements sent to LLM
- [ ] Pipeline completes without LLM when key absent
- [ ] Categorization accuracy improves on messy fixture (target ≥ 85% non-Other)

**Tests:**
- [ ] Unit: LLM response parser with mock JSON
- [ ] Integration: pipeline with LLM mocked

---

### Milestone 2.2 — Recurring Payment Detection

**Target:** Days 2–3

| # | Task | Files / Modules | Depends On |
|---|------|-----------------|------------|
| 2.2.1 | `RecurringGroup` model | `models/recurring_group.py` | 1.1.1 |
| 2.2.2 | Recurring detector | `pipeline/recurring.py` | 1.4.4 |
| 2.2.3 | Fuzzy grouping | Token overlap or Levenshtein on `description_clean` | 2.2.2 |
| 2.2.4 | Cadence detection | Monthly (~28–32 days), amount ±5% tolerance | 2.2.2 |
| 2.2.5 | Category overrides | EMI, SIP, Subscriptions patterns | 2.2.2 |
| 2.2.6 | Update transactions | Set `is_recurring`, `recurring_group_id` | 2.2.2 |
| 2.2.7 | `GET /api/v1/sessions/{id}/recurring` | List recurring groups | 2.2.2 |
| 2.2.8 | Recurring total metric | Add to analytics | 2.2.2 |

**Acceptance criteria:**
- [ ] Detects Netflix/Spotify-style monthly debits in fixture
- [ ] Detects EMI with consistent amount and ~monthly interval
- [ ] Groups have label, typical_amount, frequency, confidence
- [ ] Recurring insight template: "N recurring payments totalling ₹Z/month"

**Tests:**
- [ ] Unit: synthetic recurring series (3+ monthly txns)
- [ ] Unit: non-recurring similar merchants not grouped falsely

---

### Milestone 2.3 — Charts & Enhanced Dashboard

**Target:** Days 3–4

| # | Task | Files / Modules | Depends On |
|---|------|-----------------|------------|
| 2.3.1 | Monthly spend aggregation | Add `monthly_spend[]` to analytics | 1.5.1 |
| 2.3.2 | `CategoryChart` | Pie or bar chart — Recharts | 2.3.1 |
| 2.3.3 | Monthly trend chart | Line/bar by month | 2.3.1 |
| 2.3.4 | `RecurringList` component | Cards for each recurring group | 2.2.7 |
| 2.3.5 | Dashboard tabs/sections | Summary · Transactions · Recurring · Insights | 1.6.4 |
| 2.3.6 | "This month" filter | Based on latest txn date in statement | 2.3.1 |

**Acceptance criteria:**
- [ ] Category breakdown chart renders with correct proportions
- [ ] Monthly trend shows spend per calendar month
- [ ] Recurring panel lists detected payments with amounts

---

### Milestone 2.4 — Category Override

**Target:** Day 4–5

| # | Task | Files / Modules | Depends On |
|---|------|-----------------|------------|
| 2.4.1 | `PATCH /api/v1/sessions/{id}/transactions/{txn_id}` | Update category, set confidence = 1.0 | 1.5.6 |
| 2.4.2 | Recompute metrics on override | Invalidate and refresh `AnalysisResult` | 2.4.1 |
| 2.4.3 | Category dropdown in table | Inline edit per row | 2.4.1 |
| 2.4.4 | Visual indicator | User-overridden badge | 2.4.3 |

**Acceptance criteria:**
- [ ] User changes category → analytics and charts update
- [ ] Override persisted in DB

---

### Phase 2 — Exit Criteria (Demo Checklist)

- [ ] LLM categorizes previously `Other` transactions (when API key set)
- [ ] Recurring subscriptions/EMIs shown in dedicated panel
- [ ] Category pie chart and monthly trend chart on dashboard
- [ ] User can override a category and see updated totals
- [ ] ≥ 4 insights including recurring template (if recurring detected)

### Phase 2 — Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| LLM latency slows upload | Batch calls; show progress; async processing if > 5s |
| LLM cost | Only send unmatched txns; cache merchant mappings |
| False recurring positives | Require ≥ 2 occurrences + interval check; show confidence |

---

## Phase 3 — Polish & Deliverable

### Goal

Ship an evaluation-ready prototype: second format support, exportable report, privacy controls, and **split production deployment** — **FastAPI backend on [Railway](https://railway.app/)**, **React frontend on [Vercel](https://vercel.com/)**.

> **Status legend:** ✅ Done · ⬜ Pending

### Requirements Covered

- Shareable report / visual summary
- Privacy-conscious data handling
- **Public demo URL** (Vercel) backed by a **hosted API** (Railway)
- Broader format support (within prototype scope)

### Deployment Architecture (Phase 3)

```
┌─────────────────────┐         HTTPS          ┌─────────────────────┐
│  Vercel (frontend)  │  ─── VITE_API_URL ──►  │  Railway (backend)  │
│  React + Vite SPA   │      /api/v1/*         │  FastAPI + uvicorn  │
└─────────────────────┘                        └──────────┬──────────┘
                                                          │
                                               ┌──────────▼──────────┐
                                               │  Railway PostgreSQL │
                                               │  (or SQLite volume) │
                                               └─────────────────────┘
```

| Layer | Platform | Repo path | Status |
|-------|----------|-----------|--------|
| **Frontend** | Vercel | `frontend/` | ✅ Build-ready (`npm run build` → `dist/`) |
| **Backend** | Railway | `backend/` | ✅ Dockerfile + `railway.toml` present |
| **Database** | Railway | — | ⬜ PostgreSQL add-on to provision on deploy |

**Cross-service env wiring:**

| Variable | Where | Value | Status |
|----------|-------|-------|--------|
| `VITE_API_URL` | Vercel env | `https://<railway-domain>.up.railway.app` | ⬜ Set after Railway deploy |
| `CORS_ORIGINS` | Railway env | `https://<app>.vercel.app` | ⬜ Set after Vercel deploy |
| `DATABASE_URL` | Railway env | Postgres connection string from Railway plugin | ⬜ Auto-injected by Railway PostgreSQL add-on |
| `GROQ_API_KEY` | Railway env | Secret — never committed | ⬜ Copy from `.env` |
| `GROQ_RPM/TPM/RPD/TPD` | Railway env | `30` / `1000` / `12000` / `100000` | ⬜ Match free-tier limits |
| `SESSION_TTL_HOURS` | Railway env | `72` | ⬜ Set explicitly (default in config) |
| `MAX_UPLOAD_SIZE_MB` | Railway env | `10` | ⬜ Set explicitly |

---

### Milestone 3.1 — Multi-Format Parsing ✅ DONE

All parsing work is complete and tested.

| # | Task | Files | Status |
|---|------|-------|--------|
| 3.1.1 | ICICI CSV parser | `parsers/icici.py` | ✅ |
| 3.1.2 | Generic CSV column mapper | `parsers/generic.py` — auto-detects date/desc/amount columns | ✅ |
| 3.1.3 | Excel support (.xlsx) | `parsers/excel_loader.py` + `openpyxl` in `requirements.txt` | ✅ |
| 3.1.4 | Parser registry | `parsers/registry.py` — HDFC → ICICI → Generic → Excel priority | ✅ |
| 3.1.5 | Upload UI format hints | `FileUpload.tsx` — lists HDFC · ICICI · generic CSV · Excel; CSV template link | ✅ |
| 3.1.6 | Test fixtures | `tests/fixtures/icici_sample.csv`, `generic_columns.csv`, `hdfc_with_emi.csv` | ✅ |

**Acceptance criteria:**
- [x] HDFC, ICICI, generic CSV, and Excel all parse via the same upload endpoint
- [x] Clear error message + template link for unsupported files
- [x] `test_parsers_phase3.py` — ICICI and generic fixture tests pass

---

### Milestone 3.2 — Report Export ✅ DONE

| # | Task | Files | Status |
|---|------|-------|--------|
| 3.2.1 | HTML report template | `app/templates/report.html` — summary, categories, insights, recurring | ✅ |
| 3.2.2 | Report service | `services/report.py` — `build_report_context`, `render_report_html`, `render_report_pdf` | ✅ |
| 3.2.3 | `GET /api/v1/sessions/{id}/report` | `api/routes/sessions.py` — `?format=html` or `?format=pdf` | ✅ |
| 3.2.4 | PDF generation | `weasyprint` in `requirements.txt`; graceful 503 if unavailable | ✅ |
| 3.2.5 | `ReportExport` component | `frontend/src/components/ReportExport.tsx` — Download PDF + Print/Share buttons | ✅ |

**Acceptance criteria:**
- [x] HTML report renders with real ₹ amounts, category table, insights, recurring list
- [x] PDF download triggered from UI; falls back to print view if WeasyPrint unavailable
- [x] `test_session_lifecycle.py::test_report_html_endpoint` passes

---

### Milestone 3.3 — Privacy & Session Lifecycle ✅ DONE

| # | Task | Files | Status |
|---|------|-------|--------|
| 3.3.1 | `DELETE /api/v1/sessions/{id}` | `api/routes/sessions.py` — cascade deletes transactions, groups, analysis (204) | ✅ |
| 3.3.2 | Session TTL — lazy expiry check | `services/session_lifecycle.py` — `is_session_expired()` checked on every read | ✅ |
| 3.3.3 | `SESSION_TTL_HOURS` env var | `config.py` default 72 h; set via env on Railway | ✅ |
| 3.3.4 | Privacy notice in UI | `HomePage.tsx` — data retention copy, no third-party storage statement | ✅ |
| 3.3.5 | Raw upload files never persisted | `services/pipeline.py` — temp file deleted in `finally` block | ✅ |

**Acceptance criteria:**
- [x] DELETE returns 204 and second call returns 404
- [x] Expired sessions return 404 on any read endpoint
- [x] Raw upload file gone after parse; confirmed in pipeline code
- [x] `test_session_lifecycle.py` — delete and expiry tests pass

---

### Milestone 3.4 — LLM-Enhanced Narrative Insights ✅ DONE

| # | Task | Files | Status |
|---|------|-------|--------|
| 3.4.1 | Narrative insight prompt | `services/llm.py` — `NARRATIVE_SYSTEM_PROMPT`, `_build_narrative_payload` (aggregate metrics only, no PII) | ✅ |
| 3.4.2 | Merge with template insights | `pipeline/insights.py` — templates first, LLM appends 2–3 observations | ✅ |
| 3.4.3 | Graceful fallback | `generate_narrative_insights` returns `[]` if LLM disabled or daily budget low | ✅ |
| 3.4.4 | AI badge in `InsightCards` | `InsightCards.tsx` — purple "AI" badge on `source === "ai"` insights | ✅ |
| 3.4.5 | Rate-limit guard for narrative | `llm.py` — checks `remaining_daily_tokens` before narrative call; 15 s deadline | ✅ |

**Acceptance criteria:**
- [x] ≥ 5 insights when LLM enabled (template + AI); 3 template-only when disabled
- [x] No PII sent — payload contains only aggregated totals and category names
- [x] `test_insights_phase3.py` and `test_narrative_insights.py` pass

---

### Milestone 3.5 — Deployment (Railway + Vercel) ⬜ PENDING

This is the only remaining milestone. All code is production-ready; the steps below are one-time dashboard/CLI operations.

#### 3.5.1 — Backend → Railway

**What's already in the repo:**

| File | Purpose |
|------|---------|
| `backend/Dockerfile` | Multi-stage build; `python:3.12-slim`; WeasyPrint system deps; `$PORT` support |
| `backend/railway.toml` | `builder = "DOCKERFILE"`; health check at `/api/v1/health`; restart on failure |
| `backend/requirements.txt` | All deps including `psycopg2-binary` for Postgres |
| `backend/app/config.py` | `normalize_database_url` converts `postgres://` → `postgresql://` (Railway quirk) |
| `backend/app/db.py` | `_connect_args_for` adds `sslmode=require` for Postgres automatically |

**Step-by-step Railway deploy:**

1. Push repo to GitHub (if not already).
2. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**.
3. Select the repo. Railway auto-detects `backend/railway.toml`.
   - If prompted for root directory: set it to `backend/`.
4. Click **Add Plugin** → **PostgreSQL**. Railway injects `DATABASE_URL` automatically.
5. In **Variables**, add all secrets (never commit these):

   ```
   GROQ_API_KEY=<your-key>
   GROQ_MODEL=llama-3.3-70b-versatile
   GROQ_RPM=30
   GROQ_TPM=1000
   GROQ_RPD=12000
   GROQ_TPD=100000
   GROQ_MAX_TOKENS_PER_REQUEST=350
   GROQ_MAX_TXNS_PER_UPLOAD=15
   GROQ_UPLOAD_TIME_BUDGET_SEC=45
   GROQ_MAX_DESCRIPTION_CHARS=48
   CORS_ORIGINS=https://<your-vercel-app>.vercel.app
   SESSION_TTL_HOURS=72
   MAX_UPLOAD_SIZE_MB=10
   ```

6. Railway builds the Docker image and deploys. Wait for health check at `/api/v1/health` → `{"status":"ok"}`.
7. Note your Railway public domain: `https://<project>.up.railway.app`.

**Railway checklist:**
- [ ] PostgreSQL plugin provisioned; `DATABASE_URL` visible in Variables
- [ ] All env vars set (see table above)
- [ ] `GET https://<project>.up.railway.app/api/v1/health` returns `{"status":"ok","groq_configured":true}`
- [ ] `groq_limits.remaining_daily_tokens` visible in health response

#### 3.5.2 — Frontend → Vercel

**What's already in the repo:**

| File | Purpose |
|------|---------|
| `frontend/vercel.json` | SPA rewrite: all paths → `index.html` (required for `/analysis/:id`) |
| `frontend/vite.config.ts` | Standard Vite + React config; `VITE_API_URL` consumed via `import.meta.env` |
| `frontend/src/api/client.ts` | `API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000"` |

**Step-by-step Vercel deploy:**

1. Go to [vercel.com](https://vercel.com) → **Add New Project** → Import from GitHub.
2. Select the repo.
3. In **Configure Project**:
   - **Root Directory**: `frontend`
   - **Framework Preset**: Vite (auto-detected)
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. Under **Environment Variables**, add:
   ```
   VITE_API_URL=https://<your-project>.up.railway.app
   ```
   Set for **Production** and **Preview** environments.
5. Click **Deploy**. Vercel builds and publishes the SPA.
6. Note your Vercel URL: `https://<app>.vercel.app`.

**After Vercel deploy — update Railway CORS:**

Go back to Railway → Variables → update:
```
CORS_ORIGINS=https://<app>.vercel.app,https://<app>-*.vercel.app
```
The second entry covers preview deployments. Railway redeploys automatically.

**Vercel checklist:**
- [ ] Root Directory = `frontend`; Build Command = `npm run build`; Output = `dist`
- [ ] `VITE_API_URL` set to Railway domain (Production + Preview)
- [ ] `https://<app>.vercel.app` loads without blank page or 404
- [ ] Browser Network tab shows API calls going to Railway domain (no CORS errors)

#### 3.5.3 — Integration Verification

| # | Check | How to verify |
|---|-------|---------------|
| 3.5.3a | CORS headers correct | Open browser DevTools → Network → upload request → response has `Access-Control-Allow-Origin` |
| 3.5.3b | Full upload flow works | Upload `docs/sample-data/phase2_hdfc_priya_sharma.csv` on Vercel URL → dashboard loads |
| 3.5.3c | Recurring panel populated | Same upload → Recurring tab shows 8 groups |
| 3.5.3d | PDF export works on production | Click Download PDF → file downloads with real amounts |
| 3.5.3e | Delete session works | Click "Delete my data" → redirects to home, session 404 |
| 3.5.3f | README updated | `README.md` has live Vercel URL + Railway URL + local run instructions |

**README must include (⬜ pending):**
- Live demo URL (Vercel)
- API base URL (Railway)
- Local development instructions (`uvicorn` + `npm run dev`)
- Environment variable reference table
- Sample CSV files location (`docs/sample-data/`)

---

### Phase 3 — Exit Criteria (Final Deliverable)

Aligned with [context.md](./context.md) expected output:

- [x] Cleaned transaction data — `description_clean` + payment mode in every transaction
- [x] Categorized expenses — rules (0.92) → dictionary (0.85) → LLM (0.78) → Other
- [x] Recurring payment detection — monthly/weekly cadence, confidence scoring, dedicated UI tab
- [x] Spend summary dashboard with charts — category bar chart + monthly trend with highlight
- [x] ≥ 3 personalized financial insights (≥ 5 with LLM) — template + AI narrative with badge
- [x] Downloadable / shareable report — HTML + PDF via WeasyPrint; print view
- [x] Privacy — TTL 72 h, DELETE endpoint, raw files never persisted, privacy notice in UI
- [x] Multi-format support — HDFC CSV, ICICI CSV, generic CSV, Excel (.xlsx)
- [ ] **Deployed: Vercel frontend URL + Railway API URL documented in README** ⬜
- [ ] **Production upload works end-to-end (Vercel → Railway → PostgreSQL)** ⬜

---

### Phase 3 — Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| WeasyPrint system deps missing on Railway | Dockerfile already installs `libpango`, `libpangocairo`, `libgdk-pixbuf2.0`; test `/report?format=pdf` after deploy |
| Railway free tier sleeps on inactivity | Cold start adds 5–30 s to first request; mention in README; upgrade to hobby tier for demos |
| SQLite on Railway ephemeral disk | Use PostgreSQL add-on (step 3.5.1 above); `psycopg2-binary` is in `requirements.txt` |
| Vercel preview URLs not in `CORS_ORIGINS` | Add wildcard `https://<app>-*.vercel.app` to Railway `CORS_ORIGINS` |
| `VITE_API_URL` baked at build time | Must be set in Vercel env *before* deploying; changing it requires a redeploy |

---

## Testing Plan by Phase

| Phase | Unit | Integration | E2E | Manual |
|-------|------|-------------|-----|--------|
| 1 | Parser, cleaner, rules, metrics | Upload → DB | — | Upload walkthrough |
| 2 | Recurring, LLM parser | Full pipeline + LLM mock | — | Override + charts |
| 3 | Report renderer | Multi-format parse | Upload → export | **Vercel + Railway** demo, mobile |

### Fixture Requirements (build incrementally)

| Fixture | Phase | Contents |
|---------|-------|----------|
| `hdfc_messy.csv` | 1 | UPI strings, salary credit, food, shopping |
| `hdfc_with_emi.csv` | 2 | Monthly EMI + Netflix + rent |
| `icici_sample.csv` | 3 | Second bank format |
| `generic_columns.csv` | 3 | Non-standard headers for mapper |

---

## Dependency Graph

```
Phase 1
  0.x Setup
    → 1.1 Models/DB
      → 1.2 Parse/Upload
        → 1.3 Clean
          → 1.4 Categorize (rules)
            → 1.5 Metrics/Insights
              → 1.6 Frontend MVP

Phase 2 (requires Phase 1 complete)
  1.4 Categorize → 2.1 LLM fallback
  1.5 Metrics    → 2.2 Recurring
  1.6 Frontend   → 2.3 Charts + 2.4 Override

Phase 3 (requires Phase 2 complete)
  2.x            → 3.1 Multi-format
  2.3 Dashboard  → 3.2 Report export
  1.1 Models     → 3.3 Privacy/TTL
  2.1 LLM        → 3.4 Narrative insights
  All            → 3.5 Deploy (Railway API → Vercel SPA)
```

---

## Requirement Traceability

| context.md requirement | Phase | Milestone |
|------------------------|-------|-----------|
| Accept bank statement data | 1 | 1.2 |
| Extract/clean transactions | 1 | 1.2, 1.3 |
| Categorize expenses | 1, 2 | 1.4, 2.1 |
| Detect recurring payments | 2 | 2.2 |
| Calculate metrics | 1, 2 | 1.5, 2.2 |
| Human-readable insights | 1, 2, 3 | 1.5, 2.2, 3.4 |
| Dashboard / report | 1, 2, 3 | 1.6, 2.3, 3.2 |
| Privacy-conscious handling | 1, 3 | 1.2 (delete raw file), 3.3 |
| Prototype over all banks | 1, 3 | 1.2 (one bank), 3.1 (second + generic) |
| Deployed deliverable | 3 | 3.5 (Railway backend, Vercel frontend) |

---

## Optional Stretch Goals (Post Phase 3)

Not required for evaluation; implement only if time permits.

| Item | Value |
|------|-------|
| PDF bank statement parsing | Broader input support |
| Background job queue (Celery/RQ) | Large file handling |
| User authentication | Multi-user persistence |
| Category learning from overrides | Improve rules over time |
| Excel export of cleaned data | Power-user feature |
| Hindi/regional merchant names | Better India coverage |

---

## Suggested Weekly Schedule (Solo, Full-Time)

| Week | Focus | Deliverable |
|------|-------|-------------|
| Week 1 | Setup + Phase 1 (1.1–1.5) | API pipeline works via curl/Postman |
| Week 2 | Phase 1 (1.6) + Phase 2 start | Working MVP dashboard |
| Week 3 | Phase 2 complete + Phase 3 | Charts, recurring, LLM, export |
| Week 4 | Phase 3 deploy + testing | **Vercel demo URL**, Railway API, final README |

---

*This plan follows the modular monolith architecture in [architecture.md](./architecture.md). Adjust timelines based on team size; backend pipeline (1.1–1.5) and frontend (1.6) can partially overlap once API contracts are defined.*
