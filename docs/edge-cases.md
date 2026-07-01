# RupeeRadar — Edge Cases & Corner Case Catalogue

This document catalogues known corner cases, boundary conditions, and failure scenarios across every layer of the RupeeRadar pipeline. Each entry identifies where the case surfaces, the expected system behaviour, and any test or guard that should exist.

---

## 1. File Upload & Ingestion

### 1.1 File Validation

| # | Edge Case | Expected Behaviour | Risk if Missed |
|---|-----------|-------------------|----------------|
| 1.1.1 | Empty file (0 bytes) | Reject with 422; session marked `failed`; message: "No transactions found" | Crashes parser on `read()` |
| 1.1.2 | File exactly at the 10 MB limit | Accept and process normally | Off-by-one rejection |
| 1.1.3 | File 1 byte above the 10 MB limit | Reject with 413 before writing to disk | Large file stored unnecessarily |
| 1.1.4 | Unsupported extension (`.pdf`, `.txt`, `.json`) | Reject with 400; surface format hint and link to sample template | Silent parse failure |
| 1.1.5 | File with no extension | Reject with 400 | `Path.suffix` returns `""`, not in `ALLOWED_EXTENSIONS` |
| 1.1.6 | Password-protected Excel / encrypted CSV | Parser raises exception → session `failed`; user-friendly error shown | Unhandled exception bubbles to 500 |
| 1.1.7 | CSV file renamed to `.xlsx` (MIME mismatch) | `openpyxl` will fail to open; surface clear error rather than crash | Stack trace exposed to user |
| 1.1.8 | File upload interrupted mid-stream | Content length mismatch or truncated content; session `failed` | Partial rows silently parsed |
| 1.1.9 | Duplicate upload of the same file in the same session | Should be idempotent or warn; new session created per upload | Double-counting transactions |
| 1.1.10 | Filename with special characters or Unicode | `Path(filename).suffix` must still work; filename sanitized before saving temp file | Directory traversal or filesystem error |

---

### 1.2 HDFC Parser

| # | Edge Case | Expected Behaviour |
|---|-----------|-------------------|
| 1.2.1 | CSV with BOM (`\ufeff`) at start | `utf-8-sig` decoding strips BOM correctly; first header recognised |
| 1.2.2 | Headers with trailing/leading whitespace (e.g. `" Date "`) | `field_map` strips whitespace before lookup; no missing-column error |
| 1.2.3 | Both `Withdrawal Amt.` and `Deposit Amt.` empty for a row | Row skipped with warning `"Row N: no valid amount"` |
| 1.2.4 | Both `Withdrawal Amt.` and `Deposit Amt.` populated (bank error) | Debit takes precedence (withdrawal > 0 branch fires first); warning logged |
| 1.2.5 | Amount string uses Indian comma formatting (`"1,23,456.78"`) | `parse_amount` strips commas before `float()` conversion |
| 1.2.6 | Amount string contains currency symbol (e.g. `"₹450.00"`) | `parse_amount` strips non-numeric prefix characters |
| 1.2.7 | `Narration` field contains only digits or a single character | `SKIP_PATTERNS` may not match; row parsed with a near-empty description |
| 1.2.8 | Date in unsupported format (e.g. `"01 Jun 2025"`, `"Jun-01-25"`) | `parse_date` returns `None`; row skipped with warning |
| 1.2.9 | `Closing Balance` column absent | `balance` set to `None`; no crash (optional field check present) |
| 1.2.10 | Statement with only header row and no data rows | `ParseResult` contains no transactions and a warning; session `failed` |
| 1.2.11 | Extra/unknown columns in CSV | `DictReader` ignores them; `field_map` lookup still works |
| 1.2.12 | Rows that are summary/footer lines (e.g. `"Opening Balance"`) | `SKIP_PATTERNS` must match and skip these rows; warning emitted |
| 1.2.13 | Multi-line narration (quoted newline inside CSV cell) | Standard `csv.DictReader` handles quoted newlines; verify narration not truncated |

---

### 1.3 Generic CSV / Excel Parser

