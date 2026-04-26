# Phase 2.9 – Technical Stack Mapping

## 1. Overview

This document maps each architectural component to its concrete technology choice, explains why that choice was made, and describes the alternatives considered.

Every choice is evaluated against the project's core priorities: accuracy, low cost, fast development, and local-first execution.

---

## 2. Language and Runtime

### 2.1 Python 3.11+

**Chosen**: Python 3.11+

**Why**:

* Dominant language for ML/NLP/RAG ecosystems
* Strong libraries for every component we need (Anthropic SDK, sentence-transformers, ChromaDB, Typer, Pydantic)
* Familiar syntax keeps solo development fast
* Version 3.11 brings meaningful speed improvements and better error messages
* Native `asyncio` support for future concurrency needs

**Alternatives considered**:

* **TypeScript / Node**: Strong for web backends, weaker for local ML inference
* **Go**: Fast, but anaemic ML ecosystem
* **Rust**: Best performance, but slower development velocity

### 2.2 uv for Package Management

**Chosen**: uv (Astral)

**Why**:

* 10-100× faster than pip and poetry for dependency resolution
* Unified tool for venv, Python version management, and lockfile
* Modern replacement for pip + virtualenv + pyenv
* Active development and strong ecosystem adoption

**Alternatives considered**:

* **pip + virtualenv**: Slower, less unified, older conventions
* **Poetry**: Mature, but slower and has had historical resolution issues
* **pdm**: Good, but smaller community and ecosystem

---

## 3. LLM Layer

### 3.1 Anthropic Claude API

**Chosen**: Anthropic Claude (Haiku + Sonnet)

**Why**:

* Strong instruction-following and structured output quality
* Competitive pricing for Haiku tier (cheaper than GPT-4-class models)
* Sonnet tier provides the reasoning quality needed for grounded legal analysis
* Consistent API across models for easy tier selection

**Alternatives considered**:

* **OpenAI GPT-4**: Comparable quality, slightly higher cost at equivalent tier
* **Google Gemini**: Competitive, less mature ecosystem for structured output
* **Local LLMs (Llama, Mistral)**: Free inference but insufficient reasoning quality for legal grounding in v1
* **Cohere**: Strong for retrieval use cases but weaker on long-form reasoning

### 3.2 Model Tier Split

**Chosen**:

* Haiku for Extract and Classify
* Sonnet for Reason

**Why**:

* Extract and Classify are structured tasks that Haiku handles reliably at a fraction of the cost
* Reason requires multi-chunk synthesis and careful grounding — Sonnet's reasoning depth is necessary
* This split keeps average per-query cost under 0.05 EUR while preserving reasoning quality

---

## 4. Retrieval Layer

### 4.1 ChromaDB

**Chosen**: ChromaDB in embedded mode

**Why**:

* Runs in-process, no server required
* Zero operational overhead for v1
* Sufficient performance for 10K+ chunks
* Simple Python API
* Free, open-source, active development
* Easy migration path to hosted Chroma or Qdrant in v2

**Alternatives considered**:

* **Pinecone**: Managed, but costs money and adds network latency
* **Qdrant**: More production-grade but requires running a separate server
* **Weaviate**: Feature-rich but heavier to operate
* **FAISS**: Fast but lower-level and missing metadata filtering

### 4.2 BAAI/bge-m3 Embeddings

**Chosen**: `BAAI/bge-m3` via `sentence-transformers`

**Why**:

* Strong semantic quality for legal English
* Runs locally, no API costs for embedding
* Reasonable model size (~2GB) for a laptop
* Supports multilingual retrieval for future v2 expansion
* MIT licensed

**Alternatives considered**:

* **OpenAI text-embedding-3-large**: Good quality but API-based, adds cost and latency
* **Voyage AI voyage-3**: Best-in-class for some legal benchmarks, but API-based
* **all-MiniLM-L6-v2**: Smaller and faster but lower quality
* **Cohere embed-english-v3**: Strong but API-based

### 4.3 BM25 for Sparse Retrieval

**Chosen**: `rank-bm25` library

**Why**:

* Proven algorithm for keyword matching
* Complements dense retrieval (catches queries where embeddings miss lexical overlap)
* No training required
* Lightweight, pure Python

**Alternatives considered**:

