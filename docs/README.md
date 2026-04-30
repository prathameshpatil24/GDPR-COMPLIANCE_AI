# GDPR AI – Documentation

This folder contains the complete design, requirements, and execution documentation for GDPR AI. The structure follows a four-phase engineering discipline: from problem framing, through requirements and architecture, into execution strategy.

Every document in this folder is version-controlled and updated in lockstep with the codebase. When a design decision changes, the relevant document is updated and the change is captured in a commit alongside the code change that implements it.

## Version roadmap (product releases)

| Version | Scope |
|---------|--------|
| **v1** | Violation analysis CLI — scenario in, grounded violation report out (**shipped**). |
| **v2** | Compliance assessment (**intake → map → assess → generate**), local **REST API**, SQLite persistence, document generation, unified **eval** framework, JSON/output hardening, **stats** / **history** (**shipped**). |
| **v3** | **Web UI** (React dashboard), authentication, rate limiting, feedback capture, PDF export, in-browser reports (**planned**). |
| **v4** | **Near-100% accuracy architecture** (deterministic article mapping, cross-reference graph, full-text assembly, verification, confidence scoring; ChromaDB + BM25 as fallback), **Retrieval Gap Tracker**, German-first **multilingual** retrieval, **document upload**, **website scanning**, KB refresh at service scale, ToS/privacy, optional commercial licensing (**planned**). See [v4-overview.md](v4-overview.md). |

## v2 Scope

Version 1 delivers a **violation analyzer**: free-text scenarios in, grounded violation reports with cited GDPR articles out. Version 2 expands the same product into a **compliance architect** while keeping v1 intact as a first-class mode. v2 accepts a structured (or conversational) **system description** and produces a **compliance blueprint** — risk analysis, DPIA drafts, RoPA templates, consent-flow recommendations, technical implementation guidance, and retention policy drafts — backed by the same retrieval-grounded knowledge base and language-model reasoning engine. v2 adds a REST API (local), SQLite persistence for projects and generated documents, document generation (Jinja2 → markdown), and a new pipeline (**intake → map → assess → generate**) alongside the existing v1 pipeline (**extract → classify → retrieve → reason**). The **browser UI is v3**, not v2. All design docs use clearly marked **v2** sections so v1 material stays easy to find; see [ADR-006](adr/006-dual-mode-architecture.md) and [ADR-007](adr/007-sqlite-for-local-persistence.md).

## V3 — Frontend planning (local SPA)

Implementation-agnostic specs for the **React + Vite** dashboard (v3): overview, design system, motion, component tree, API integration, milestones.

* [v3-overview.md](v3-overview.md)
* [v3-design-system.md](v3-design-system.md)
* [v3-animations.md](v3-animations.md)
* [v3-component-tree.md](v3-component-tree.md)
* [v3-api-integration.md](v3-api-integration.md)
* [v3-roadmap.md](v3-roadmap.md)

## V4 — Product planning

Prioritised features: **near-100% accuracy architecture**, **retrieval gap tracker**, **multilingual retrieval**, **document upload**, **website scanning**.

* [v4-overview.md](v4-overview.md) — rationale, scope, dependencies
* [v4-gap-tracker.md](v4-gap-tracker.md) — schema, CLI/API, ingestion, metrics
* [v4-roadmap.md](v4-roadmap.md) — milestones

## Phase 0 – Overview

Foundational framing of what GDPR AI is, why it exists, who it serves, and how it will be delivered.

* [01 – Problem Statement](phase-0-overview/01-problem-statement.md)
* [02 – Why GDPR AI](phase-0-overview/02-why-gdpr-ai.md)
* [03 – Target Users](phase-0-overview/03-target-users.md)
* [04 – Implementation Plan](phase-0-overview/04-implementation-plan.md)

## Phase 1 – Requirements

What the system must do, how well it must do it, and the boundaries within which it operates.

* [05 – Functional Requirements](phase-1-requirements/05-functional-requirements.md)
* [06 – Non-Functional Requirements](phase-1-requirements/06-non-functional-requirements.md)
* [07 – Constraints and Assumptions](phase-1-requirements/07-constraints-assumptions.md)