| # | Edge Case | Expected Behaviour |
|---|-----------|-------------------|
| 1.3.1 | No recognisable date column | Parser returns an error asking user to map columns |
| 1.3.2 | Amount split across debit/credit columns vs single signed column | Both layouts mapped; sign convention enforced |
| 1.3.3 | Merged cells in Excel (common in bank statements) | `openpyxl` unmerge or use first cell value; downstream does not receive `None` |
| 1.3.4 | Excel file with multiple sheets | First sheet (index 0) used by default; user informed if relevant data is on another sheet |
| 1.3.5 | Entirely blank rows or rows with only whitespace | Skipped silently; not counted as transactions |
| 1.3.6 | Column headers in a non-first row (bank statements with preamble rows) | Heuristic to detect header row; fallback prompts user to confirm column mapping |

---

## 2. Cleaning & Normalization

### 2.1 Description Cleaning

| # | Edge Case | Expected Behaviour |
|---|-----------|-------------------|
| 2.1.1 | Raw description is all numeric (e.g. reference number only) | `clean_description` strips non-alpha → result is `""` → falls back to `"UNKNOWN"` |
| 2.1.2 | Very long description (500+ characters) | Cleaned text is truncated or summarised; no performance issue in regex |
| 2.1.3 | Description with only special characters (`"---"`, `"..."`) | `NON_ALPHA` strips all → `""` → `"UNKNOWN"` |
| 2.1.4 | UPI string with no meaningful merchant segment (e.g. `"UPI/DR/123456/789012"`) | Slash splitting leaves only digits → `"UNKNOWN"` |
| 2.1.5 | Merchant name casing variation (`"swiggy"`, `"SWIGGY"`, `"Swiggy"`) | All lookups run on `.upper()`; case-insensitive match confirmed |
| 2.1.6 | Merchant alias substring collision (e.g. `"AMAZON"` matching `"AMAZON PRIME"`) | Longest-alias-first sort in `_load_merchant_categories()` prevents false short match |
| 2.1.7 | Description that matches multiple merchant aliases | First match wins (order dependent); document priority in `merchants.json` |
| 2.1.8 | Non-ASCII / Unicode characters in narration (Hindi merchant names) | `NON_ALPHA` strips them; potential loss of meaningful text — consider Unicode-safe cleaning |
| 2.1.9 | Whitespace-only description after cleaning | Collapses to `""` → `"UNKNOWN"` |
| 2.1.10 | Payment mode not detected (e.g. cash ATM withdrawal without ATM keyword) | `payment_mode` is `None`; category still assigned correctly |

---

### 2.2 Date Normalization

| # | Edge Case | Expected Behaviour |
|---|-----------|-------------------|
| 2.2.1 | Two-digit year ambiguity (`"01/06/25"` — 2025 or 1925?) | `%d/%m/%y` interprets 25 as 2025; document assumption |
| 2.2.2 | Day and month transposition (`"06/01/2025"` could be Jan 6 or Jun 1) | Parser is format-specific; HDFC uses `%d/%m/%Y`; wrong format → warning |
| 2.2.3 | Invalid calendar date (`"31/02/2025"`) | `datetime.strptime` raises `ValueError`; `parse_date` returns `None`; row skipped |
| 2.2.4 | Future dates (transaction dated after today) | Parsed without error; metrics period includes it; may indicate wrong year parsed |
| 2.2.5 | Dates spanning a year boundary (Dec → Jan) | Monthly aggregation (`txn.date[:7]`) works correctly; period_start/end span two years |
| 2.2.6 | All transactions on the same single date | `period_start == period_end`; savings rate and monthly trend still computed correctly |

---

### 2.3 Duplicate Detection

