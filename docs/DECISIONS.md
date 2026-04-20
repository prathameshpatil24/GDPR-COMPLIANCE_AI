# Architecture Decision Records

## ADR-001: Pre-indexed RAG over live fetching
**Date**: 2026-04-21
**Status**: Accepted

Legal text is stable. Pre-indexing gives ~100x speed and ~10x cost advantage
vs. live fetching, and avoids rate-limiting. Live fetching reserved for v2
as fallback for long-tail queries.

## ADR-002: ChromaDB for v1
**Date**: 2026-04-21
**Status**: Accepted

Embedded, no server, <5min setup. Pinecone/Qdrant overkill for <10K chunks.
Migration path to Qdrant documented if scale requires.

## ADR-003: English-only for v1
**Date**: 2026-04-21
**Status**: Accepted

German content in knowledge base, but UI + reports in English. Bilingual
prompts/outputs come in v2 once core pipeline is validated.
