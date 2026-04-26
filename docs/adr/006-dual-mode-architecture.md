# ADR-006: Dual-Mode Architecture (Violation Analysis + Compliance Assessment)

**Status**: Accepted  
**Date**: 2026-04-26  
**Deciders**: Project owner  

---

## Context

Version 2 could have **replaced** violation analysis with compliance assessment entirely. Alternatively, the product could ship **two modes**: the existing v1 pipeline (scenario → violated articles) and a new pipeline (system description → compliance blueprint).

Violation analysis remains valuable for **incident-style** questions and for users who already have a narrative fact pattern. Compliance assessment addresses **greenfield** and **architecture** questions. Both benefit from the same retrieval corpus and the same reasoning engine vendor contract.

---

## Decision

**Support both violation analysis (v1) and compliance assessment (v2) as separate pipelines that share the ChromaDB knowledge base and the language-model reasoning engine.**

A **mode router** at the CLI and API boundary selects `violation_analysis` vs `compliance_assessment` before invoking stage-specific code.

---

## Rationale

* **Shared infrastructure** (embeddings, vector store, chunk metadata, cost tracking) avoids duplicating ingestion and retrieval logic.
* **Separate pipelines** allow prompts, gold tests, and output schemas to evolve independently without breaking the other mode.
* **Preserved v1 utility** — no forced migration of CLI users or eval harnesses to a single new abstraction.

---

## Consequences

### Positive

* Retrieval improvements (chunking, weighting, new sources) benefit **both** modes where collections overlap.
* Portfolio and product story stay clear: **detective** vs **architect** metaphors map to explicit entry points.

### Negative

* **Two** prompt families and **two** gold sets to maintain (violation + compliance).
* Slightly more **routing** and testing surface in CLI and FastAPI.
* Risk of **drift** if one mode’s grounding rules are tightened without the other — mitigated by shared validation helpers and documentation cross-links.

---

## Compliance

This ADR does not relax ADR-005 (strict grounding): both modes must cite only from retrieved material for regulatory claims, adapted per-mode in validation logic.