| # | Edge Case | Expected Behaviour |
|---|-----------|-------------------|
| 2.3.1 | Two genuinely identical transactions on the same day (e.g. two ₹500 Swiggy orders) | Hash collision — one is silently dropped; consider flagging instead of hard-deduplication |
| 2.3.2 | Duplicate across re-uploads (same session) | Hash seen in `seen` set; second occurrence skipped with warning |
| 2.3.3 | Same transaction with minor description variation (`"SWIGGY"` vs `"SWIGGY "`) | Different hashes → both kept; could lead to near-duplicates in table |
| 2.3.4 | Refund that exactly mirrors a debit (same amount, same merchant, same date) | Refund is a credit; hash includes amount as signed float — different hash, both kept |

---

## 3. Categorization

### 3.1 Rule Engine

| # | Edge Case | Expected Behaviour |
|---|-----------|-------------------|
| 3.1.1 | Description matches multiple rules (e.g. "SALARY AMAZON" matches Salary and Shopping) | First matching rule wins; rule order in `CATEGORY_RULES` must be intentional |
| 3.1.2 | Salary credit with unusual wording (`"NEFT CREDIT FROM EMPLOYER"`) | No rule matches → falls to LLM or `Other`; add common patterns to rules |
| 3.1.3 | EMI description without keyword ("HOME LOAN" missing, just bank ref) | Rule misses; LLM needed; user override is last resort |
| 3.1.4 | Credit transaction matching a debit rule (e.g. cashback labelled "AMAZON REFUND") | Categorized as `Shopping`; `CASHBACK` rule maps to Shopping intentionally per code |
| 3.1.5 | `REDEMPTION` keyword on a debit (withdrawal from investment) | Rule checks `type == credit`; debit with REDEMPTION falls through to Other or LLM |
| 3.1.6 | Pure digits or `"UNKNOWN"` description | No rule/dictionary matches; goes to LLM; LLM likely returns Other due to no signal |
| 3.1.7 | Category confidence threshold for `Other` | Transactions with `confidence == 0.0` and `category == Other` are the LLM input set |

---

### 3.2 LLM Categorization

| # | Edge Case | Expected Behaviour |
|---|-----------|-------------------|
| 3.2.1 | `GROQ_API_KEY` absent or blank | `groq_enabled` is False; `GroqLLMService.enabled` is False; unmatched stay as `Other` |
| 3.2.2 | LLM returns category not in the valid enum | `parse_categorization_response` coerces to `Other` |
| 3.2.3 | LLM returns confidence outside 0–1 (e.g. `1.5`) | Clamped with `max(0.0, min(1.0, confidence))` |
| 3.2.4 | LLM returns malformed JSON | `json.loads` raises; caught by `except Exception`; returns `None`; batch left as `Other` |
| 3.2.5 | LLM returns empty `transactions` array | `parse_categorization_response` returns `{}`; no updates applied |
| 3.2.6 | LLM returns IDs that don't match any unmatched txn | Orphan entries in `llm_results` ignored; original `Other` stays |
| 3.2.7 | All 500 transactions are unmatched (no rules hit) | Capped at `groq_max_txns_per_upload`; remaining stay `Other`; log warning emitted |
| 3.2.8 | Groq rate limit exceeded mid-upload (`429`) | `limiter.acquire` returns False; remaining batches skipped; partial categorization |
| 3.2.9 | Upload time budget (`groq_upload_time_budget_sec`) expires mid-batch | Loop breaks; already-processed batches kept; skipped txns stay `Other` |
| 3.2.10 | LLM categorizes a credit transaction as a debit category (e.g. Salary → Food) | Result stored as-is; no type-vs-category validation exists; could corrupt metrics |
| 3.2.11 | Very short description (1–2 chars) sent to LLM | LLM returns `Other` with low confidence; expected behavior |
| 3.2.12 | Description longer than `groq_max_description_chars` | Truncated with `"…"` before sending; original `description_clean` retained in DB |

---

## 4. Recurring Payment Detection

