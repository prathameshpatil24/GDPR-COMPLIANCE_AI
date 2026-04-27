# GDPR AI — Testing Guide

> Complete testing checklist for verifying the GDPR AI system (v1 violation analysis + v2 compliance assessment). Run these checks layer by layer — if anything breaks at a layer, fix it before moving to the next.

---

## Layer 1 — Smoke Test (Does it run?)

**Time: 2 min | Cost: ~$0.10**

```bash
cd ~/Desktop/GDPR-COMPLIANCE_AI
git checkout develop
git status

# Version check
uv run gdpr-check version

# v1 — Violation Analysis
uv run gdpr-check analyze "A company sends marketing emails to users without getting consent"

# v2 — Compliance Assessment
uv run gdpr-check assess "I am building a SaaS that collects email addresses from a web form and sends weekly newsletters via Mailchimp. Data stored in PostgreSQL on AWS eu-central-1."

# Start API server (leave running, open new terminal for Layer 2)
uv run gdpr-check serve
```

**Expected:**
- `version` prints the current version
- `analyze` returns a violation report with cited GDPR articles (Art. 6, 7 at minimum)
- `assess` returns a compliance assessment with findings and risk level
- `serve` starts FastAPI on http://localhost:8000

---

## Layer 2 — API Endpoints

**Time: 5 min | Cost: ~$0.30**

> Requires the server to be running from Layer 1 (`uv run gdpr-check serve`)

```bash
# Health check
curl http://localhost:8000/health

# v1 — Violation Analysis via API
curl -X POST http://localhost:8000/api/v1/analyze/violation \
  -H "Content-Type: application/json" \
  -d '{"scenario": "A German hospital accidentally emails patient test results to the wrong patient."}'

# v2 — Compliance Assessment via API (freetext)
curl -X POST http://localhost:8000/api/v1/analyze/compliance \
  -H "Content-Type: application/json" \
  -d '{"system_description": "I am building a mobile fitness app that tracks user location, heart rate, and workout history. Data is stored on AWS eu-central-1. I share anonymized analytics with a third-party research partner in the US."}'

# List projects
curl http://localhost:8000/api/v1/projects

# Generate documents from a compliance analysis
# (replace PASTE_ANALYSIS_ID with the analysis_id from the compliance response above)
curl -X POST http://localhost:8000/api/v1/documents/generate \
  -H "Content-Type: application/json" \
  -d '{"analysis_id": "PASTE_ANALYSIS_ID", "doc_types": ["dpia", "ropa", "checklist", "consent_flow", "retention_policy"]}'

# Retrieve a specific analysis
# (replace PASTE_ANALYSIS_ID with the id from any previous response)
curl http://localhost:8000/api/v1/analyze/PASTE_ANALYSIS_ID

# Retrieve a specific document
# (replace PASTE_DOCUMENT_ID with a document id from the generate response)
curl http://localhost:8000/api/v1/documents/PASTE_DOCUMENT_ID
```

**Check each response for:**
- Valid JSON returned
- GDPR articles cited are real (not hallucinated)
- v2 findings have correct status (compliant / at_risk / non_compliant / insufficient_info)
- Generated DPIA has all required sections
- Generated RoPA has Article 30 fields

---

## Layer 3 — Automated Tests

**Time: 2 min | Cost: $0 (mocked LLM)**

```bash
# Run all unit + integration tests
uv run pytest tests/ -v

# Quick summary — check total count and pass rate
uv run pytest tests/ -v --tb=short | tail -10

# Run specific test files if needed
uv run pytest tests/test_db_repository.py -v
uv run pytest tests/test_eval_harness.py -v
```

**Expected:** All tests pass (47+ from Phases K–P plus eval harness tests)

---

## Layer 4 — Gold Test Evaluation

**Time: 10-30 min | Cost: ~$3-5**

```bash
# Step 1: Dry run — validates all 50 scenarios parse correctly, NO LLM calls
uv run python tests/run_eval.py --dry-run

# Step 2: Smoke test — 1 scenario from each mode
uv run python tests/run_eval.py --scenarios SC-V-001,SC-C-001

# Step 3: Run v1 scenarios only
uv run python tests/run_eval.py --mode violation_analysis

# Step 4: Run v2 scenarios only
uv run python tests/run_eval.py --mode compliance_assessment

# Step 5: Full run — all 50 scenarios, save results
uv run python tests/run_eval.py --output gold/eval_results.json

# Step 6: Check against baseline (after baseline is saved)
uv run python tests/run_eval.py --check-baseline

# Optional filters
uv run python tests/run_eval.py --difficulty hard
uv run python tests/run_eval.py --category consent
```

**What to look for:**
- Article recall above 80% for both modes
- No scenarios with 0% recall
- v2 finding coverage above 75%
- Investigate any "fail" scenarios

---

## Layer 5 — Document Quality Spot Check

**Time: 10 min | Cost: $0 (read existing outputs)**

Pick 2-3 interesting v2 scenarios and inspect the generated documents:

