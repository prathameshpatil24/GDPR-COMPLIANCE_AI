# ADR-008: Deterministic Article Mapping as Primary Retrieval (v4)

**Status**: Accepted (planning)
**Date**: 2026-04-30
**Deciders**: Project owner

---

## Context

From v1 through v3 planning, **retrieval** for legal content has been described primarily as **hybrid search**: dense embeddings (ChromaDB / cosine similarity) plus sparse **BM25** over chunked text. That stack is appropriate for open corpora, but **similarity in embedding space is not equivalent to legal relevance**: GDPR uses overlapping vocabulary across many articles; a single query vector can blur distinct legal tests; and “nearest neighbours” can be **related but wrong** articles.

For a **compliance** product, retrieval errors translate directly into **user risk** (e.g. missing a DPIA obligation or a lawful-basis conflict). The project’s **v4** goal is **near-100%** grounded accuracy where the corpus allows it, and **explicit uncertainty** where it does not.

The **GDPR +** linked German law and guidance form a **finite, bounded corpus** (on the order of 99 articles, 173 recitals, plus sections and guidelines). In principle, **topics can be mapped deterministically** to article sets without consulting a vector index for the common case.

---

## Decision

**Use deterministic article mapping and cross-reference graph expansion as the primary retrieval path in v4**, with **full-text article assembly** from a dedicated store for reasoning context. **Retain ChromaDB + BM25 hybrid search as a fallback** for queries that do not match deterministic rules or need long-tail coverage (e.g. enforcement summaries, novel phrasing).

See [v4-overview.md](../v4-overview.md) for the five-layer architecture (map → graph → store → reason → verify → confidence).

---

## Rationale

* **Accuracy by construction:** A curated **topic → article** map is **auditable**; users and operators can see *why* an article entered the context set.
* **Latency and cost:** Layers 1–3 (map, graph, store lookup) add **no LLM tokens** and minimal CPU vs embedding + vector search on every query.
* **Explainability:** Deterministic paths are easier to regression-test than pure embedding k-NN.
* **Similarity still valuable:** Semantic search remains the right **safety net** for unmapped topics, ambiguous scenarios, and non-article knowledge (cases, trackers) that does not fit a static map row.

---

## Consequences

### Positive

* Clear path to higher **article-level precision** on gold scenarios.
* Reduced reliance on “retrieval lottery” for **core** GDPR questions.
* Structured **verification** and **confidence** layers become meaningful because the primary context is **known article text**.

### Negative / costs

* **Upfront curation:** ~200–300 hand-maintained mapping rules (and ongoing updates when law or guidance changes).
* **Pipeline complexity:** Three retrieval paths (deterministic, graph expansion, semantic fallback) must be **merged, deduplicated, and tested**.
* **Operational asset:** The article map is a **long-lived** product asset requiring governance (versioning, changelogs).

### Unchanged by this ADR

* ADR-002 (**ChromaDB** for vector storage) remains valid: vectors still index chunks for **fallback** and for sources that stay chunk-oriented.
* ADR-001 (**pre-indexed RAG**) remains valid: legal text is still **prepared offline**; v4 adds **deterministic** and **full-text** layers on top of the same corpus.

---

## Alternatives Considered

### RAG-only (status quo)

Rejected as **primary** strategy for v4 accuracy goals: similarity drift and chunk boundaries remain a ceiling on legal precision.

### Replace ChromaDB entirely

Rejected for v4: **fallback** and auxiliary collections remain necessary; migration risk without proportional gain.

### Live fetch at query time as primary

Rejected: conflicts with ADR-001 operational model; does not remove the need to decide *what* to retrieve.
