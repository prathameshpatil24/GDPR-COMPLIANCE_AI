# V3 Frontend — Product Overview

This document scopes the **v3 web frontend** for GDPR AI: a local-first React SPA that talks to the existing **v2 FastAPI** backend. It does not replace or duplicate pipeline logic; it is a presentation and orchestration layer.

---

## Version scope

| Topic | Decision |
|--------|-----------|
| **What v3 is** | The **web UI** for GDPR AI: Analyze, History, Stats/Dashboard, and Settings. |
| **Backend** | Unchanged **FastAPI** app under `src/gdpr_ai/api/` (violation + compliance analyze routes, projects, documents, health). |
| **Deployment** | **Local only** for v3: no cloud, no public domain, **no Docker** requirement in this phase. |
| **Dev URLs** | Vite dev server: **`http://localhost:5173`**. API: **`http://localhost:8000`** (existing `gdpr-check serve` / uvicorn). |
| **Networking** | Prefer **Vite proxy** for `/api/*` and `/health` → `localhost:8000` to avoid CORS friction during development (see [v3-api-integration.md](v3-api-integration.md)). |
| **Tenancy** | **Single-user**: one operator on one machine. No multi-tenant isolation, no hosted auth service in v3. |
| **Relationship to v4** | When **v4** ships — **retrieval gap tracker** (dashboard/API), **multilingual** retrieval, **document upload**, **website scanning**, and hosted/product hardening — this frontend is expected to **deploy alongside** those capabilities; v3 establishes patterns (design system, API client, charts) that v4 extends. See [v4-overview.md](v4-overview.md). |

---

## Locked tech stack

Do **not** substitute frameworks without an explicit architecture decision.

| Layer | Choice |
|--------|--------|
| **UI library** | **React 18+** |
| **Build / dev** | **Vite** (SPA, no SSR) |
| **Styling** | **Tailwind CSS** — `dark` mode via **`class` strategy**; **dark is the default** theme. |
| **Components** | **shadcn/ui** (Radix primitives) |
| **Charts** | **Recharts** |
| **Motion** | **Framer Motion** |
| **Fonts** | **Inter** — UI text; **Geist Mono** — article references, scores, IDs, code. |
| **Explicitly out of scope** | **Next.js**, SSR, RSC, Vercel-specific features. Pure **client-side** SPA with API calls to FastAPI. |

---

## Information architecture (four pages)

### 1. Home / Analyze

Primary workflow.

- **Mode toggle**: **Violation Analysis** | **Compliance Assessment**.
- **Input**: Large text area; mode-specific placeholder examples.
- **Submit**: Primary action with loading state (long-running; see API integration doc).
- **Results** (below fold after completion):
  - **Violation**: severity badge, scenario summary, violations table (confidence), recommendations, citations, retrieval gap notes (`unsupported_notes`).
  - **Compliance**: overall risk badge, executive summary, **findings** as expandable cards (area, status, article pills, description, remediation, technical guidance), data map summary/visualization, recommendations.
- **Charts**: risk overview (donut or horizontal bar: compliant / at_risk / non_compliant / insufficient_info), article confidence bar chart (violation mode).

### 2. History

Past analyses.

- **Table**: timestamp, scenario/system text (truncated), mode, severity or risk indicator, cost, latency.
- **Row expand** or drill-down: full report using the same result components as Analyze.
- **Filters**: mode (violation / compliance), severity band where applicable.
- **Search**: substring match on scenario text (client-side or server-side once list API exists).

### 3. Stats / Dashboard

Usage analytics.

- **Summary metrics**: total queries, average latency, average cost, total cost, total tokens — aligned with existing **`get_stats()`** semantics where exposed (see API integration; may require a new HTTP endpoint).
- **Charts**: cost over time, latency over time, queries per day, severity distribution (donut), average violations per query.

### 4. Settings

Configuration and about.

- **API key** (masked input): product intent for optional BYOK or local override; **v3 local default** is server-side `ANTHROPIC_API_KEY` in backend `.env` — document honestly in UI (see API integration).
- **Theme**: toggle **dark / light**; **dark remains default**.
- **About**: app version, link to docs; health/version from `GET /health`.

---

## Repository layout (planned)

Frontend code will live in a **separate top-level directory** (e.g. `frontend/`) — **not** under `src/gdpr_ai/`. This overview intentionally avoids prescribing the exact folder name until Milestone 1; the [v3-component-tree.md](v3-component-tree.md) document defines the internal `src/` structure of that frontend package.

---

## Success criteria (v3)

- A developer can run **API + Vite** locally and complete **both** modes end-to-end from the browser.
- Reports are **faithful** to backend JSON (no invented fields).
- **Long waits** (20–190s) are communicated clearly with non-blocking UI.
- **History** and **Stats** are usable for the single-user workflow, with documented backend gaps closed by small API additions where needed.

---

## References

- [v3-design-system.md](v3-design-system.md)
- [v3-animations.md](v3-animations.md)
- [v3-component-tree.md](v3-component-tree.md)
- [v3-api-integration.md](v3-api-integration.md)
- [v3-roadmap.md](v3-roadmap.md)
- [v4-overview.md](v4-overview.md) (next product phase)
- Existing backend: `src/gdpr_ai/api/`, `src/gdpr_ai/models.py`, `src/gdpr_ai/compliance/schemas.py`
