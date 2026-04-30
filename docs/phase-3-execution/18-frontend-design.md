# Phase 3.18 – Frontend Design

> **Status**: Deferred to v3. Version 1 is CLI-only; version 2 adds a local REST API. This document outlines a planned web frontend that would consume that API in a later release.

## 1. Overview

Version 1 uses the terminal as the user interface. Users enter scenarios via `gdpr-check` and receive Rich-formatted output. This is ideal for solo developer use but limits adoption by non-technical users.

Version **3** introduces a **React dashboard** (this document uses **Next.js** as the reference stack) that exposes the same pipelines via a browser, targeting the broader user segments defined in [03 – Target Users](../phase-0-overview/03-target-users.md).

**Scope:** **v2** ships **CLI + local REST API** only. The browser UI is **v3** and consumes the API in [11 – API Design](../phase-2-architecture/11-api-design.md). **v4** adds **near-100% accuracy architecture**, the **Retrieval Gap Tracker** (dashboard/API), **multilingual** retrieval, **document upload**, and **website scanning**; see [v4-overview.md](../v4-overview.md) and the **Version roadmap** in [Documentation README](../README.md).

---

## 2. Goals

### 2.1 Primary Goals

* Match CLI capability: full scenario analysis with grounded reports
* Clean, modern interface accessible to non-technical users
* Preserve CLI behaviour — no divergence between the two interfaces
* Fast iteration: a basic version shippable in days, not weeks

### 2.2 Non-Goals for v3 (initial web release)

* Native mobile apps
* Offline-first PWA
* Real-time collaboration
* Multiple concurrent sessions per user

---

## 3. Planned Stack

### 3.1 Framework: Next.js (App Router)

Chosen for:

* Strong React ecosystem
* Server-side rendering for fast first paint
* File-based routing simplicity
* Vercel-friendly deployment path if needed

Deployed initially as a static export served from the same VPS as the FastAPI backend, via a reverse proxy in Docker Compose.

### 3.2 Styling: Tailwind CSS

Chosen for:

* Utility-first approach matches fast iteration
* Excellent defaults for a text-heavy content product
* Small production bundle with tree-shaking

### 3.3 Component Library: shadcn/ui

Chosen for:

* Headless, accessible components
* Easy to restyle per the project's brand
* No runtime overhead (components are copied into the project)

### 3.4 State Management: React Query + Zustand

React Query for server state (API calls, caching). Zustand for local UI state (input draft, preferences).

### 3.5 Forms: React Hook Form + Zod

Type-safe form handling with schema validation mirroring the Pydantic backend schema.

---

## 4. Planned Screens

### 4.1 Home / Analyse

The primary screen. Single input area for the scenario, a button to analyse, and a report view below.

**Components**:

* Scenario textarea (supports 2000 chars)
* Character count indicator
* "Analyse" button (disabled when input invalid)
* Report panel (hidden until results arrive)
* Examples dropdown ("Try a sample scenario")

**Behaviour**:

* Submitting fires `POST /v1/analyse`
* Loading state during pipeline execution (3-5s expected)
* Report rendered inline
* Feedback thumbs-up / thumbs-down below each report

### 4.2 Report View

Displays the structured `GDPRReport` from the API.

**Sections**:

* Scenario summary
* Violations (cards with article, definition, scenario-specific explanation, source link)
* Similar enforcement cases (compact list)
* Disclaimer (footer)

**Interactions**:

* Click article link → external navigation to source
* Click similar case → external navigation
* Expand / collapse long explanations
* Copy report as markdown or plain text
* Export as PDF (deferred to v3)

### 4.3 Query History (authenticated)

Lists past queries for the authenticated user, most recent first.

**Components**:

* Table: timestamp, scenario summary (truncated), violation count, cost
* Click row → opens full report

### 4.4 Examples / Learn

A curated set of scenarios with expected outputs, positioned as educational content.

**Purpose**:

* Demonstrates capability to first-time visitors
* Teaches users how to phrase effective scenarios
* SEO value for organic discovery

### 4.5 About / Methodology

Explains:

* How the system works (high-level RAG explanation)
* What it can and cannot do
* Data sources and licensing
* Disclaimer repeated in detail

### 4.6 Account and Settings (authenticated)

* API key management (issue, revoke)
* Feedback history
* Logout

---

## 5. Design Principles

### 5.1 Calm, Professional Aesthetic

The tool handles serious legal topics. Design avoids gimmicks, focuses on readability, and uses restrained colour palette.

### 5.2 Fast First Paint

Critical first-page content visible in under 1 second on a normal connection. Heavier components (report panel) lazy-loaded.

### 5.3 Mobile-Responsive

