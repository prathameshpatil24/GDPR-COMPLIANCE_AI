# Phase 1.7 – Constraints and Assumptions

## 1. Overview

This document records the project-level constraints and assumptions that shape every design decision in GDPR AI. Constraints are external rules we must respect. Assumptions are working beliefs about users, data, and context that, if false, would require rework.

Both are numbered for traceability (`C-` for constraints, `A-` for assumptions).

---

## 2. Hard Constraints (Legal and Licensing)

### C-01 – CC BY-NC-SA 4.0 for GDPRhub Content

GDPRhub's content is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International. This means:

* The knowledge base containing GDPRhub-derived chunks cannot be used for commercial purposes
* Attribution to noyb — European Center for Digital Rights — must be preserved
* Any derivative knowledge base must be licensed under the same terms
* Commercial use requires separate licensing negotiation via `info@noyb.eu`

Implication: v1 is strictly non-commercial. Commercial availability requires either removing GDPRhub content or securing commercial licensing.

### C-02 – No Legal Advice

The system must never claim to provide legal advice.

* Every output includes a disclaimer
* Marketing language avoids claims of legal authority
* Users are directed to qualified counsel for decisions with legal or financial consequences

### C-03 – Translation Status

Machine translations of German legal text have no legal status. Only the German-language originals are authoritative.

* Disclaimers make this explicit
* Translation errors must be treated as non-authoritative
* Critical disputes about the law must reference the original German

### C-04 – Source Attribution

Every knowledge-base chunk must retain attribution metadata.

* GDPR: EUR-Lex URL, © European Union
* BDSG / TTDSG: gesetze-im-internet.de, Federal Ministry of Justice
* EDPB: edpb.europa.eu, © European Union
* DSK / BfDI / BayLDA / LfDI BW: respective publishers
* GDPRhub: gdprhub.eu, © noyb, CC BY-NC-SA 4.0
* Enforcement Tracker: enforcementtracker.com, © CMS Hasche Sigle

---

## 3. Hard Constraints (Technical)

### C-05 – English-Only Runtime

All user-facing surfaces (input, output, CLI) use English only in v1.

* Scenarios are accepted only in English
* Reports are generated only in English
* Multilingual UI is deferred to **v4** (German-first; see [03 – Target Users](../phase-0-overview/03-target-users.md) and [v4-overview.md](../v4-overview.md); **Near-100% Accuracy Architecture** is v4 priority 1, **Retrieval Gap Tracker** priority 2)

### C-06 – Text-Only Input

The system accepts only free-text scenarios in v1.

* No document upload (PDF, DOCX, etc.)
* No URL analysis
* No image or screenshot inputs

### C-07 – Single-Turn Interaction

Each query is independent. No conversation memory in v1.

* Follow-up questions must re-state the full scenario
* Multi-turn reasoning in a product UI is deferred to **v3** (web); deeper multilingual flows align with **v4**

### C-08 – Local Execution

The system must run entirely on a single machine in v1.

* No cloud hosting
* No external databases (besides ChromaDB running embedded)
* No server components

### C-09 – Anthropic API Dependency

Language model calls go exclusively to Anthropic's API in v1.

* Haiku for fast classification and extraction
* Sonnet for grounded reasoning
* No fallback to other providers (OpenAI, Cohere, local LLMs) in v1

### C-10 – Python 3.11+

The system requires Python 3.11 or higher.

* Reason: modern type hints and performance improvements
* Enforcement: pinned via `uv python pin 3.11`

---

## 4. Soft Constraints (Budget and Time)

### C-11 – Budget Ceiling

The total budget for development and running costs is modest.

* Target: under 20 EUR for all development
* Monthly running cost: under 10 EUR for personal use

### C-12 – Development Time

The development plan assumes part-time solo effort.

* Target: 2-3 weeks to v1 shipped
* Constraint: interleaves with full-time work and study commitments

### C-13 – Solo Developer

The project is built and maintained by a single developer in v1.

* No team coordination overhead
* No cross-team dependencies
* Implication: simplicity is favoured over process

---

## 5. Scope Constraints

### C-14 – GDPR and German Law Only

The system covers GDPR and German national law in v1.

* No CCPA, PIPEDA, LGPD, or other regimes
* No coverage of other EU member state implementations beyond what appears in GDPRhub cases

### C-15 – Violation Detection, Not Compliance Workflow

The system identifies potential violations from scenarios. It does not manage compliance workflows.

* No DPIA management
* No consent record management
* No data subject request queue
* No breach notification tracking

### C-16 – Reasoning, Not Drafting

The system explains violations. It does not draft remediation documents.

* No DPA text generation
* No policy drafting
* No complaint letter composition

---

## 6. Working Assumptions

### A-01 – Source Stability

Legal and regulatory source websites (EUR-Lex, gesetze-im-internet.de, EDPB, GDPRhub) will remain available and maintain stable HTML structures for the duration of the project.

* If any source structure changes, parsing code will need updates
* Mitigation: raw HTML cached locally for re-parsing

### A-02 – GDPR Text Stability

The text of GDPR articles will not change materially during v1 development.

* Minor amendments are possible but rare
* Quarterly re-scraping captures any changes