| # | Edge Case | Expected Behaviour |
|---|-----------|-------------------|
| 4.1 | Only 1 occurrence of a merchant | `len(cluster) < MIN_OCCURRENCES (2)` → not flagged as recurring |
| 4.2 | Exactly 2 occurrences with inconsistent interval (e.g. 5 days apart) | `_detect_frequency` returns `"unknown"` → group discarded |
| 4.3 | Amount varies by more than 5% (e.g. variable utility bill) | `_amounts_compatible` returns False → not flagged; could miss real recurring payments |
| 4.4 | Amount is `₹0` for all occurrences | `median == 0` in `_amounts_compatible` → returns False; group skipped |
| 4.5 | Two different merchants with similar descriptions (e.g. "HDFC BANK EMI" vs "HDFC LOAN EMI") | Similarity ≥ 0.55 → incorrectly merged into one group; label may be wrong |
| 4.6 | Monthly transaction on the 31st in months with 30 days (interval = 29 or 32 days) | Interval at boundary of `MONTHLY_MIN_DAYS (28)` – `MONTHLY_MAX_DAYS (32)`; should still detect |
| 4.7 | Recurring payment missed for one month then resumed | Gap month breaks cadence; second cluster of 2 may not reach monthly threshold |
| 4.8 | Salary credits grouped as recurring | Only debits are considered (`txn.amount < 0` filter); salary credits excluded correctly |
| 4.9 | EMI description changes slightly each month (bank appends counter) | Token similarity may drop below `SIMILARITY_THRESHOLD (0.55)` → missed grouping |
| 4.10 | Statement contains only 1 month of data | Not enough intervals to confirm monthly cadence reliably; low confidence expected |
| 4.11 | Weekly recurring (e.g. weekly SIP) | `_detect_frequency` handles 6–8 day intervals; confidence formula differs from monthly |
| 4.12 | Quarterly or annual payments (insurance, subscription) | Fall through as `"unknown"` frequency and are discarded; not surfaced in recurring panel |
| 4.13 | Large number of similar merchant names (100+ clusters) | Greedy O(n²) clustering may be slow; profile on 2,000-row statements |

---

## 5. Metrics & Aggregations

| # | Edge Case | Expected Behaviour |
|---|-----------|-------------------|
| 5.1 | Statement with zero income (all debits) | `savings_rate` is `None` (division by zero guard present); insight about savings omitted |
| 5.2 | Statement with zero spend (all credits) | `total_spend = 0`; `top_categories` is empty list; biggest_debit is `None` |
| 5.3 | Negative savings (spend > income) | `savings` is negative float; `savings_rate` is negative; insight reads as deficit |
| 5.4 | All transactions in `Other` category | `top_categories` list has one entry `Other`; insight correctly names it |
| 5.5 | Single transaction in the statement | `period_start == period_end`; `monthly_spend` has one entry; biggest debit is that transaction |
| 5.6 | Very large amounts (₹1 crore+) | `_inr()` formatter must handle large numbers; Indian comma grouping verified |
| 5.7 | Fractional paisa amounts (e.g. `₹0.50`) | `round(..., 2)` preserves paise; `_inr` formatter handles correctly |
| 5.8 | `txn.date` is `None` or unparseable for period calc | `date.fromisoformat()` raises; `dates` list comprehension skips `None` — verify guard exists |
| 5.9 | `monthly_spend` key derived from `txn.date[:7]` on a non-ISO date | If date was not normalized, slice produces wrong key; depends on cleaner running first |
| 5.10 | Recurring groups with `frequency != "monthly"` in `recurring_total_monthly` | Filter `g.frequency == "monthly"` ensures weekly groups excluded from monthly total |

---

## 6. Insight Generation

| # | Edge Case | Expected Behaviour |
|---|-----------|-------------------|
| 6.1 | No transactions at all | Returns single fallback insight: "Upload a statement with transactions to see personalized insights." |
| 6.2 | `savings_rate` is `None` (no income) | Savings insight skipped; no `NoneType` formatting error |
| 6.3 | `biggest_debit` is `None` (no debits) | Biggest-transaction insight skipped |
| 6.4 | `recurring_groups` is `None` or empty | Recurring insight skipped; no attribute error |
| 6.5 | LLM narrative returns insights referencing raw PII | `_build_narrative_payload` sends only aggregate metrics — PII cannot appear; validated |
| 6.6 | LLM narrative response has more than 3 items | `parse_narrative_response` slices to `[:3]` |
| 6.7 | LLM narrative returns insights with `₹0` amounts | Technically valid but misleading; no current guard |
| 6.8 | `_inr(0.0)` called on zero amounts | Returns `"₹0"`; verify formatter handles single-digit whole numbers |
| 6.9 | `period_start` or `period_end` is `None` | Fallback insight uses total spend only; no string formatting error |
| 6.10 | Indian number formatting: `_inr(100000)` | Should return `"₹1,00,000"` not `"₹100,000"` — verify grouping logic |

