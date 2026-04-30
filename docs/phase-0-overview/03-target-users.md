# Phase 0.3 – Target Users

## 1. Overview

GDPR AI is designed with multiple user segments in mind, though the initial version is scoped for a single user: the project owner. The architecture, language policy, and feature set anticipate broader adoption in later versions.

This document defines the user segments, their specific needs, how GDPR AI addresses those needs, and the scope of user support across versions.

---

## 2. Primary User Segments

### 2.1 Solo Developers and Founders

**Profile**

* Technical individuals building SaaS products or internal tools
* Often first-time founders without legal support on the team
* Process personal data in EU contexts (user accounts, analytics, marketing)
* Time-constrained and cost-sensitive

**Needs**

* Fast, reliable answers to compliance questions before shipping features
* Understanding of which articles apply to common processing activities
* Awareness of enforcement precedents to calibrate risk
* Plain-language explanations without legal jargon

**How GDPR AI helps**

* Natural-language scenario input removes legal drafting burden
* Structured report format maps directly to engineering decisions
* Enforcement anchoring provides risk context
* Low cost allows regular use throughout development

### 2.2 Junior Data Protection Officers

**Profile**

* Early-career DPOs, often covering multiple business units
* Volume of incoming questions exceeds capacity for deep analysis on each
* Need to triage quickly and escalate only the genuinely complex cases
* Accountable to regulators and senior management

**Needs**

* Fast initial classification of incoming questions
* Confidence that routine cases are handled correctly
* A tool that surfaces which articles and guidelines to review
* A starting point for deeper research, not a replacement for it

**How GDPR AI helps**

* End-to-end runs take tens of seconds to a few minutes depending on scenario complexity, which still beats manual article lookup for bulk triage
* Article-level output maps to the DPO's existing workflow
* Enforcement case references support risk communication to management
* Clear disclaimers ensure the DPO remains the decision-maker

### 2.3 Privacy-Curious Engineers and Product Managers

**Profile**

* Technical professionals without formal legal training
* Want to understand privacy concerns before they escalate
* Design features with privacy-by-design in mind
* Often act as the bridge between engineering teams and DPOs

**Needs**

* Intuition for which product decisions trigger which articles
* Vocabulary to communicate privacy concerns to engineering peers
* Confidence that they are not missing obvious compliance issues

**How GDPR AI helps**

* Exposure to specific articles builds familiarity over time
* Consistent report format trains a shared vocabulary
* Low cost encourages exploration without billing anxiety

### 2.4 Students and Researchers

**Profile**

* Students of law, data science, or information systems
* Researchers studying AI, privacy, or regulatory compliance
* Interested in both the subject matter and the underlying technology

**Needs**

* Concrete scenario-to-article mappings for learning
* A reference implementation of domain-specific RAG
* Access to a low-cost tool without institutional licensing

**How GDPR AI helps**

* Educational value through transparent reasoning
* Open-source code invites study and extension
* Zero entry cost for personal experimentation

### 2.5 Small and Medium Enterprises (SMEs)

**Profile**

* Organisations too small for in-house legal departments
* Often rely on external counsel for formal compliance work
* Face the same GDPR obligations as large enterprises
* Cannot justify enterprise-grade compliance platforms

**Needs**

* Pre-consultation preparation to reduce legal billing
* Routine question handling without external engagement
* Documentation trail for internal accountability

**How GDPR AI helps**

* Accelerates routine analysis before involving external counsel
* Provides article citations that external counsel can quickly validate
* Low cost makes regular use economically rational

---

## 3. Secondary User Segments

These segments are not the primary focus, but the architecture should not exclude them.

### 3.1 Technical Journalists and Bloggers

Writers covering technology, privacy, or regulatory topics who need fast grounding on specific articles when writing about real-world incidents.

### 3.2 Vendor Review Teams

Procurement and vendor risk teams assessing whether a SaaS supplier's data practices raise specific article concerns.

### 3.3 Academic and Policy Researchers

Researchers studying enforcement patterns, article frequency in DPA decisions, or the evolution of national implementations.

---

## 4. User Scope Across Versions

### 4.1 Version 1 – Closed Personal Use