### A-03 – Embedding Model Quality

The `BAAI/bge-m3` embedding model is sufficient for legal English retrieval.

* Validated: empirically via gold-set retrieval quality
* Fallback: switch to Voyage or OpenAI embeddings if quality insufficient

### A-04 – LLM Reasoning Capability

Claude Sonnet can reliably reason over 10-15 retrieved chunks and produce grounded outputs.

* Validated: in evaluation harness runs
* Fallback: simpler prompt structure if reasoning quality is inconsistent

### A-05 – User Technical Proficiency

Users of v1 are comfortable with a command-line interface and can edit `.env` files.

* Non-technical users are target for **v3** (web UI)

### A-06 – Scenarios Describe Real or Hypothetical Situations

User scenarios describe fact patterns with enough detail for legal analysis.

* Too-vague scenarios are rejected with a clarification request
* Real-world scenarios without clear legal framing may still produce useful output

### A-07 – English is an Acceptable Interface Language

Users of v1 accept English output even in German contexts.

* Evidence: most EU privacy professionals work in English at least partially
* **v4** will introduce a **Retrieval Gap Tracker**, German-first multilingual UI and retrieval, and new input modes — see [v4-overview.md](../v4-overview.md)

### A-08 – Local Storage Capacity

Target machines have at least 1 GB of free disk space for the knowledge base and embedding model.

* Actual size: approximately 500 MB total
* Verification: `df -h` check before `uv sync`

### A-09 – Internet Availability for API Calls

Users have reliable internet access for Anthropic API calls during query time.

* Offline retrieval inspection is supported
* Full pipeline requires network

### A-10 – User Awareness of the Non-Commercial Constraint

Users understand that the bundled knowledge base cannot be redistributed commercially.

* Communicated: README licensing section
* Enforced: v1 is not commercially offered

---

## 7. Assumption Invalidation Plan

If a key assumption is invalidated, the following actions apply:

| Assumption | Invalidation Signal | Response |
|------------|---------------------|----------|
| A-01 Source stability | Scraper fails on a source | Update parser; verify other scrapers still work |
| A-03 Embedding quality | Gold-set retrieval drops | Switch embedding model; re-index |
| A-04 LLM reasoning | Gold-set precision drops | Simplify prompt; reduce chunk count; iterate |
| A-05 User proficiency | Feedback indicates CLI is too technical | Accelerate **v3** web UI |
| A-09 Internet availability | Frequent API failures | Add offline-only fallback mode |

---

## 8. Dependencies on External Factors

### 8.1 External Services

| Service | Purpose | Risk if Unavailable |
|---------|---------|---------------------|
| Anthropic API | LLM reasoning | System fails gracefully with clear error |
| EUR-Lex | GDPR source | Cached copy remains valid |
| gesetze-im-internet.de | BDSG, TTDSG source | Cached copy remains valid |
| GDPRhub | Enforcement cases | Cached copy remains valid |
| EDPB | Guidelines | Cached copy remains valid |

### 8.2 External Policies

| Policy | Impact |
|--------|--------|
| Anthropic pricing | Direct impact on per-query cost |
| Anthropic data retention | Users are advised to review before sharing sensitive scenarios |
| CC BY-NC-SA 4.0 (GDPRhub) | Hard non-commercial constraint |

---

## 9. Summary

GDPR AI operates within a clear envelope: GDPR and German law, English runtime, single-shot CLI, local execution, non-commercial use, single developer, modest budget, short timeline. These constraints are deliberate choices that trade breadth for depth and feature richness for precision.

The working assumptions are tractable — source stability, embedding quality, LLM reasoning — and all have defined response plans if invalidated. This leaves the project with a small, well-understood risk surface and a clear path to v1.

---

## v2 Constraints and Assumptions

**Accuracy of intake** — v2 assumes the user supplies a **good-faith, accurate** system description. Incomplete or misleading inputs produce unreliable assessments (garbage in, garbage out).

**Not legal advice** — v2 outputs are **guidance and drafts** only. Every generated document SHALL include a **disclaimer** that it is not legal advice and must be reviewed by qualified counsel where appropriate.

**DPO and high-risk processing** — v2 does **not** replace a qualified DPO or legal counsel for **high-risk** processing or regulated sectors; it accelerates structured thinking only.

**Regulatory scope** — v2 knowledge covers GDPR, BDSG, TTDSG, and EDPB-oriented materials in the knowledge base. It does **not** claim completeness for **sector-specific** regimes (for example dedicated health finance or telecom rules beyond what the indexed corpus contains).

**EU AI Act scope** — Cross-references to the EU AI Act are **limited to GDPR-adjacent** personal-data and documentation obligations, not full conformity assessment for AI products.

**Local processing and LLM calls** — All indexing, retrieval, SQLite storage, and document assembly run **locally**. Content sent to the language-model API is limited to **scenario or system-description text** and **retrieved legal excerpts** — not bulk personal data from a production database.

**SQLite sufficiency** — SQLite is the persistence layer for v2 local use. Migration to PostgreSQL (or similar) is **deferred to v3+** if multi-user **hosted** deployment requires it.