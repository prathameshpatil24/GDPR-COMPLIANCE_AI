# Phase 3.16 – Knowledge Base Schema Design

## 1. Overview

This document defines the concrete data schemas used across the knowledge base pipeline — from scraped raw data through chunks to ChromaDB records. It is the implementation-level complement to [10 – Data and Knowledge Model](../phase-2-architecture/10-data-knowledge-model.md).

All schemas are Pydantic models, which means runtime validation, JSON serialisation, and automatic documentation are all free.

---

## 2. Raw Scraped Data Schemas

### 2.1 GDPR Article (raw)

```python
class GDPRArticleRaw(BaseModel):
    article_number: int              # 1..99
    title: str                       # "Lawfulness of processing"
    paragraphs: list[GDPRParagraph]
    source_url: str

class GDPRParagraph(BaseModel):
    number: str                      # "1", "1(a)", "2"
    text: str
    sub_paragraphs: list[GDPRSubParagraph] = []

class GDPRSubParagraph(BaseModel):
    letter: str                      # "a", "b", "c"
    text: str
```

File: `data/raw/gdpr/articles.json`

### 2.2 GDPR Recital (raw)

```python
class GDPRRecitalRaw(BaseModel):
    number: int                      # 1..173
    text: str
    source_url: str
```

File: `data/raw/gdpr/recitals.json`

### 2.3 BDSG / TTDSG Section (raw)

```python
class GermanSectionRaw(BaseModel):
    section_number: str              # "§ 26"
    title_de: str                    # German original title
    subsections: list[GermanSubsection]
    source_url: str
    source_law: Literal["BDSG", "TTDSG"]

class GermanSubsection(BaseModel):
    number: str                      # "(1)", "(2)"
    text_de: str                     # German original
```

Files: `data/raw/bdsg/sections.json`, `data/raw/ttdsg/sections.json`

### 2.4 EDPB Guideline (raw)

```python
class EDPBGuidelineRaw(BaseModel):
    guideline_id: str                # "05/2020"
    title: str
    sections: list[EDPBSection]
    source_url: str
    published_date: str              # ISO date

class EDPBSection(BaseModel):
    heading: str
    text: str
    page_reference: str | None
```

File: `data/raw/edpb/guidelines/<guideline_id>.json`

### 2.5 DSK Kurzpapier (raw)

```python
class DSKPaperRaw(BaseModel):
    paper_id: str                    # slug
    title_de: str
    sections: list[DSKSection]
    source_url: str

class DSKSection(BaseModel):
    heading_de: str
    text_de: str
```

File: `data/raw/dsk/<paper_id>.json`

### 2.6 GDPRhub Case (raw)

```python
class GDPRhubCaseRaw(BaseModel):
    case_id: str
    case_name: str
    country: str
    dpa_or_court: str
    decision_date: str               # ISO date
    articles_cited: list[str]        # ["Art. 5", "Art. 32"]
    fine_amount_eur: int | None
    summary_text: str                # GDPRhub's original summary
    facts: str
    outcome: str
    source_url: str
    license: Literal["CC-BY-NC-SA-4.0"]
```

File: `data/raw/gdprhub/cases/<case_id>.json`

### 2.7 Enforcement Tracker Fine (raw)

```python
class EnforcementFineRaw(BaseModel):
    fine_id: str
    company: str
    country: str
    decision_date: str               # ISO date
    fine_amount_eur: int
    articles_cited: list[str]
    sector: str
    source_url: str
```

File: `data/raw/enforcement_tracker/fines.json`

---

## 3. Translated Data Schemas (for German sources)

### 3.1 Translated BDSG / TTDSG Section

```python
class GermanSectionTranslated(BaseModel):
    section_number: str
    title_en: str                    # English translation
    title_de: str                    # kept for traceability
    subsections: list[GermanSubsectionTranslated]
    source_url: str
    source_law: Literal["BDSG", "TTDSG"]
    translation_metadata: TranslationMetadata

class GermanSubsectionTranslated(BaseModel):
    number: str
    text_en: str
    text_de: str

class TranslationMetadata(BaseModel):
    translator_model: str            # "claude-haiku-4-5-20251001"
    translated_at: datetime
    spot_check_status: Literal["verified", "pending", "issue"] = "pending"
    spot_check_notes: str | None = None
```

File: `data/processed/translated/bdsg.json`

### 3.2 Translated DSK Paper

```python
class DSKPaperTranslated(BaseModel):
    paper_id: str
    title_en: str
    title_de: str
    sections: list[DSKSectionTranslated]
    source_url: str
    translation_metadata: TranslationMetadata

class DSKSectionTranslated(BaseModel):
    heading_en: str
    heading_de: str
    text_en: str
    text_de: str
```

