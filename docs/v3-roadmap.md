# V3 Frontend — Milestone Roadmap

Delivery plan for the **local-only** React SPA (Vite + Tailwind + shadcn/ui) described in [v3-overview.md](v3-overview.md). Milestones are **sequential**; each should be shippable as a coherent increment on `develop`.

---

## Milestone 1: Project scaffold

**Goal:** Empty app shell wired to the backend with correct defaults.

- [ ] Initialize **Vite + React 18** (JavaScript or TypeScript per team choice — planning docs use `.jsx`).
- [ ] Add **Tailwind** with **`class`-based dark mode**; **dark** as default in `html` / root.
- [ ] Install and configure **shadcn/ui** (Radix + Tailwind).
- [ ] Load **Inter** and **Geist Mono** in `globals.css`.
- [ ] Implement **Sidebar** + **Header** + routed outlet; routes: `/`, `/history`, `/stats`, `/settings`.
- [ ] Add **Framer Motion** `PageTransition` wrapper on route changes.
- [ ] Configure **Vite proxy**: `/api` and `/health` → `http://localhost:8000`.
- [ ] Add `api/client.js` with fetch wrapper and error typing.

**Exit:** Run `gdpr-check serve` + `npm run dev`; navigate all routes; dark theme persists.

---

## Milestone 2: Analyze page

**Goal:** End-to-end violation and compliance runs from the browser.

- [ ] **ModeToggle** (violation | compliance).
- [ ] **ScenarioInput** with mode-specific placeholders and limits (violation 8000 chars; compliance text or future JSON path).
- [ ] **SubmitButton** + **`useAnalyze` / `useAssess`** calling `POST /api/v1/analyze/violation` and `.../compliance`.
- [ ] **LoadingState** with skeleton + indeterminate progress + “1–3 minutes” guidance.
- [ ] Render raw structured **ViolationReport** and **ComplianceReport** (minimal styling acceptable before M3).

**Exit:** Both modes return real JSON from a local API; errors show toast/inline.

---

## Milestone 3: Results visualization

**Goal:** Production-quality report UI matching the design system.

- [ ] **SeverityBadge** + **StatusBadge** with animation rules ([v3-animations.md](v3-animations.md)).
- [ ] **FindingCard** expand/collapse with `AnimatePresence`.
- [ ] **ArticleTag**, **ConfidenceBar**, **RecommendationList**, **CitationList**, **RetrievalGapNote**.
- [ ] **RiskOverviewChart** (finding status distribution) + **ConfidenceChart** (violations).
- [ ] **DataFlowDiagram** for compliance `data_map.data_flows`.
- [ ] Staggered card reveal for findings.

**Exit:** Analyze page matches [v3-design-system.md](v3-design-system.md) for core components.

---

## Milestone 4: History and Stats

**Goal:** Operational visibility for the single user.

- [ ] **History:** implement data loading strategy from [v3-api-integration.md](v3-api-integration.md) (interim: projects + per-id fetch; preferred: new list endpoint when added).
- [ ] **HistoryTable** with sort, mode filter, severity filter, text search.
- [ ] **HistoryDetail** reusing Violation/Compliance report components.
- [ ] **Stats:** consume **`GET /api/v1/stats/summary`** when implemented; otherwise stub with CLI-documented aggregates or defer charts.
- [ ] **StatCard**, **CostChart**, **LatencyChart**, **QueryChart**, **SeverityChart** — wire to real series when API available.

**Exit:** User can review past runs and see cost/latency trends without leaving the app (subject to backend endpoints).

---

## Milestone 5: Polish

**Goal:** Hardening and settings.

- [ ] **Toast** system; consistent error and success feedback.
- [ ] **EmptyState** for History/Stats with no data.
- [ ] **Skeleton** coverage on all slow views.
- [ ] Hover/focus polish per design system; **responsive** layout (desktop-first; basic tablet width).
- [ ] **Settings:** theme toggle (dark default), About + health/version fetch, **ApiKeyInput** with honest copy about server-side key.
- [ ] **Light mode** pass: verify all surfaces in [v3-design-system.md](v3-design-system.md).

**Exit:** v3 local MVP ready for daily dogfooding; documentation updated if API routes were added.

---

## Dependency notes

- Backend work tracked explicitly in [v3-api-integration.md](v3-api-integration.md) (**stats** + **analysis list** endpoints) can parallelize after Milestone 2.
- **v4** features (**retrieval gap** dashboard/API, multilingual, uploads, scanning) **extend** this UI; avoid hard-coding copy-only flows that block i18n hooks added in v4. See [v4-overview.md](v4-overview.md).

---

## References

- [v3-overview.md](v3-overview.md)
- [v3-component-tree.md](v3-component-tree.md)
- [v3-api-integration.md](v3-api-integration.md)
