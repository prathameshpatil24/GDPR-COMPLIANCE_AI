# ADR-001: Pre-Indexed RAG over Live Fetching

**Status**: Accepted
**Date**: 2026-04-21
**Deciders**: Project owner

---

## Context

GDPR AI needs access to a large body of legal text at query time: GDPR articles, BDSG sections, EDPB guidelines, DPA decisions, and enforcement case summaries.

Two broad approaches exist for getting this content to the LLM:

1. **Pre-indexed retrieval (RAG)**: Scrape all sources once, chunk them, embed them, store them locally. At query time, retrieve the relevant chunks from the local store and pass them to the LLM.

2. **Live fetching**: At query time, fetch the relevant source pages over HTTP, parse them, and pass the result to the LLM.

We must choose one (or a hybrid) as the primary strategy.

---

## Decision

**Use pre-indexed retrieval (RAG) as the primary strategy for v1.** Reserve live fetching as a fallback for specific long-tail cases in v2.

---

## Rationale

### Speed

Pre-indexed retrieval: ~50ms per query (local vector search + BM25). Live fetching: 5-20 seconds per query (multiple HTTP requests + HTML parsing + much larger LLM context).

This is a ~100x speedup.

### Cost

Pre-indexed retrieval sends approximately 3K tokens per query to the LLM. Live fetching sends 20K-50K tokens (raw HTML pages). At Sonnet rates, this is a ~10x cost reduction.

### Reliability

Source websites (EUR-Lex, gesetze-im-internet.de, GDPRhub) have rate limits and occasional outages. Pre-indexed retrieval is immune to these at query time. Live fetching would produce user-visible errors whenever a source is slow or blocking.

### Knowledge of What to Fetch

To live-fetch, the system must already know *which* page to fetch for a given scenario. Determining this requires... retrieval. So live fetching cannot avoid retrieval entirely — it just pushes it to a different layer. Pre-indexing is the simpler, more direct approach.

### Quality Control

Pre-indexing allows careful chunking, metadata attachment, and quality review once. Live fetching relies on whatever HTML happens to come back at query time.

### Legal Text is Stable

GDPR articles, BDSG sections, and landmark cases do not change frequently. There is no meaningful freshness penalty from pre-indexing and refreshing quarterly for legal text, monthly for enforcement cases.

---

## Consequences

### Positive

* Sub-second retrieval at query time
* Roughly 10x lower LLM cost per query
* Full control over chunking and metadata
* Immune to source website outages at query time

### Negative

* Requires a one-time build step (~1 hour) before the system can answer queries
* Knowledge base can become stale; requires a refresh process
* Initial disk space requirement (~500 MB)

### Mitigated Risks

* **Staleness**: scheduled monthly re-scraping of enforcement cases; quarterly for legal text
* **Build cost**: the scraping and chunking steps use no LLM calls and are free
* **Disk space**: 500 MB is trivial on any modern laptop

---

## Alternatives Considered

### Alternative 1: Live Fetching Only

Rejected. Too slow, too expensive, unreliable, and still requires retrieval to decide what to fetch.

### Alternative 2: Hybrid (Pre-indexed + Live Fallback)

Considered. Appropriate for v2 when specific long-tail cases warrant live enrichment (e.g., user asks about a very recent case not yet in the index). For v1, adds complexity without proportional value.

### Alternative 3: Direct URL Analysis

The user provides a URL (e.g., a company's privacy policy) and the system fetches and analyses it. Rejected for v1 because it expands scope beyond the project's core value proposition (scenario → article). Scoped for v2.

---

## Follow-Up Actions

* Pre-indexing scripts implemented in Phase B of the implementation plan
* Refresh cadence documented in the knowledge base schema doc
* Live-fetch fallback revisited in v2 planning

---

## v4 note (retrieval strategy)

**v4** adds **deterministic article mapping**, a **cross-reference graph**, and **full-text article assembly** ahead of chunk-based **ChromaDB + BM25** retrieval for the common case; hybrid search remains the **fallback** when rules do not match. See [v4-overview.md](../v4-overview.md).