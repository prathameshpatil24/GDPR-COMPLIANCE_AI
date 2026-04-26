# Phase 2.10 – Data and Knowledge Model Design

## 1. Overview

The knowledge base is the single most important asset of GDPR AI. Retrieval quality depends entirely on how source text is chunked, what metadata is attached, and how the data is organised for efficient query-time filtering.

This document defines the chunking strategy, metadata schema, topic taxonomy, and storage structure.

---

## 2. Data Sources and Raw Form

### 2.1 Sources

| Source | Original Format | Language | Volume |
|--------|-----------------|----------|--------|
| GDPR | HTML (EUR-Lex) | English | 99 articles, 173 recitals |
| BDSG | HTML (gesetze-im-internet.de) | German | ~80 sections |
| TTDSG | HTML (gesetze-im-internet.de) | German | ~30 sections |
| EDPB Guidelines | PDF / HTML | English | ~30 documents |
| DSK Kurzpapiere | PDF | German | ~20 documents |
| GDPRhub | HTML (MediaWiki) | English | 50-100 cases |
| Enforcement Tracker | HTML table | English | 500+ fine entries (metadata) |

### 2.2 Raw Storage Layout

```
data/raw/
├── gdpr/
│   ├── articles.json        # all articles, structured
│   └── recitals.json        # all recitals, structured
├── bdsg/
│   └── sections.json        # German original
├── ttdsg/
│   └── sections.json        # German original
├── edpb/
│   └── guidelines/
│       └── <guideline_id>.json
├── dsk/
│   └── <paper_id>.json      # German original
├── gdprhub/
│   └── cases/
│       └── <case_id>.json
└── enforcement_tracker/
    └── fines.json
```

Raw files preserve the original structure as much as possible, so re-chunking doesn't require re-scraping.

---

## 3. Chunking Strategy

### 3.1 Principles

* Each chunk should be a self-contained semantic unit
* Chunks should match the granularity at which citations are made
* Chunk size should fit comfortably in LLM context (300-800 tokens target)
* Chunks should preserve cross-references to related articles

### 3.2 Chunking Rules per Source

#### 3.2.1 GDPR Articles

Each article paragraph is a separate chunk. This means `Article 6(1)(a)` is its own chunk, distinct from `Article 6(1)(b)`.

* Chunk text: the paragraph text itself
* Minimum size: 30 tokens (below, merge with adjacent paragraph)
* Maximum size: 600 tokens (above, split on sentence boundaries)

#### 3.2.2 GDPR Recitals

Each recital is one chunk.

* Recitals are short (typically 50-200 tokens)
* No further splitting needed

#### 3.2.3 BDSG and TTDSG

Each section (§) is one chunk. If a section is very long, split on subsection boundaries (§26(1), §26(2), etc.).

#### 3.2.4 EDPB Guidelines

Each guideline is split into semantic sections (headers in the document). Aim for 300-800 token chunks.

#### 3.2.5 DSK Kurzpapiere

Each paper becomes a single chunk if short, or split by section if longer than 800 tokens.

#### 3.2.6 GDPRhub Cases

Each case is summarised to approximately 300 tokens. The summary includes:

* Case name
* DPA or court
* Facts (2-3 sentences)
* Articles cited
* Fine amount
* Outcome

#### 3.2.7 Enforcement Tracker

Each fine entry is a single structured chunk:

* Company name
* Country
* Date
* Fine amount
* Articles cited
* Sector

---

## 4. Chunk Metadata Schema

Every chunk in ChromaDB carries this metadata structure.

```python
class ChunkMetadata(BaseModel):
    # Identity
    chunk_id: str                  # UUID
    source: Literal[
        "gdpr", "bdsg", "ttdsg",
        "edpb", "dsk", "bfdi",
        "baylda", "lfdi_bw",
        "gdprhub", "enforcement_tracker"
    ]

    # Legal identifier
    article_or_section: str        # e.g., "Art. 6", "§ 26", "Guideline 05/2020"
    paragraph: str | None          # e.g., "1(a)", "2"
    full_citation: str             # e.g., "Art. 6(1)(a) GDPR"

    # Source traceability
    source_url: str                # original URL
    source_publisher: str          # e.g., "European Union", "noyb"
    license: str                   # e.g., "public-domain", "CC-BY-NC-SA-4.0"
    original_language: Literal["en", "de"]
    kb_language: Literal["en"]     # always English in v1
    translated: bool               # True if originally German

    # Retrieval aids
    topic_tags: list[str]          # from fixed taxonomy
    related_articles: list[str]    # cross-references
    related_recitals: list[str]

    # Case-specific (for GDPRhub and Enforcement Tracker)
    case_name: str | None
    dpa_or_court: str | None
    fine_amount_eur: int | None
    sector: str | None

    # Operational
    indexed_at: datetime
    chunk_version: int             # for migrations
```

---

## 5. Topic Taxonomy

The fixed topic taxonomy constrains the classification stage. It partitions GDPR scenarios into retrieval-friendly buckets.

### 5.1 Taxonomy

