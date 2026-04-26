# ADR-007: SQLite for Local Persistence (Projects, Analyses, Documents)

**Status**: Accepted  
**Date**: 2026-04-26  
**Deciders**: Project owner  

---

## Context

Version 1 is largely **stateless** at the product level: each CLI run stands alone, aside from optional query logging. Version 2 introduces **projects** (multiple system descriptions per user), **analysis history**, and **generated markdown documents** that users revisit, compare, and export.

A persistence layer is required that matches **local-first** deployment: no mandatory cloud database, minimal operations, single-tenant developer machine.

---

## Decision

**Use SQLite for v2 project, analysis, and document storage.**

Schema includes users (local identity), projects, analyses (with mode and JSON result), and documents (markdown bodies linked to analyses). See [10 – Data and Knowledge Model](../phase-2-architecture/10-data-knowledge-model.md).

---

## Rationale

* **Zero external infrastructure** — file-based, ships with Python ecosystem support.
* **Appropriate scale** — hundreds to thousands of projects, not millions of tenants.
* **Backup and erase** — single file is easy to copy, move, or delete for privacy.
* **Straightforward migration path** — if v3 introduces hosted multi-user, schemas can move to PostgreSQL with ORM or ETL.

---

## Consequences

### Positive

* Fast to implement; works identically on macOS, Linux, WSL.
* SQL queries support dashboards and cost rollups per project.

### Negative

* **Concurrent writers** are limited — acceptable for single-user local v2.
* **No built-in network authentication** — API auth deferred to v3; trust boundary is the local machine.
* **Single file corruption** risks mitigated by periodic copy-out backups (user-operated).

---

## Compliance

SQLite stores **system descriptions** and **assessment text**, not production personal datasets. Users must still avoid pasting real data subject records into descriptions sent to the language-model API.