The initial version is scoped for a single user: the project owner. This allows:

* Rapid iteration without user-support overhead
* No authentication, authorisation, or multi-tenancy complexity
* No need for terms of service, privacy policy, or legal review of the tool itself
* Freedom to experiment with prompts, retrieval, and output formats

### 4.2 Version 2 – Compliance Engine, API, and Eval (shipped)

Version 2 is **not** the web UI; it is the **compliance assessment** track delivered alongside v1:

* **Compliance pipeline** — **intake → map → assess → generate** (system description to data map, findings, and markdown documents)
* **REST API** — FastAPI exposes violation analysis and compliance assessment on localhost, with async jobs where needed
* **Eval framework** — unified gold scenarios, baselines, and harness for regression on both modes
* **JSON hardening** — truncation-safe parsing and structured-output handling for long LLM responses
* **Observability** — aggregated **stats**, per-run **history**, and query telemetry (cost, latency, tokens)

The CLI remains the primary interface for v2; projects and generated documents persist in SQLite.

### 4.3 Version 3 – Web UI (planned)

Browser-based product surface on top of the v2 API:

* **React dashboard** (see [Frontend Design](../phase-3-execution/18-frontend-design.md); stack details may evolve)
* Basic **authentication** and **rate limiting** per user
* **Feedback capture** (e.g. thumbs up/down, optional comments) tied to runs
* **PDF export** and **in-browser** rendered reports
* **Multi-turn** clarifying flows where the product design needs them

### 4.4 Version 4 – Near-100% Accuracy, Gap Tracker, Multilingual Retrieval, New Inputs, and Public Product (planned)

v4 prioritises **near-100% retrieval accuracy** through **deterministic article mapping**, **cross-reference graph expansion**, **full-text article assembly**, a **verification** pass, and **confidence scoring** — with **ChromaDB + BM25** retained as **fallback** for edge cases (see [V4 Feature Overview](../v4-overview.md)).

Priority order (see [V4 Feature Overview](../v4-overview.md)):

1. **Near-100% Accuracy Architecture** — rule-based topic-to-article map, parsed GDPR cross-reference expansion, full-text store for reasoning context, second-pass LLM verification, per-claim and overall confidence (explicit uncertainty when not grounded).
2. **Retrieval Gap Tracker** — automated logging and ranking of ungrounded article references (from violation `unsupported_notes` and compliance `insufficient_info` findings), CLI/API visibility, optional semi-automated ingestion, and **gap-rate** metrics; **feeds curation** of the deterministic map for a **self-improving** loop.
3. **Multilingual retrieval** (German-first): bilingual indexing and cross-lingual retrieval; **response language English** initially; UI language indicator.
4. **Document upload** — privacy policies, DPAs, consent forms, and related artefacts as first-class inputs (PDF/DOCX/TXT).
5. **Website scanning** — URL in; privacy/cookie signals extracted; compliance assessment on scraped text (with rate limits).

Also still in scope for v4 where previously planned:

* **Knowledge base** refresh cadence suited to a hosted service
* Formal **terms of service** and **privacy policy**
* **Optional commercial licensing**, subject to CC BY-NC-SA constraints on GDPRhub-derived content

---

## 5. Non-Target Users

GDPR AI is explicitly not designed for:

### 5.1 Non-Technical End Consumers

Individual data subjects asking "Is it legal for this company to have my data?" need a different product — closer to a complaint-drafting tool — and are better served by consumer-facing services.

### 5.2 Large Enterprise Compliance Teams

Organisations with existing enterprise suites have integration, audit, and workflow needs that GDPR AI does not address.

### 5.3 Lawyers Performing Formal Legal Work

GDPR AI is not a legal research platform. Formal legal research requires tools like Beck-Online, Juris, or Westlaw and the professional judgment of a qualified lawyer.

### 5.4 Jurisdictions Outside the EU (v1 scope)

GDPR AI is focused on GDPR and German law. CCPA, PIPEDA, LGPD, and other regimes are out of scope. These could be addressed by sister projects using the same architecture.

---

## 6. User Interaction Model

### 6.1 Primary Interaction (v1)