---

## 7. API Layer

### 7.1 Session Lifecycle

| # | Edge Case | Expected Behaviour |
|---|-----------|-------------------|
| 7.1.1 | `GET /sessions/{id}` with non-existent or expired session ID | Returns 404; no stack trace leaked |
| 7.1.2 | `GET /sessions/{id}` while status is still `processing` | Returns current status; client should poll |
| 7.1.3 | Session with status `failed` queried for transactions/analytics | Endpoints return 404 or empty data with error message; no 500 |
| 7.1.4 | `DELETE /sessions/{id}` twice | Second call returns 404; cascades are idempotent |
| 7.1.5 | Session TTL expired; session still in DB | Read endpoints return 404 or indicate expiry; background purge or lazy check |
| 7.1.6 | `PATCH /sessions/{id}/transactions/{txn_id}` with invalid category value | Returns 422 validation error; DB not updated |
| 7.1.7 | Concurrent uploads from the same (anonymous) origin | Each gets a unique `session_id`; no cross-session data leakage |

### 7.2 Pagination & Query Parameters

| # | Edge Case | Expected Behaviour |
|---|-----------|-------------------|
| 7.2.1 | `page=0` or `page=-1` on transaction list | Treated as page 1 or returns 422 |
| 7.2.2 | `page_size=0` | Returns 422 or defaults to minimum (e.g. 10) |
| 7.2.3 | `page` beyond total pages | Returns empty list with pagination metadata; not a 404 |
| 7.2.4 | Sort by unknown field | Returns 422; valid sort fields documented |

---

## 8. Data Storage & Integrity

| # | Edge Case | Expected Behaviour |
|---|-----------|-------------------|
| 8.1 | DB write fails after parsing (e.g. disk full) | Session marked `failed`; temp file still deleted in `finally` block |
| 8.2 | `AnalysisResult` metrics JSON exceeds column storage limit | Use `Text` / `JSON` column type; verify no truncation |
| 8.3 | `category_confidence` stored as float; rounding at DB layer | Stored as `Float`; display rounds to 2 decimal places |
| 8.4 | Session `expires_at` column is `NULL` (TTL not configured) | Session never auto-purged; behavior must be documented |
| 8.5 | `recurring_group_id` FK references a deleted group | Cascade delete or set null; no orphan foreign keys |
| 8.6 | `transaction_ids[]` stored as JSON array in `RecurringGroup` | Must be serialized/deserialized consistently; verify list type on read |
| 8.7 | SQLite → PostgreSQL migration: `JSON` vs `JSONB` column behaviour | Use SQLAlchemy `JSON` type for portability; test on both DB backends |

---

## 9. Frontend

| # | Edge Case | Expected Behaviour |
|---|-----------|-------------------|
| 9.1 | User uploads file, closes tab during processing | Session continues server-side; user returning with old URL can resume via session ID |
| 9.2 | `sessionId` from URL param is tampered with | Backend returns 404; frontend shows "Session not found" |
| 9.3 | Transaction table with 2,000+ rows | Pagination prevents DOM overload; virtual scrolling or server-side pagination required |
| 9.4 | Category override dropdown fails mid-edit (network error) | UI reverts to previous value; error toast shown |
| 9.5 | Chart renders with a single data point (1 month) | Recharts/Chart.js handles single-bar/point gracefully; no layout collapse |
| 9.6 | All transactions are `Other` category | Pie chart renders a single full-circle slice; label visible |
| 9.7 | INR formatting in UI: `₹1,23,456.78` vs `₹123,456.78` | Frontend uses Indian locale format consistently; verify `Intl.NumberFormat('en-IN')` |
| 9.8 | `description_clean` is `"UNKNOWN"` for many rows | Table shows `"UNKNOWN"` alongside raw description; user can use override |
| 9.9 | Report export triggered before analysis is ready | Export button disabled or shows loading state; no empty PDF generated |
| 9.10 | Mobile viewport: transaction table horizontal scroll | Table is horizontally scrollable or columns collapse on small screens |
| 9.11 | User submits a non-CSV/XLSX via drag-drop | Frontend validates extension before upload call; clear error message shown |