## Phase 2 – Architecture

System-level design decisions, stack mapping, data model, and cross-cutting concerns.

* [08 – High-Level Architecture](phase-2-architecture/08-high-level-architecture.md)
* [09 – Technical Stack Mapping](phase-2-architecture/09-technical-stack-mapping.md)
* [10 – Data and Knowledge Model Design](phase-2-architecture/10-data-knowledge-model.md)
* [11 – API Design](phase-2-architecture/11-api-design.md)
* [12 – Cloud Architecture and Deployment](phase-2-architecture/12-cloud-architecture.md) *(deferred to v3+ when the web UI is hosted; v2 API runs locally)*
* [13 – Security Design](phase-2-architecture/13-security-design.md)

## Phase 3 – Execution and Build Strategy

Implementation-level detail: modules, flow, testing, frontend, CI/CD, monitoring.

* [14 – Backend Execution Design](phase-3-execution/14-backend-execution-design.md)
* [15 – Pipeline Module Design](phase-3-execution/15-pipeline-module-design.md)
* [16 – Knowledge Base Schema Design](phase-3-execution/16-knowledge-base-schema.md)
* [17 – Runtime Request Flow](phase-3-execution/17-runtime-request-flow.md)
* [18 – Frontend Design](phase-3-execution/18-frontend-design.md) *(deferred to v3)*
* [19 – Testing Strategy](phase-3-execution/19-testing-strategy.md)
* [20 – CI/CD Pipeline Design](phase-3-execution/20-cicd-pipeline.md) *(deferred to v3+ alongside hosted delivery)*
* [21 – Monitoring and Alerting Design](phase-3-execution/21-monitoring-alerting.md)

## Architecture Decision Records (ADRs)

Point-in-time records of significant design decisions, preserved even when decisions are later superseded.

* [001 – Pre-Indexed RAG over Live Fetching](adr/001-pre-indexed-rag-over-live-fetching.md)
* [002 – ChromaDB for v1](adr/002-chromadb-for-v1.md)
* [003 – English-Only Runtime](adr/003-english-only-v1.md)
* [004 – One-Time Translation of German Sources](adr/004-one-time-translation.md)
* [005 – Strict Grounding Over Generation Quality](adr/005-strict-grounding.md)
* [006 – Dual-Mode Architecture (v1 + v2)](adr/006-dual-mode-architecture.md)
* [007 – SQLite for Local Persistence](adr/007-sqlite-for-local-persistence.md)
* [008 – Deterministic Retrieval Primary (v4)](adr/008-deterministic-retrieval-primary.md)

## How to Read This

If you are new to the project, read in the following order:

1. Phase 0 documents in sequence (01 → 04), including **v2** sections where present, and the **version roadmap** table at the top of this README
2. Phase 1 in sequence (05 → 07)
3. Phase 2 High-Level Architecture (08), Data Model (10), and **API Design (11)** for v2 surfaces
4. ADR-006 and ADR-007 for dual-mode and persistence decisions
5. Any Phase 3 document relevant to what you are working on (pipeline 15, knowledge base 16, request flow 17, testing 19)

If you are evaluating the project for portfolio or hiring purposes, the most informative documents are:

* [01 – Problem Statement](phase-0-overview/01-problem-statement.md)
* [08 – High-Level Architecture](phase-2-architecture/08-high-level-architecture.md)
* [09 – Technical Stack Mapping](phase-2-architecture/09-technical-stack-mapping.md)
* [11 – API Design](phase-2-architecture/11-api-design.md)
* [15 – Pipeline Module Design](phase-3-execution/15-pipeline-module-design.md)
* [19 – Testing Strategy](phase-3-execution/19-testing-strategy.md)

## Document Conventions

* Every document uses numbered section headers for navigability
* Tables are used for comparisons and structured data
* Code blocks are used for concrete examples, commands, and schemas
* Cross-references use relative markdown links
* Deferred work is explicitly marked to distinguish it from unaddressed work