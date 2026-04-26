# Phase 3.21 – Monitoring and Alerting Design

## 1. Overview

Observability is built in from v1, even in a local CLI context. Every query is logged with full context, latency, token usage, and cost. This data powers three things: debugging, cost control, and long-term quality tracking.

v1 observability is file-based and local. v2 adds hosted dashboards, external monitoring, and proactive alerting.

---

## 2. v1 Observability (Local CLI)

### 2.1 What Gets Logged

Every query produces one row in `data/gdpr_ai.db` (`query_log` table, schema in [16 – Knowledge Base Schema](16-knowledge-base-schema.md#7-sqlite-schema)) containing:

* Full scenario text
* Extracted entities and topic tags
* Retrieved chunk IDs
* Final report JSON
* Per-stage latency (extract, classify, retrieve, reason, validate)
* Per-call token counts (input/output, Haiku and Sonnet separately)
* Total cost in EUR
* Outcome status (ok, hallucination_retry_ok, failed)
* Any error details

### 2.2 Application Logs

Separate from the query log, Python's `logging` module writes operational logs:

* Pipeline stage start/end at INFO
* Retry attempts at WARNING
* Errors at ERROR
* Raw LLM responses at DEBUG (disabled by default)

Log destination: stderr by default; file (`data/gdpr_ai.log`) if `LOG_FILE=true`.

### 2.3 Local Inspection Tools

The CLI exposes commands for local observability:

```bash
gdpr-check stats            # today's query count, total cost, avg latency
gdpr-check stats --month    # monthly aggregates
gdpr-check logs show 10     # last 10 queries with summaries
gdpr-check logs show <id>   # detailed view of one query
gdpr-check logs clear       # wipe the local query log
```

### 2.4 Cost Tracking

Built into `llm/claude_client.py`:

* Every LLM call records input/output tokens
* Cost calculated from per-model rate constants
* Added to running total for the query
* Daily and monthly aggregates via the `cost_by_day` SQLite view

---

## 3. v1 Metrics to Watch

Even as a solo developer, the following metrics are reviewed regularly:

### 3.1 Quality Metrics

* Gold-set F1 (run weekly during development)
* Hallucination count (should always be 0)
* Retrieval recall@15 (should stay above 0.9)

### 3.2 Cost Metrics

* Average cost per query (target: under 0.05 EUR)
* Daily total cost (target: under 2 EUR at typical usage)
* Monthly total cost (target: under 10 EUR)

### 3.3 Latency Metrics

* P50 total latency (target: under 4s)
* P95 total latency (target: under 6s)
* Per-stage latency breakdown (to spot degradation)

### 3.4 Reliability Metrics

* Query success rate (target: 99%+)
* Hallucination retry count (should be rare)
* LLM API error count (inform when Anthropic has issues)

---

## 4. v1 Alert Conditions

No automated alerting in v1. The developer reviews metrics manually. Mental thresholds:

| Metric | Review threshold |
|--------|------------------|
| Daily cost | > 5 EUR (investigate cause) |
| F1 (gold set) | drops > 5% after a change |
| Hallucination count | any occurrence (investigate) |
| P95 latency | > 6s sustained (investigate) |

---

## 5. v2 Observability (Hosted Service)

### 5.1 Metrics Stack

```
┌──────────────────┐       ┌──────────────────┐      ┌──────────────────┐
│  FastAPI app     │──────►│   Prometheus     │─────►│     Grafana      │
│  (metrics)       │       │   (scrape)       │      │   (dashboards)   │
└──────────────────┘       └──────────────────┘      └──────────────────┘
         │                                                    │
         ▼                                                    │
┌──────────────────┐                                          │
│  SQLite query    │                                          │
│  log (detailed)  │◄─────────────────────────────────────────┘
└──────────────────┘                     (for deep dives)
```

### 5.2 Exported Prometheus Metrics

| Metric | Type | Labels |
|--------|------|--------|
| `gdpr_ai_queries_total` | Counter | endpoint, status |
| `gdpr_ai_query_latency_seconds` | Histogram | endpoint, stage |
| `gdpr_ai_tokens_total` | Counter | model, direction |
| `gdpr_ai_cost_eur_total` | Counter | model |
| `gdpr_ai_hallucinations_total` | Counter | stage |
| `gdpr_ai_retries_total` | Counter | stage, reason |
| `gdpr_ai_llm_errors_total` | Counter | model, error_type |
| `gdpr_ai_kb_chunks` | Gauge | source |

### 5.3 Dashboards

Grafana dashboards, all stored as code in `infra/grafana/`:

#### 5.3.1 Overview Dashboard

* Queries per minute (line chart)
* P50/P95/P99 latency (line chart)
* Error rate (gauge)
* Daily cost (counter + line chart)
* Top 10 most retrieved chunks (table)

#### 5.3.2 Cost Dashboard

* Cost per query (histogram)
* Cost by stage (stacked line)
* Daily spend vs budget (bar chart)
* Projected monthly spend (single stat)

#### 5.3.3 Quality Dashboard

* F1 over time (line chart)
* Hallucination count (counter)
* Retry rate (line chart)
* Nightly eval results (history)

#### 5.3.4 System Dashboard

* VPS CPU / memory / disk (stock node_exporter)
* ChromaDB size on disk
* SQLite size on disk
* Container uptime

---

## 6. v2 Alerting

### 6.1 Alerting Tool

Grafana alerts with email and Telegram delivery.

### 6.2 Alert Rules

| Alert | Trigger | Severity |
|-------|---------|----------|
| Service down | Health check fails 3 times in a row | Critical |
| Error rate spike | 5xx rate > 5% over 5 minutes | High |
| High latency | P95 > 10s for 10 minutes | Medium |
| Cost budget exceeded | Daily cost > 20 EUR | High |
| Hallucination detected | Any occurrence | Medium |
| Disk usage high | > 85% | Medium |
| Anthropic API down | LLM error rate > 20% | High |
| Dependency CVE | High/critical CVE in dependency | Medium |

### 6.3 Escalation

* Critical: immediate email + Telegram
* High: email within 5 minutes + Telegram within 15 minutes
* Medium: daily digest email

---

## 7. Tracing (v2)

### 7.1 OpenTelemetry Instrumentation

Every pipeline stage wrapped in an OTel span:

* `pipeline.extract`
* `pipeline.classify`
* `pipeline.retrieve`
* `pipeline.reason`
* `pipeline.validate`

Request-level trace covers the full query with parent span.

### 7.2 Trace Backend

For v2 simplicity, traces sampled at 10% and stored in Tempo (running alongside Grafana in the same Compose stack). Upgrade to a hosted tracing service only if debugging needs demand it.

---

## 8. Logging in v2

### 8.1 Structured JSON Logs

All logs in v2 are structured JSON, suitable for ingestion by any log aggregator.

```json
{
  "timestamp": "2026-04-25T14:30:00.123Z",
  "level": "INFO",
  "logger": "gdpr_ai.pipeline.orchestrator",
  "message": "Pipeline completed",
  "query_id": "uuid",
  "user_id": "user_123",
  "latency_ms": 4120,
  "cost_eur": 0.019
}
```

### 8.2 Log Aggregation

For v2: Loki (logs) + Grafana (viewing) in the same Compose stack. Simple, cheap, no external dependencies.

### 8.3 Retention

* Application logs: 30 days
* SQLite query log: 90 days (unless user opts for extended retention)

---

## 9. User-Visible Observability

### 9.1 CLI Self-Diagnosis (v1)

```bash
gdpr-check doctor
```

Checks:

* `.env` present and has `ANTHROPIC_API_KEY`
* ChromaDB directory exists and has chunks
* SQLite log readable
* Sample embedding works
* Sample retrieval returns chunks

Output: traffic-light status per check, with specific remediation advice.

### 9.2 Status Endpoint (v2)

```
GET /v1/status
```

Returns:

```json
{
  "status": "ok",
  "version": "2.0.0",
  "knowledge_base": {
    "chunk_count": 2987,
    "last_indexed": "2026-04-20T00:00:00Z",
    "sources": ["gdpr", "bdsg", "ttdsg", "edpb", "dsk", "gdprhub"]
  },
  "latency_last_24h": {
    "p50_ms": 3800,
    "p95_ms": 5400,
    "p99_ms": 7200
  }
}
```

### 9.3 Public Status Page (v3)

For v3 (public launch), a status page at `status.gdpr-ai.example.com` shows service uptime history. Hosted on UptimeRobot or similar.

---

## 10. Cost Budget Enforcement

### 10.1 v1 (Manual)

Developer reviews SQLite daily totals. No automated enforcement.

### 10.2 v2 (Automated)

If daily cost exceeds the configured budget (default: 20 EUR):

1. Alert fires immediately
2. Optional: service enters "degraded mode" that returns cached results only for pre-seen scenarios
3. Optional: new user signups disabled until next day

Configurable per environment.

---

## 11. Data Retention

### 11.1 Query Logs

* v1 (local): indefinite, user controls via `gdpr-check logs clear`
* v2 (hosted): 90 days default, opt-in to 1 year

### 11.2 Metrics

Prometheus retention: 30 days.

### 11.3 Backups

Daily encrypted backup of SQLite to off-server storage. 30-day retention.

---

## 12. Incident Response

### 12.1 Runbooks

Documented in `docs/runbooks/` (v2):

* Anthropic API outage
* Hallucination rate spike
* Cost budget exceeded
* VPS disk full
* Secret exposure

### 12.2 Incident Log

Incidents recorded in `docs/incidents/<date>.md` with timeline, root cause, action items.

---

## 13. Summary

Observability is treated as a first-class feature from v1 (local SQLite query log + cost tracking) and expanded in v2 to a full Prometheus + Grafana + Loki stack hosted alongside the service. Every query is traceable end-to-end. Cost is continuously tracked and enforced. Quality regressions are caught by the nightly evaluation run.

This observability foundation is what enables confident iteration — every change can be measured, every regression caught, every cost surprise flagged early.

---

## v2 Monitoring Additions (local API and compliance mode)

Even without hosted Prometheus, v2 SHOULD capture:

* **Per analysis:** LLM cost (USD/EUR), token counts, wall-clock time, count of chunks retrieved, count of documents generated, mode (`violation_analysis` vs `compliance_assessment`).
* **API request log:** optional SQLite table of `method`, `path`, `status`, `duration_ms`, `analysis_id`, error code — for debugging local FastAPI usage.
* **Per-project cost:** cumulative reasoning-engine spend linked to `project_id` for budget awareness.
* **Errors:** failed LLM calls (status + retry count), ChromaDB query failures, Jinja2 rendering exceptions — structured log lines at ERROR with correlation id.

Hosted Grafana/Prometheus content in earlier sections remains **future** for actual deployment; v2 prioritises **local** observability parity with v1's query logging discipline.