File: `data/processed/translated/dsk/<paper_id>.json`

---

## 4. Chunk Schema (canonical)

This is the single source of truth for what a chunk looks like before it enters ChromaDB.

```python
class Chunk(BaseModel):
    # Identity
    chunk_id: str                    # UUID
    source: SourceType
    chunk_version: int = 1

    # Text content
    text: str                        # the actual text (English in v1)

    # Legal identifier
    article_or_section: str          # "Art. 6", "§ 26", "Guideline 05/2020"
    paragraph: str | None            # "1(a)", "2", None for recitals
    full_citation: str               # "Art. 6(1)(a) GDPR", "BDSG § 26(1)"

    # Source traceability
    source_url: str
    source_publisher: str
    license: LicenseType
    original_language: Literal["en", "de"]
    kb_language: Literal["en"] = "en"
    translated: bool = False

    # Retrieval aids
    topic_tags: list[str]            # from fixed taxonomy
    related_articles: list[str] = []
    related_recitals: list[str] = []

    # Case-specific (None for non-case chunks)
    case_name: str | None = None
    dpa_or_court: str | None = None
    fine_amount_eur: int | None = None
    sector: str | None = None
    decision_date: str | None = None

    # Operational
    indexed_at: datetime

class SourceType(str, Enum):
    GDPR = "gdpr"
    GDPR_RECITAL = "gdpr_recital"
    BDSG = "bdsg"
    TTDSG = "ttdsg"
    EDPB = "edpb"
    DSK = "dsk"
    BFDI = "bfdi"
    BAYLDA = "baylda"
    LFDI_BW = "lfdi_bw"
    GDPRHUB = "gdprhub"
    ENFORCEMENT_TRACKER = "enforcement_tracker"

class LicenseType(str, Enum):
    PUBLIC_DOMAIN = "public-domain"
    EU_REUSE_POLICY = "eu-reuse-policy"
    CC_BY_NC_SA_4 = "CC-BY-NC-SA-4.0"
    FREE_WITH_ATTRIBUTION = "free-with-attribution"
    GERMAN_PUBLIC_LAW = "german-public-law"
```

File: `data/processed/chunks.jsonl` — one JSON object per line.

---

## 5. ChromaDB Record Format

ChromaDB accepts only primitive types in metadata (str, int, float, bool — no nested objects or lists of objects). Therefore the `Chunk` is flattened before insertion.

### 5.1 Flattening Rules

* `topic_tags`: joined with commas → single string
* `related_articles`: joined with commas → single string
* `related_recitals`: joined with commas → single string
* `indexed_at`: converted to ISO string
* `None` values: converted to empty string (for string fields) or 0 (for int fields)

### 5.2 Flattened Record

```python
{
    "id": "chunk_id_uuid",
    "document": "chunk.text",                    # the text
    "embedding": [float, ...],                    # 1024-dim bge-m3
    "metadata": {
        "source": "gdpr",
        "chunk_version": 1,
        "article_or_section": "Art. 6",
        "paragraph": "1(a)",
        "full_citation": "Art. 6(1)(a) GDPR",
        "source_url": "https://eur-lex.europa.eu/eli/reg/2016/679/oj",
        "source_publisher": "European Union",
        "license": "public-domain",
        "original_language": "en",
        "kb_language": "en",
        "translated": False,
        "topic_tags": "legal-basis,consent",
        "related_articles": "7,8",
        "related_recitals": "32,42,43",
        "case_name": "",
        "dpa_or_court": "",
        "fine_amount_eur": 0,
        "sector": "",
        "decision_date": "",
        "indexed_at": "2026-04-21T20:00:00Z",
    }
}
```

---

## 6. BM25 Index Format

The BM25 index is stored alongside ChromaDB as a pickled object.

```python
@dataclass
class BM25Index:
    bm25: BM25Okapi                   # the BM25 model
    chunk_ids: list[str]              # parallel list of chunk IDs
    tokenised_docs: list[list[str]]   # tokenised chunk texts
    version: int                      # bumped when tokenisation changes

# Saved as: data/processed/bm25.pkl
```

To retrieve: score all chunks, take top k, look up the corresponding `chunk_id`s, then fetch full chunks from ChromaDB by those IDs.

---

## 7. SQLite Schema

### 7.1 Query Log Table

