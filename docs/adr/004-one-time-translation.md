# ADR-004: One-Time Translation of German Sources at Index Time

**Status**: Accepted
**Date**: 2026-04-21
**Deciders**: Project owner

---

## Context

Following [ADR-003](003-english-only-runtime.md), the runtime is English-only. German-language source material (BDSG, TTDSG, DSK Kurzpapiere, BfDI / BayLDA / LfDI BW guidance) must be handled.

Three approaches:

1. **Exclude German sources**: simpler, but loses the German-market specialisation that differentiates GDPR AI.
2. **Translate at query time**: fetch German content at query time and translate on-demand.
3. **Translate once at index time**: translate German content during the knowledge-base build, store English versions, index English.

---

## Decision

**Translate German sources once during index build. Store English translations alongside originals. Index English versions only.**

---

## Rationale

### Cost

Translating once: approximately 2-5 EUR total using Claude Haiku for approximately 100K tokens of German content.

Translating at query time: approximately 0.005 EUR per query for ~2 German chunks among the retrieved 15. At 10 queries per day, that is 0.15 EUR/month — small, but unnecessarily recurring.

### Latency

Translating at query time adds 500-1500ms of LLM call latency per query. Translating once adds zero query-time latency.

### Retrieval Quality

Translating at query time means the dense retrieval happens over mixed-language content (English queries against German chunks), which degrades quality.

Translating at index time means all retrieval happens monolingually in English, delivering best-in-class retrieval quality.

### Quality Control

One-time translation allows spot-checking. A human can verify translations of key legal terms (e.g., "Beschäftigtendatenschutz" → "employee data protection", "Auftragsverarbeitung" → "processing on behalf") before the knowledge base goes live.

Query-time translation provides no opportunity for verification.

### Preserving Originals

Translated versions are stored alongside originals. If a translation issue is discovered, we can:

* Fix the translation without re-fetching
* Retain the original for authoritative reference
* Show the original German in disclaimers

---

## Consequences

### Positive

* Zero query-time translation cost after the one-time build
* Best retrieval quality (monolingual)
* Opportunity to verify translations before they affect users
* Translations are version-controlled and can be improved incrementally

### Negative

* Translation errors propagate until fixed
* Requires a translation pipeline as a project component
* Adds a phase to the build process

### Mitigated Risks

* **Translation errors**: spot-check protocol verifies samples against originals; disclaimer notes translations are non-authoritative
* **Legal term accuracy**: focus list of key terms manually verified against BDSG official translations where available
* **Updates to German source material**: re-translation triggered by content hash change

---

## Alternatives Considered

### Use Existing English Translations Where Available

Considered. The Federal Ministry of Justice publishes an official English BDSG translation. This could be used instead of machine translation.

Partially adopted: the official English translation is used as the reference for spot-checking machine translations. Not adopted wholesale because:

* Not all German sources have official English versions (DSK does not)
* Using a mix of official and machine translations creates inconsistency
* Licensing of official translations varies

### Bilingual Indexing (German + English)

Considered. Index both German and English versions of each chunk. Use cross-lingual retrieval (bge-m3 supports this).

Rejected for v1 because:

* Doubles chunk count
* Runtime language detection adds complexity
* Contradicts ADR-003's simplification goals

Appropriate for v2.

### Translate at First Use, Cache

Lazy translation: translate a chunk only when it is first retrieved, then cache. Rejected because:

* First queries become slow until cache warms
* Adds runtime complexity
* Savings are minimal given the small total corpus

---

## Implementation Notes

### Translation Model

Claude Haiku is chosen for translation because:

* Cheap enough for bulk translation
* Strong enough for legal-term accuracy in most cases
* Consistent with the rest of the pipeline's Anthropic dependency

For particularly sensitive terms (penalties, definitions), Sonnet could be used selectively.

### Translation Prompt

The translation prompt explicitly:

* Preserves legal citations verbatim
* Uses authoritative English legal terminology where available
* Retains paragraph structure and numbering
* Does not paraphrase

### Storage

Translations stored in `data/processed/translated/` with full traceability (original German, English translation, translator model, translation date, spot-check status).

---

## Follow-Up Actions

* `scripts/translate_german_sources.py` implements the one-time pipeline
* `TranslationMetadata` schema captures translator model and spot-check status
* Spot-check protocol documented in the testing strategy
* Re-translation triggered only on content hash change