```
├── legal-basis
│   ├── consent                   # Art. 6(1)(a), 7, 8
│   ├── contract                  # Art. 6(1)(b)
│   ├── legal-obligation          # Art. 6(1)(c)
│   ├── vital-interests           # Art. 6(1)(d)
│   ├── public-task               # Art. 6(1)(e)
│   └── legitimate-interest       # Art. 6(1)(f)
│
├── special-categories            # Art. 9
│
├── data-subject-rights
│   ├── information               # Art. 13, 14
│   ├── access                    # Art. 15
│   ├── rectification             # Art. 16
│   ├── erasure                   # Art. 17
│   ├── restriction               # Art. 18
│   ├── portability               # Art. 20
│   ├── object                    # Art. 21
│   └── automated-decisions       # Art. 22
│
├── controller-processor
│   ├── responsibility            # Art. 24
│   ├── privacy-by-design         # Art. 25
│   ├── joint-controllers         # Art. 26
│   ├── processor-obligations     # Art. 28
│   ├── records                   # Art. 30
│
├── security-and-breaches
│   ├── security-of-processing    # Art. 32
│   ├── notification-to-dpa       # Art. 33
│   └── notification-to-subjects  # Art. 34
│
├── dpia-and-dpo
│   ├── dpia                      # Art. 35
│   ├── prior-consultation        # Art. 36
│   └── dpo                       # Art. 37, 38, 39
│
├── transfers                     # Art. 44-50
│
├── employment                    # BDSG § 26
│
├── children                      # Art. 8
│
├── direct-marketing              # Art. 21, ePrivacy
│
└── telemedia                     # TTDSG
```

### 5.2 Tag Assignment Rules

* Each chunk is tagged with 1 to 4 taxonomy nodes
* Tagging is performed during chunking, not at query time
* Child nodes inherit parent tags (a chunk tagged `consent` is also retrievable via `legal-basis`)

---

## 6. Storage in ChromaDB

### 6.1 Collection Design

Single collection named `gdpr_ai_chunks`.

Rationale: with ~3000 chunks, a single collection is performant. Metadata filtering handles partitioning without the complexity of multiple collections.

### 6.2 Chroma Record Format

```python
{
    "id": chunk_id,                    # UUID
    "embedding": [float, ...],          # 1024-dim bge-m3 vector
    "document": chunk_text,             # the actual text
    "metadata": {
        # Flat metadata for Chroma filtering
        "source": "gdpr",
        "article": "Art. 6",
        "paragraph": "1(a)",
        "full_citation": "Art. 6(1)(a) GDPR",
        "source_url": "https://eur-lex.europa.eu/...",
        "license": "public-domain",
        "topic_tags": "legal-basis,consent",  # comma-joined for Chroma
        "related_articles": "7,8",
        "case_name": "",
        "fine_amount_eur": 0,
        "indexed_at": "2026-04-21T20:00:00Z",
        "chunk_version": 1
    }
}
```

### 6.3 Indexing Strategy

* ChromaDB uses HNSW by default for approximate nearest-neighbour search
* Default parameters are sufficient for 10K-scale collections
* No need to tune HNSW parameters in v1

---

## 7. BM25 Index

### 7.1 Separate Index

BM25 operates on the raw chunk text, not embeddings. It is maintained separately from ChromaDB.

### 7.2 Implementation

* Stored as a pickled `rank_bm25.BM25Okapi` object in `data/processed/bm25.pkl`
* Rebuilt whenever ChromaDB is rebuilt
* Tokenisation: lowercase + whitespace split + basic punctuation stripping
* No stopword removal (legal text relies on precise wording including common words)

### 7.3 Retrieval

At query time:

1. Tokenise the query
2. Score all chunks via `bm25.get_scores(tokenised_query)`
3. Return top N

---

## 8. Hybrid Retrieval Scoring

### 8.1 Score Combination

Dense and sparse scores are combined via normalised sum:

```
final_score = 0.5 * normalise(dense_score) + 0.5 * normalise(bm25_score)
```

Normalisation: min-max scaling to [0, 1] within the result set.

Weights (0.5 / 0.5) are starting defaults. Tuned against the gold set during Phase G.

### 8.2 Pre-Filtering

Before scoring, apply metadata filters:

* If classification produced 2 topic tags, only chunks with at least one matching tag are considered
* If jurisdiction is Germany-specific, BDSG and TTDSG chunks are boosted
* If scenario mentions special categories, Art. 9 chunks are boosted

---

## 9. Translation Data Flow

### 9.1 German Sources

BDSG, TTDSG, DSK, BfDI, BayLDA, LfDI BW are translated from German to English during indexing.

### 9.2 Translation Storage

```
data/processed/translated/
├── bdsg.json             # English translations with metadata
├── ttdsg.json
├── dsk/
│   └── <paper_id>.json
└── ...
```

Each translated entry retains:

* `original_text_german`
* `translated_text_english`
* `translator`: "claude-haiku"
* `translation_date`
* `spot_check_status`: "verified" | "pending" | "issue"

### 9.3 Re-Translation Triggers

Re-translation runs only when:

* Source text has changed (hash comparison)
* A spot-check has flagged an issue

