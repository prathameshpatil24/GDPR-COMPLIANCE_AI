# ADR-002: ChromaDB for v1 Vector Storage

**Status**: Accepted
**Date**: 2026-04-21
**Deciders**: Project owner

---

## Context

The RAG architecture requires a vector database to store chunk embeddings and support similarity search. Several options exist, ranging from simple local libraries to hosted managed services.

Criteria:

* Low operational overhead (single developer, local-first v1)
* Sufficient performance for ~3000 chunks
* Metadata filtering support
* Free or very low cost for personal use
* Clear migration path as the project scales

---

## Decision

**Use ChromaDB in embedded mode for v1.**

---

## Rationale

### Zero Operational Overhead

ChromaDB in embedded mode runs in-process with Python. No separate server to install, configure, run, or maintain. Perfect for a single-developer, local-first v1.

### Sufficient Performance

ChromaDB uses HNSW for approximate nearest-neighbour search. With ~3000 chunks (our v1 scale) and the default HNSW parameters, query latency is well under 100ms. Performance is not a concern at this scale.

### Metadata Filtering

ChromaDB supports metadata filtering at query time, essential for our topic-tag-based pre-filtering in the retrieve stage. No need for a second store or custom index.

### Free and Open Source

ChromaDB is Apache-2.0 licensed. Free forever for any use case. No vendor lock-in.

### Migration Path

If v1 performance becomes insufficient, migration to Qdrant (self-hosted) or hosted Chroma is straightforward. Both have similar APIs. The knowledge base is rebuildable from source scripts, so migration is not destructive.

---

## Consequences

### Positive

* Zero operational complexity
* No infrastructure cost
* Fast local iteration
* Simple Python API

### Negative

* Not suitable for multi-user concurrent access (single writer)
* Scaling beyond ~100K chunks would require upgrade
* Backup and replication are manual

### Mitigated Risks

* **Single-writer limitation**: v1 is single-user anyway
* **Scale**: 100K chunks is ~30x our current size; years away
* **Backups**: ChromaDB data is entirely regeneratable from source scripts

---

## Alternatives Considered

### Pinecone

Managed cloud vector database. Rejected for v1 because:

* Costs money (free tier limited, production tier starts at ~$70/month)
* Requires network round-trip per query (~100ms latency added)
* Adds external dependency for a local-first tool
* Vendor lock-in

Strong choice for v3+ if the project scales to thousands of daily users.

### Qdrant (self-hosted)

Strong vector DB, Rust-based, production-grade. Rejected for v1 because:

* Requires running a separate server (Docker container at minimum)
* More configuration than ChromaDB
* Overkill for 3000 chunks

Appropriate upgrade path from ChromaDB when scale demands it.

### Weaviate

Feature-rich but heavier to operate. Rejected for v1 because of operational overhead similar to Qdrant, with added complexity.

### FAISS

Pure C++/Python library, extremely fast. Rejected because:

* No built-in metadata filtering; would require a parallel structure
* Lower-level API; more code to write and maintain
* No persistence out of the box

### pgvector (Postgres extension)

Good choice if Postgres is already in use. Rejected for v1 because:

* We have no other Postgres use case
* Adds a service to manage
* Overkill for local-first v1

### Plain NumPy + Pickle

Simplest possible approach: embeddings in a NumPy array, compute cosine similarity on every query. Rejected because:

* Would scan all chunks linearly (slower at scale)
* No metadata filtering without extra code
* ChromaDB is only marginally more complex and much more capable

---

## Follow-Up Actions

* ChromaDB wrapper lives in `src/gdpr_ai/knowledge/store.py`
* The wrapper abstracts the library, making future migration a single-file change
* Performance monitored via per-stage latency logging