Most users will be on desktop, but mobile must work. Tailwind's responsive utilities handle most cases. Specific tests on iPhone SE (narrowest common viewport) and iPad.

### 5.4 Accessibility

* Semantic HTML
* Keyboard navigation
* ARIA labels on interactive elements
* Color contrast meeting WCAG AA
* Screen reader tested on VoiceOver

### 5.5 Zero Dark Patterns

No nagging popups, no deceptive free trials, no hidden unsubscribe flows. Users can leave cleanly at any time.

---

## 6. Authentication (v3)

### 6.1 Sign-Up Flow

* Email + password, or
* GitHub OAuth (developer-friendly)

Verification email required before activation.

### 6.2 Session Management

* Server-issued session cookies
* HttpOnly, Secure, SameSite=Lax
* Session lifetime: 7 days rolling

### 6.3 API Key Issuance

After sign-up, user gets a default API key for programmatic use. Additional keys can be created/revoked from settings.

---

## 7. Error States

### 7.1 Recoverable Errors

| Error | UX |
|-------|-----|
| Invalid scenario (too short/long) | Inline validation on the textarea |
| Rate limited | Banner with countdown to retry |
| LLM unavailable | Inline error with retry button |

### 7.2 Non-Recoverable Errors

| Error | UX |
|-------|-----|
| Hallucination after retry | "Unable to produce a grounded report. Please rephrase or try a different scenario." |
| Invalid API key | Redirect to login |
| Server error | Generic "Something went wrong" page with incident ID |

---

## 8. Performance Targets

* First Contentful Paint: < 1.2s
* Time to Interactive: < 2s
* Analyse submit → report visible: match real pipeline latency (tens of seconds to a few minutes — see [03 – Target Users](../phase-0-overview/03-target-users.md) §7.1); UI must show progress, not imply instant chat
* Lighthouse score: > 90 across categories

---

## 9. Analytics and Telemetry

### 9.1 Privacy-First Analytics

Server-side, anonymous analytics only:

* Page views (no user identifier)
* Feature usage counts
* Error rates

No Google Analytics. Options under consideration: Plausible (self-hosted), Umami, or simple server logs.

### 9.2 Feedback Capture

Thumbs-up / thumbs-down on each report stored with the query log. Optional free-text comment.

---

## 10. Internationalisation (v4)

The **v3** web client is **English-first**, matching runtime policy today. **v4** introduces:

* **Retrieval gaps** UI — ranked ungrounded articles, charts, link to ingestion workflow (see [v4-gap-tracker.md](../v4-gap-tracker.md))
* German-first **multilingual retrieval** and aligned UI/report language
* **Document upload** and **website scan** input surfaces on Analyze
* Language indicator / switcher in header (product decision)
* Report output in selected language where the pipeline supports it (initially English-only responses per [v4-overview.md](../v4-overview.md))

The codebase should use i18n-ready patterns from the start (react-intl or next-intl) in **v3**, to avoid refactoring when **v4** lands.

---

## 11. Component Catalogue (Sketch)

| Component | Purpose |
|-----------|---------|
| `<ScenarioInput />` | Large textarea with validation |
| `<AnalyseButton />` | Primary action button with loading state |
| `<ReportPanel />` | Container for the full report |
| `<ViolationCard />` | Single violation display |
| `<SimilarCaseRow />` | Single enforcement case summary |
| `<DisclaimerFooter />` | Always visible on report |
| `<QueryHistoryTable />` | Authenticated user's past queries |
| `<FeedbackWidget />` | Thumbs-up/down + optional comment |

---

## 12. Deployment

### 12.1 Build

Next.js static export (`next build && next export`).

### 12.2 Serving

Static files served by Caddy or nginx within Docker Compose. Same VPS as the FastAPI backend.

### 12.3 CI/CD

GitHub Actions workflow:

1. On push to `main`, build static export
2. Deploy to VPS via rsync
3. Caddy auto-reloads

---

## 13. Summary

The **v3** frontend is designed as a thin, well-styled **React** client over the same pipelines that power the CLI. Next.js + Tailwind + shadcn/ui (or equivalent) deliver a professional, fast-loading interface with minimal maintenance overhead. Authentication, history, feedback, and PDF export are built in from the start of the web release.

Implementation begins when the **v2** API and eval baselines are stable enough to be a dependable backend contract.

---

## v2 / v3 / v4 Note

Frontend work remains **out of scope for v2**. **v2** delivers **CLI commands** and a **local REST API** only. **v3** adds the **React** dashboard that consumes that API. **v4** adds **near-100% accuracy**-related UX (citations, confidence, uncertainty), **gap analytics**, multilingual retrieval, document/URL inputs, and UI/report language strategy on top ([v4-roadmap.md](../v4-roadmap.md)).