This keeps ongoing costs minimal.

---

## 10. Data Quality Controls

### 10.1 Chunk Completeness

Every chunk must have:

* Non-empty text
* Valid source identifier
* At least one topic tag
* Source URL
* License identifier

Missing any of these → the chunk is rejected during indexing and logged.

### 10.2 Deduplication

Chunks are deduplicated by exact text match before embedding. Near-duplicates (e.g., paraphrased guidance) are kept separate to preserve nuance.

### 10.3 Integrity Check

`scripts/verify_knowledge_base.py` runs a health check:

* Expected chunk counts per source
* All metadata fields present
* Sample retrievals return plausible results
* No orphan chunks (metadata without a Chroma entry or vice versa)

---

## 11. Versioning and Migration

### 11.1 Chunk Versioning

Every chunk carries a `chunk_version` field. When chunking logic changes, the version is bumped and the knowledge base is rebuilt.

### 11.2 Rebuild Strategy

Full rebuilds are supported via `scripts/rebuild_knowledge_base.py`. This:

1. Re-scrapes sources (or uses cached raw data)
2. Re-chunks with current chunking rules
3. Re-embeds
4. Rebuilds ChromaDB collection
5. Rebuilds BM25 index

### 11.3 Delta Updates

For incremental updates (e.g., new GDPRhub cases):

1. Fetch only new or changed source data
2. Chunk the new data
3. Embed and add to existing collection
4. Update BM25 index in place

---

## 12. Summary

The data model is structured for both retrieval efficiency and traceability. Paragraph-level chunking preserves sub-clause precision. Rich metadata enables filtered retrieval. The fixed taxonomy constrains classification. Hybrid retrieval combines dense semantic similarity with sparse keyword matching. Translation of German sources happens once during indexing, keeping runtime costs minimal.

Every chunk is traceable to its source, its license, and its legal identifier — supporting both accuracy and the licensing obligations defined in the project's constraint set.

---

## v2 Data Model Extension

### New ChromaDB collections (v2)

v1 may use a single logical collection or partitioned metadata; v2 **adds** dedicated collections (or metadata partitions) for compliance artefacts:

| Collection key | Contents |
|----------------|----------|
| `dpia_guidance` | EDPB DPIA guidance, template structures, example assessment patterns |
| `ropa_templates` | RoPA field definitions, example entries, Article 30 requirements |
| `tom_catalog` | Technical and organisational measures catalog, mapped to GDPR articles |
| `consent_guidance` | EDPB consent guidelines, legitimate-interest assessment framing |
| `ai_act_crossref` | EU AI Act articles relevant to GDPR data-protection obligations |

Indexing uses the same **bge-m3** embedding model as v1 for consistent retrieval.

### SQLite schema (user projects and documents)

```sql
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    system_description JSON NOT NULL,
    data_map JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE analyses (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    mode TEXT NOT NULL CHECK(mode IN ('violation_analysis', 'compliance_assessment')),
    input_text TEXT,
    result JSON NOT NULL,
    llm_cost_usd REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE documents (
    id TEXT PRIMARY KEY,
    analysis_id TEXT NOT NULL REFERENCES analyses(id),
    doc_type TEXT NOT NULL CHECK(doc_type IN ('dpia', 'ropa', 'checklist', 'consent_flow', 'retention_policy', 'violation_report')),
    content TEXT NOT NULL,
    format TEXT NOT NULL DEFAULT 'markdown',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### DataMap schema (Pydantic)

```python
class DataCategory(BaseModel):
    name: str                        # e.g., "email addresses", "IP addresses"
    sensitivity: str                 # "standard" | "special_category" | "criminal"
    volume: str                      # "low" | "medium" | "high"
    subjects: list[str]              # e.g., ["customers", "employees"]


class ProcessingPurpose(BaseModel):
    purpose: str                     # e.g., "marketing emails", "analytics"
    legal_basis_claimed: str | None  # e.g., "consent", "legitimate_interest"
    data_categories: list[str]       # references to DataCategory names


class DataFlow(BaseModel):
    source: str                      # e.g., "web form", "API", "third-party"
    destination: str                 # e.g., "PostgreSQL", "analytics provider"
    data_categories: list[str]
    crosses_border: bool
    destination_country: str | None


class ThirdParty(BaseModel):
    name: str
    role: str                        # "processor" | "joint_controller" | "independent_controller"
    purpose: str
    dpa_in_place: bool | None        # Data Processing Agreement
    country: str | None


class StorageInfo(BaseModel):
    location: str                    # e.g., "AWS eu-central-1", "local server"
    country: str
    encryption_at_rest: bool | None
    encryption_in_transit: bool | None
    retention_period: str | None     # e.g., "30 days", "2 years", "indefinite"


class DataMap(BaseModel):
    system_name: str
    system_description: str
    data_categories: list[DataCategory]
    processing_purposes: list[ProcessingPurpose]
    data_flows: list[DataFlow]
    third_parties: list[ThirdParty]
    storage: list[StorageInfo]
    has_automated_decision_making: bool
    processes_children_data: bool
    uses_ai_ml: bool
```