---

## 10. Security & Privacy

| # | Edge Case | Expected Behaviour |
|---|-----------|-------------------|
| 10.1 | Account number present in `description_raw` column | Never included in LLM payload (only `description_clean` sent); never logged |
| 10.2 | `GROQ_API_KEY` accidentally committed or exposed in response | Key read only from env var; never serialized in any API response or log |
| 10.3 | CORS request from unlisted origin | Request blocked with 403; `CORS_ORIGINS` must include Vercel preview URLs |
| 10.4 | Malicious filename (path traversal: `"../../etc/passwd.csv"`) | `Path(filename).suffix` used only for extension; temp file uses `uuid`-based name |
| 10.5 | Extremely large number of sessions from same IP (DoS) | No rate limiting in prototype; document as known gap; add in production |
| 10.6 | Session data accessed after TTL window | Returns 404 or empty; DB row deleted by purge job or lazy check |
| 10.7 | LLM prompt injection via crafted description (e.g. `"Ignore instructions and..."`) | LLM only returns structured JSON for categorization; narrative prompt uses aggregate metrics only; impact is limited but not zero |

---

## 11. Deployment-Specific (Railway + Vercel)

| # | Edge Case | Expected Behaviour |
|---|-----------|-------------------|
| 11.1 | `VITE_API_URL` set to wrong Railway domain | All API calls fail with network error; clear error in browser console |
| 11.2 | Railway PostgreSQL not provisioned; `DATABASE_URL` missing | FastAPI startup fails with DB connection error; Railway log shows cause |
| 11.3 | SQLite used on Railway with ephemeral filesystem | DB wiped on redeploy; data loss; use PostgreSQL or persistent volume |
| 11.4 | Vercel SPA routing: direct navigation to `/analysis/abc` | Without `vercel.json` rewrite rules, returns 404; rewrite to `index.html` required |
| 11.5 | Railway app sleeps (free tier) during demo | First request has cold-start latency (5–30s); inform evaluators or upgrade tier |
| 11.6 | `SESSION_TTL_HOURS` not set in Railway env | Defaults to env fallback; if `None`, sessions never purge; set explicit default |
| 11.7 | Vercel preview deployment uses production `VITE_API_URL` | Preview API calls hit production backend; scope env vars by environment in Vercel |

---

## 12. Test Fixture Gaps

The following scenarios should be covered by test fixtures but may currently be missing:

| # | Missing Fixture / Scenario |
|---|---------------------------|
| 12.1 | CSV with only 1 transaction (boundary for recurring detection) |
| 12.2 | CSV where every transaction is a credit (no debits) |
| 12.3 | CSV with extremely long narration fields (500+ chars) |
| 12.4 | CSV with mixed encoding (some rows UTF-8, some Latin-1) |
| 12.5 | ICICI statement format once `parsers/icici.py` is implemented |
| 12.6 | Statement spanning exactly 2 calendar months (tests monthly aggregation boundary) |
| 12.7 | Statement with salary + refund credits + investment debits (tests credit categorization) |
| 12.8 | Two transactions with identical `(date, amount, description_raw)` hash (tests dedup) |
| 12.9 | Statement with recurring payments that skip one month |
| 12.10 | LLM mock returning malformed JSON (tests graceful degradation) |

---

*Last updated: Phase 3 scope. Revisit after adding new bank parsers, PDF support, or authentication.*