```bash
# Run a detailed compliance assessment
uv run gdpr-check assess "I am building an AI recruitment tool that screens CVs using machine learning. It processes candidate names, work history, education, and sometimes photos. The model scores candidates and auto-rejects those below a threshold. Data stored in PostgreSQL, hosted on Hetzner in Germany."

# Run a healthcare scenario
uv run gdpr-check assess "I am building a telemedicine platform where patients can upload medical reports, chat with doctors, and receive prescriptions. We store health records in PostgreSQL on AWS eu-central-1. We use Twilio for video calls and Stripe for payments."

# Run a children's data scenario
uv run gdpr-check assess "I am building an educational app for children aged 8-14. It tracks learning progress, quiz scores, and time spent per topic. Parents create accounts for their kids. Data stored on Google Cloud in Belgium."
```

**Check each output for:**
- ⚠️ Disclaimer present at the top of every generated document
- All sections filled (no empty sections)
- Articles cited are real and relevant to the scenario
- Technical recommendations are specific, not generic
- ⚠️ warnings appear where data was missing from the description
- AI recruitment → MUST flag: Art. 22, DPIA required, AI Act high-risk, discrimination risk
- Healthcare → MUST flag: Art. 9 (special category), DPIA, breach notification, encryption
- Children → MUST flag: Art. 8 (children's consent), parental consent, data minimization

---

## Layer 6 — Edge Cases

**Time: 5 min | Cost: ~$0.50**

```bash
# Empty input
uv run gdpr-check assess ""

# Very short / vague input
uv run gdpr-check assess "a website"

# No data collection at all
uv run gdpr-check assess "I am building a calculator app that runs entirely offline with no data collection whatsoever"

# Extremely detailed multi-concern input
uv run gdpr-check assess "I am building a multi-tenant B2B healthcare CRM that processes patient names, diagnoses, treatment plans, insurance IDs, and genetic test results. Data is stored in PostgreSQL on AWS us-east-1 and replicated to eu-west-1. We use Stripe for billing, SendGrid for emails, Segment for analytics, and share de-identified data with three research universities in the US, UK, and Japan. We process data from children aged 12+ with parental consent. Our AI model predicts treatment outcomes and flags high-risk patients automatically."

# v2 with structured JSON input (if supported)
uv run gdpr-check assess --file test_system.json
```

**Expected behavior:**
- Empty / very short → returns mostly `insufficient_info` findings or asks for more detail
- No data collection → returns mostly compliant, may flag need for documentation anyway
- Very detailed → catches everything: special categories, cross-border, children's data, automated decisions, multiple processors, AI Act

---

## Layer 7 — Observability & Persistence

**Time: 2 min | Cost: $0**

```bash
# Check query log stats (after running some analyses)
uv run gdpr-check stats
uv run gdpr-check history

# Check SQLite database directly
sqlite3 data/app.db ".tables"
sqlite3 data/app.db "SELECT id, mode, created_at FROM analyses ORDER BY created_at DESC LIMIT 5;"
sqlite3 data/app.db "SELECT id, doc_type, created_at FROM documents ORDER BY created_at DESC LIMIT 5;"
sqlite3 data/app.db "SELECT COUNT(*) FROM analyses;"
sqlite3 data/app.db "SELECT COUNT(*) FROM documents;"
sqlite3 data/app.db "SELECT COUNT(*) FROM projects;"

# Attach feedback to a query (use query ID from history)
uv run gdpr-check feedback PASTE_QUERY_ID --thumbs up
uv run gdpr-check feedback PASTE_QUERY_ID --thumbs down
```

**Expected:**
- `stats` shows aggregate query counts, avg latency, avg cost
- `history` shows recent queries with timestamps
- SQLite tables exist and have data
- Analyses are linked to projects, documents linked to analyses

---

## Layer 8 — Code Quality

**Time: 1 min | Cost: $0**

```bash
# Lint check
uv run ruff check src/ tests/

# Type checking (if configured)
uv run mypy src/gdpr_ai/ --ignore-missing-imports

# Format check
uv run ruff format --check src/ tests/
```

**Expected:** Clean or near-clean output.

---

## Summary Table

| Layer | What | Time | Cost | Pass Criteria |
|-------|------|------|------|---------------|
| 1 | Smoke test | 2 min | ~$0.10 | CLI commands return valid output |
| 2 | API endpoints | 5 min | ~$0.30 | All endpoints return valid JSON |
| 3 | Automated tests | 2 min | $0 | All pytest tests pass |
| 4 | Gold evaluation | 10-30 min | ~$3-5 | Article recall > 80%, no fails |
| 5 | Document spot check | 10 min | $0 | All sections present, correct articles |
| 6 | Edge cases | 5 min | ~$0.50 | No crashes, appropriate responses |
| 7 | Observability | 2 min | $0 | Data persisted in SQLite |
| 8 | Code quality | 1 min | $0 | Ruff clean |

**Total: ~35-55 min | ~$4-6 in API costs**

---

## When to Run This

- **After completing Phase Q** — full run, all 8 layers
- **After any pipeline change** — Layers 1, 3, 4
- **After any API change** — Layers 1, 2, 3
- **After any prompt change** — Layers 1, 4, 5
- **Quick sanity check** — Layers 1, 3 only (4 min, $0.10)