```sql
CREATE TABLE IF NOT EXISTS query_log (
    query_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,

    -- Input
    scenario TEXT NOT NULL,

    -- Pipeline intermediates (JSON-encoded)
    entities_json TEXT,
    topics_json TEXT,
    retrieved_chunk_ids TEXT,         -- comma-separated UUIDs

    -- Output
    report_json TEXT,

    -- Metrics
    latency_ms_total INTEGER,
    latency_ms_extract INTEGER,
    latency_ms_classify INTEGER,
    latency_ms_retrieve INTEGER,
    latency_ms_reason INTEGER,
    latency_ms_validate INTEGER,

    -- Tokens
    tokens_input_haiku INTEGER,
    tokens_output_haiku INTEGER,
    tokens_input_sonnet INTEGER,
    tokens_output_sonnet INTEGER,

    -- Cost
    cost_eur REAL,

    -- Outcome
    status TEXT,                      -- "ok", "hallucination_retry_ok", "failed"
    error_type TEXT,

    -- Feedback (nullable, updated later)
    feedback_rating TEXT,             -- "up", "down", NULL
    feedback_comment TEXT
);

CREATE INDEX idx_query_log_timestamp ON query_log(timestamp);
CREATE INDEX idx_query_log_cost ON query_log(cost_eur);
CREATE INDEX idx_query_log_feedback ON query_log(feedback_rating);
```

### 7.2 Cost Summary View

```sql
CREATE VIEW IF NOT EXISTS cost_by_day AS
SELECT
    DATE(timestamp) AS day,
    COUNT(*) AS query_count,
    SUM(cost_eur) AS total_cost_eur,
    AVG(cost_eur) AS avg_cost_eur,
    AVG(latency_ms_total) AS avg_latency_ms
FROM query_log
GROUP BY DATE(timestamp)
ORDER BY day DESC;
```

---

## 8. File System Layout Summary

```
data/
├── raw/                              # scraped originals, regeneratable
│   ├── gdpr/articles.json
│   ├── gdpr/recitals.json
│   ├── bdsg/sections.json
│   ├── ttdsg/sections.json
│   ├── edpb/guidelines/*.json
│   ├── dsk/*.json
│   ├── gdprhub/cases/*.json
│   └── enforcement_tracker/fines.json
│
├── processed/                        # cleaned and enriched
│   ├── translated/
│   │   ├── bdsg.json
│   │   ├── ttdsg.json
│   │   └── dsk/*.json
│   ├── chunks.jsonl                  # canonical chunk stream
│   └── bm25.pkl                      # pickled BM25 index
│
├── chroma/                           # ChromaDB persistent storage
│   └── <chroma's internal files>
│
└── gdpr_ai.db                        # SQLite query log
```

All `data/` subdirectories are gitignored.

---

## 9. Versioning and Migration

### 9.1 Chunk Version

`chunk_version` field supports schema evolution. When chunking logic changes in a non-backward-compatible way, the version is bumped, and the knowledge base must be rebuilt.

### 9.2 BM25 Version

The pickled BM25 file carries a version number. If tokenisation or corpus changes, the version is incremented, and callers must rebuild.

### 9.3 SQLite Migrations

For v1, the SQLite schema is created on first run. For v2, an Alembic-style migration system may be added as the schema evolves.

---

## 10. Summary

The knowledge base schema is designed for traceability (every chunk knows its source, URL, and license), retrieval efficiency (flat metadata for ChromaDB filtering, parallel BM25 index), and cost observability (SQLite query log with per-stage metrics).

All schemas are Pydantic models with strict validation, ensuring that malformed data is caught at ingestion rather than at query time.

---

## v2 Knowledge Base Expansion

### New sources to scrape, translate where needed, chunk, and embed

* EDPB **DPIA** guidance (Guidelines on Data Protection Impact Assessment, WP 248 rev.01 and successors)
* EDPB **consent** guidelines (05/2020 and related)
* EDPB **legitimate interests** assessment materials
* **Article 30** RoPA requirements and supervisory authority exemplars
* **BSI IT-Grundschutz** (or equivalent) **TOM** catalogues mapped to GDPR security and organisational articles — English summaries where primary materials are German
* **EU AI Act** — articles most relevant to **personal data** processing alignment (for example Arts. 10, 13, 14, 26, 27 — exact set frozen at implementation time)
* Sample **DPIA** publications from supervisory authorities (BfDI, CNIL, ICO) where licence permits indexing and attribution

### Collection layout

* **v1 chunks remain** in the existing corpus; v2 adds **additional ChromaDB collections** (or the same collection with a discriminating `collection` / `source_family` metadata field — implementation choice documented at build time).
* **Shared embedding model:** `BAAI/bge-m3` (same as v1) for cross-retrieval between legal text and guidance.
* **Attribution:** every new chunk carries `source`, `url`, `license` consistent with [10 – Data and Knowledge Model](../phase-2-architecture/10-data-knowledge-model.md).

### Chunk metadata extensions (implementation)

Extend `SourceType` / topic tags as needed for `dpia_guidance`, `ropa_templates`, `tom_catalog`, `consent_guidance`, `ai_act_crossref` without breaking existing v1 filters (additive enum values and tags only).