* **TF-IDF**: Simpler but weaker ranking
* **SPLADE**: Neural sparse retrieval, much higher setup complexity
* **Elasticsearch**: Overkill for 10K chunks

---

## 5. Application Layer

### 5.1 Typer for CLI

**Chosen**: Typer

**Why**:

* Modern, type-hint-driven CLI framework
* Auto-generates help text from function signatures
* Excellent integration with Rich for output formatting
* Built on Click with cleaner API

**Alternatives considered**:

* **Click**: Mature but more verbose
* **argparse**: Standard library, lower-level
* **fire**: Minimal but less feature-rich

### 5.2 Rich for Terminal Output

**Chosen**: Rich

**Why**:

* Beautiful default styling
* Tables, panels, syntax highlighting, progress bars out of the box
* Excellent for structured report rendering
* Plays well with Typer

**Alternatives considered**:

* **Plain print**: No styling, poor readability for structured reports
* **blessed / curses**: Lower-level, more complex

### 5.3 Pydantic v2 for Data Models

**Chosen**: Pydantic v2

**Why**:

* Industry-standard for Python data validation
* v2 is significantly faster than v1
* Native JSON schema generation
* Tight integration with FastAPI (v2 web layer)
* Strict validation enforces data contracts throughout pipeline

**Alternatives considered**:

* **dataclasses**: Standard library but no validation
* **attrs**: Clean but less integrated with the ML ecosystem
* **msgspec**: Fast but smaller community

### 5.4 pydantic-settings for Configuration

**Chosen**: `pydantic-settings`

**Why**:

* Extends Pydantic v2 for loading config from `.env`
* Type-safe configuration access throughout the codebase
* Clean separation of development vs production settings

**Alternatives considered**:

* **python-dotenv + manual parsing**: Works but untyped
* **dynaconf**: More feature-rich but heavier

---

## 6. Data Layer

### 6.1 SQLite for Query Logs

**Chosen**: SQLite

**Why**:

* Zero-configuration embedded database
* Sufficient performance for single-user query logging
* Rich SQL querying capability for cost analysis
* No external dependencies
* Built into Python standard library

**Alternatives considered**:

* **Postgres**: Overkill for single-user logs
* **JSONL files**: Simple but worse query ergonomics
* **DuckDB**: Excellent for analytics but heavier for simple append-only logs

### 6.2 JSON / JSONL for Intermediate Storage

**Chosen**: JSON for structured source files, JSONL for chunk stream

**Why**:

* Human-readable for debugging
* Well-supported by all Python libraries
* Streaming-friendly (JSONL)
* Easy to diff and version-control (when needed)

---

## 7. Scraping and Parsing

### 7.1 httpx

**Chosen**: httpx

**Why**:

* Modern HTTP client with async support
* Better API than requests
* Built-in support for HTTP/2 and timeouts
* Handles redirects and retries cleanly

**Alternatives considered**:

* **requests**: Mature but synchronous and older API
* **aiohttp**: Async-first but more complex for simple scrapers

### 7.2 BeautifulSoup4 + lxml

**Chosen**: BeautifulSoup4 with lxml parser

**Why**:

* Forgiving HTML parsing (critical for real-world HTML)
* lxml backend gives good performance
* Standard choice in the Python scraping ecosystem

**Alternatives considered**:

* **lxml only**: Faster but less forgiving with messy HTML
* **Playwright**: Overkill for static HTML pages
* **Scrapy**: Framework-level, too heavy for our needs

---

## 8. Development Tooling

### 8.1 Ruff for Linting and Formatting

**Chosen**: Ruff

**Why**:

* 10-100× faster than Black, isort, flake8 combined
* Replaces multiple tools with one
* Actively developed, rapidly growing ecosystem
* Uniform code style with minimal configuration

**Alternatives considered**:

* **Black + isort + flake8**: Mature but slow and fragmented
* **pylint**: Comprehensive but slow

### 8.2 mypy for Type Checking

**Chosen**: mypy

**Why**:

* Most mature Python type checker
* Strong ecosystem of type stubs
* Deep integration with Pydantic

**Alternatives considered**:

* **pyright / pylance**: Faster, but mypy has better integration with Pydantic v2
* **pyre**: Meta's checker, smaller community

### 8.3 pytest for Testing