The primary interaction is a single-shot scenario-to-report flow via the command line:

```
gdpr-check "A German hospital accidentally emails patient test results
            to the wrong patient."
```

The output is a structured report printed to the terminal.

### 6.2 Secondary Interaction (v1)

Users can inspect query logs in the local SQLite database and review retrieval chunks for debugging or learning.

### 6.3 Future Interaction (v3)

A **web UI** lets users type scenarios or system descriptions into a text area, see **rendered reports** in the browser, and **export to PDF**. **Multi-turn** flows can support clarifying questions where product design requires them.

### 6.4 Future Interaction (v4)

* **Higher-confidence analysis** — deterministic primary retrieval, verification pass, and **confidence / uncertainty** surfaced in the UI alongside citations
* **Gaps dashboard** — see which articles most often lack KB or map coverage; trigger or plan ingestion and map updates from ranked gaps
* **Multilingual input** (German-first) aligned with retrieval; **English** structured output initially
* **Document upload** for privacy-policy, DPA, consent, and related review workflows
* **Website scanning** as an input source (subject to technical and legal guardrails in requirements)

---

## 7. User Expectations

### 7.1 What Users Can Expect

* **Latency** — Full pipeline runs are dominated by sequential LLM calls; observed end-to-end times are roughly **20–190 seconds** depending on scenario or system-description complexity, model routing, and hardware—not sub-second interactive chat. Retrieval itself remains fast; most time is reasoning and validation. **v4** adds a **verification** LLM call per analysis on top of the primary reasoning call.
* Accurate article citations grounded in the knowledge base
* **v4:** **Confidence scoring** on claims and **explicit flags** when the system is **not sure**, rather than guessing
* Clear disclaimers that the output is informational
* Consistent report format across queries
* Attribution to source documents for every claim

### 7.2 What Users Should Not Expect

* Legally binding advice
* 100% correctness on edge cases
* Coverage of jurisdictions outside GDPR and German law
* Analysis of uploaded documents or websites before **v4**
* Multi-turn conversational memory in the CLI for **v1**; richer multi-turn is planned for **v3** in the web UI

---

## 8. Summary

GDPR AI serves a spectrum of users united by the need for fast, grounded, affordable GDPR violation analysis. The initial version is deliberately scoped for personal use, with the architecture designed to scale cleanly to broader segments as the tool matures.

The common thread across all target segments is a preference for specialised, transparent, low-cost tooling over generic chatbots or expensive enterprise platforms.

---

## v2 Target Users

v2 keeps all v1 segments but adds emphasis on **builders** and **repeat professional use**. The tiers below describe who benefits most from **compliance assessment** and **document generation**, not from violation analysis alone.

### Tier 1 — Startup founders and indie developers

Building a SaaS product or app, need GDPR-aligned artefacts **before launch**, often **no lawyer and no DPO**. Motivation: a **one-time or occasional** purchase of a **compliance blueprint** they can refine with counsel if needed.

### Tier 2 — Freelance and agency developers

Deliver **10–15 client projects per year**; each new system needs RoPA-style thinking, DPIA triggers, and third-party flow documentation. **Repeat users** — one blueprint per engagement, with comparability across projects.

### Tier 3 — Small-company CTOs and tech leads (roughly 5–50 people)

Shipping **new data collection**, **new integrations**, or **EU expansion**. Need to **reassess periodically** as the product and stack change.

### Tier 4 — Compliance consultants and freelance DPOs

Support **10–20 organisations**; use the tool to **accelerate** structured deliverables — for example a **first-cut DPIA** in minutes instead of many hours of blank-page work — always with professional review where stakes are high.

### Why v2 is not “one-time use”

Teams revisit compliance when:

* **New features** introduce new categories of personal data
* **New third-party processors** or **cross-border** flows appear
* **EU AI Act** or product changes require **reassessment** of risk
* **Investors or acquirers** request due-diligence packs
* **Operational maturity** requires clearer **DSAR** and breach-playbook alignment

v2 is designed for **iteration**: stored **projects**, **re-runs** on changed system descriptions, and **comparison** of assessments over time (see requirements and data model docs).