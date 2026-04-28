# ADR-003: English-Only Runtime

**Status**: Accepted
**Date**: 2026-04-21
**Deciders**: Project owner

---

## Context

GDPR AI targets the German market specifically. A significant portion of the knowledge base (BDSG, TTDSG, DSK guidance) is originally in German. The GDPR itself exists in all EU official languages.

The question: should the runtime system (input, output, retrieval) support multiple languages, or should it be monolingual?

Options:

1. **Bilingual (German + English)**: Accept input in either language, produce output in either, maintain the knowledge base in both.
2. **English-only**: All input, output, and indexed content in English.
3. **German-only**: All input, output, and indexed content in German.

---

## Decision

**English-only runtime for v1–v3.** German-first multilingual retrieval and UI are **v4** scope (see [Documentation README](../README.md) and [v4-overview.md](../v4-overview.md)). **v4** also prioritises a **Retrieval Gap Tracker** (KB expansion loop); that does not change the English-only **response** policy until multilingual work ships.

---

## Rationale

### Complexity Reduction

A single runtime language eliminates:

* Language detection at query time
* Multiple parallel chunk indices
* Cross-lingual retrieval tuning
* Duplicate prompt sets
* Runtime translation of outputs

This is a substantial reduction in v1 scope.

### English is the Working Language of EU Compliance

Most compliance work in the EU, including in Germany, is conducted at least partially in English:

* International teams work in English
* Most EDPB guidelines have English originals
* GDPR itself has an authoritative English version
* Cross-border DPA decisions often published in English

### Retrieval Quality

Multilingual retrieval with dense embeddings works, but not as well as monolingual retrieval. By translating German sources to English at indexing time, we avoid retrieval quality penalties at query time.

### One-Time Translation is Cheaper than Runtime Translation

Translating BDSG, TTDSG, and DSK once during indexing costs approximately 2-5 EUR total. Translating at query time would cost ~0.005 EUR per query — not expensive, but adds latency and complexity.

### Faster Path to v1

A monolingual v1 ships weeks sooner than a bilingual one. Shipping v1 unlocks real usage feedback, which informs better design for v2.

---

## Consequences

### Positive

* Dramatically simpler v1 architecture
* Higher retrieval quality (monolingual dense retrieval)
* Lower per-query cost
* Faster development

### Negative

* German users must read English reports
* German scenarios must be re-stated in English
* Some legal nuance may be lost in translation of source material
* Less accessible to non-English-proficient users

### Mitigated Risks

* **English comprehension**: EU compliance professionals typically read English
* **Translation nuance**: translations spot-checked against originals for legal terms; original German retained in metadata
* **Accessibility**: **v4** will add German-first multilingual UI and retrieval, plus **retrieval gap** visibility to improve grounding over time (see [v4-overview.md](../v4-overview.md))

---

## Alternatives Considered

### Bilingual from Day One

Rejected because it doubles complexity in nearly every pipeline stage for a modest increase in user reach in v1's single-user context.

### German-Only

Rejected because:

* English GDPR is authoritative for European Union
* International users would be excluded
* English-language LLMs are generally stronger than German-only approaches for nuanced reasoning

### Cross-Lingual Retrieval (bge-m3 supports this natively)

Considered. bge-m3 is designed for cross-lingual retrieval, and this path remains open for **v4**. For v1, the additional tuning effort and retrieval quality risk did not justify the complexity.

---

## Follow-Up Actions

* Knowledge base built with German sources translated to English (see ADR-004)
* CLI accepts and produces only English
* **v4** roadmap includes **Retrieval Gap Tracker** (priority 1), then multilingual UI and retrieval (German-first), document upload, and website scanning — see [v4-roadmap.md](../v4-roadmap.md)