**Chosen**: pytest

**Why**:

* De facto standard for Python testing
* Plugin ecosystem (pytest-asyncio, pytest-cov, etc.)
* Clean fixture model

**Alternatives considered**:

* **unittest**: Standard library but more verbose
* **nose2**: Less active development

---

## 9. Version Control and Collaboration

### 9.1 Git + GitHub

**Chosen**: Git hosted on GitHub

**Why**:

* Universal developer tool
* GitHub provides free private and public repos
* Well-suited for portfolio visibility

**Alternatives considered**:

* **GitLab**: Comparable, smaller portfolio visibility
* **Bitbucket**: Comparable, smaller portfolio visibility

---

## 10. Stack Summary Table

| Layer | Component | Technology | Why |
|-------|-----------|------------|-----|
| Runtime | Language | Python 3.11+ | ML ecosystem, type hints |
| Runtime | Package manager | uv | Speed, unified tooling |
| LLM | API provider | Anthropic Claude | Quality + cost balance |
| LLM | Fast model | Claude Haiku | Cheap, fast, good enough |
| LLM | Smart model | Claude Sonnet | Reasoning depth |
| Retrieval | Vector DB | ChromaDB (embedded) | Zero ops, good for v1 |
| Retrieval | Embeddings | BAAI/bge-m3 | Free, strong, multilingual-ready |
| Retrieval | Sparse | rank-bm25 | Complements dense retrieval |
| App | CLI | Typer | Type-hint driven |
| App | Formatting | Rich | Beautiful terminal output |
| App | Models | Pydantic v2 | Industry standard, fast |
| App | Config | pydantic-settings | Typed config from .env |
| Data | Query logs | SQLite | Zero config, queryable |
| Scraping | HTTP | httpx | Modern, async-ready |
| Scraping | Parsing | BeautifulSoup4 + lxml | Forgiving, fast |
| Dev | Linting | Ruff | Fast, unified |
| Dev | Types | mypy | Pydantic compatibility |
| Dev | Tests | pytest | Standard, flexible |
| VCS | Repo host | GitHub | Portfolio visibility |

---

## 11. Deferred-to-v2 Stack Decisions

These choices are documented here for visibility but not implemented in v1:

### 11.1 Web Framework: FastAPI

For v2 HTTP API. Chosen for tight Pydantic integration and async performance.

### 11.2 Frontend: Next.js + Tailwind

For v2 web UI. Chosen for React ecosystem and fast iteration.

### 11.3 Container Orchestration: Docker + Compose

For v2 self-hosted deployment. Minimal overhead, wide familiarity.

### 11.4 Hosting: Hetzner VPS or AWS Fargate

For v2. Hetzner chosen as default for EU data residency and low cost.

### 11.5 CI/CD: GitHub Actions

For v2 automated testing and deployment.

### 11.6 Re-Ranker: bge-reranker-v2-m3

For v2 retrieval quality improvement.

---

## 12. Summary

The v1 stack is deliberately narrow: Python, Anthropic, ChromaDB, local embeddings, SQLite, a CLI, and strong dev tooling. Every component is chosen for either operational simplicity or best-in-class quality in its specific role. Costs are minimised by using local inference where possible and paying only for LLM reasoning calls.

The architecture is ready to absorb v2 extensions (FastAPI, web UI, re-ranking, hosting) without rearchitecting the core pipeline.

---

## v2 Stack Additions

| Component | v1 | v2 Addition |
|-----------|-----|-------------|
| Document generation | None (reports via pipeline only) | **Jinja2** templates rendering to **markdown** (DPIA, RoPA, checklist, consent, retention) |
| Persistence | Stateless runs + query log SQLite | **SQLite** via **aiosqlite** (or equivalent async driver) for projects, analyses, documents |
| API framework | FastAPI present in stack; HTTP deferred | **FastAPI** application exposing **v1** and **v2** routes on **localhost** |
| Input validation | Scenario string + length checks | **Pydantic v2** models for **system description** and **DataMap** |
| Template engine | None | **Jinja2** for regulatory-structure templates combined with assessment variables |

v2 does **not** introduce a new vector database: ChromaDB and **bge-m3** remain the embedding and retrieval stack; v2 adds **collections** and ingestion scripts for new source types (see data model and knowledge-base docs).