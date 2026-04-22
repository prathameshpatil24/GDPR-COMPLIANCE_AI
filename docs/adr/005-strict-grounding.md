# ADR-005: Strict Grounding Over Generation Fluency

**Status**: Accepted
**Date**: 2026-04-21
**Deciders**: Project owner

---

## Context

A core tension in every RAG system: should the LLM be allowed to supplement retrieved content with its general knowledge, or should it be forbidden from doing so?

For GDPR AI, this tension is sharp:

* General-purpose Claude knows a lot about GDPR from training data
* Training-data knowledge is potentially outdated or inaccurate
* Hallucinated article numbers are a primary failure mode of generic LLMs
* User trust depends on outputs being traceable to source

Two philosophies:

1. **Permissive**: Use retrieved chunks as helpful context but allow the LLM to add surrounding knowledge, producing more fluent, expert-sounding outputs.

2. **Strict grounding**: Constrain the LLM to cite only retrieved chunks. Reject any output that cites articles not present in the retrieval set.

---

## Decision

**Adopt strict grounding. No article number appears in a report unless it was present in a retrieved chunk for that specific query.**

---

## Rationale

### Hallucinations are the Primary Failure Mode

In a legal-reasoning tool, an invented article number is worse than saying nothing. A user who sees "Article 47 GDPR" cited for consent (when Article 47 actually covers Binding Corporate Rules) is worse off than a user who sees "no matching article identified."

Strict grounding eliminates this failure mode entirely.

### Trust and Verification

Every claim in a grounded output can be traced back to a source URL in the chunk metadata. Users can verify any citation against the authoritative source. This is impossible with permissive generation.

### Differentiation from Generic Chatbots

Generic LLMs produce confident-sounding but unreliable GDPR analysis. The primary differentiator of GDPR AI is that its claims are traceable and verifiable. Strict grounding is this differentiator made operational.

### Retrieval as Quality Gate

Strict grounding turns retrieval quality into the upper bound of end-to-end quality. This is actually desirable — we can improve retrieval (chunking, embeddings, filtering) as a separate, measurable concern, without the LLM "covering up" retrieval gaps by drawing from training data.

### Predictable Behaviour

When the retrieval misses, the system says so rather than making up plausible-sounding answers. This is auditable and debuggable — we can trace every "no violation identified" output to a retrieval gap and expand the gold set accordingly.

---

## How It Is Enforced

### Prompt Engineering

The reason-stage system prompt explicitly forbids ungrounded citations:

> "You may cite only articles that appear in the retrieved chunks below. If an article is not in the retrieved chunks, do not mention it."

### Validation Layer

After the LLM produces a draft report, a deterministic validator checks:

* Every cited article number is present in the retrieved chunks' metadata
* Every source URL matches a retrieved chunk

If validation fails, the draft is rejected. The reason stage is retried once. If the second attempt also fails validation, the system returns an error rather than presenting an ungrounded report.

### Structured Output

The report schema forces structure that ties every claim to a source (`article`, `source_url`). There is no free-form paragraph that could smuggle in ungrounded content.

---

## Consequences

### Positive

* Zero hallucinated article numbers (verified by validation layer)
* All claims are source-traceable
* Retrieval gaps become visible and fixable
* User trust is well-founded
* Cheaper to test (deterministic validation is free; LLM-based evaluation of correctness is expensive)

### Negative

* Less fluent outputs (no "by the way" commentary drawn from training knowledge)
* "No violation identified" more common than in permissive systems
* Requires stronger retrieval to compensate
* Users must understand that the system only knows what is retrieved

### Mitigated Risks

* **Retrieval gaps cause missed violations**: addressed by continuous gold-set expansion and retrieval tuning
* **"No violation identified" frustrates users**: framed as a feature, not a bug; honest uncertainty beats confident wrongness
* **Less fluent output**: fluency was never the goal — accuracy was

---

## Alternatives Considered

### Permissive with Confidence Scores

Let the LLM cite ungrounded articles but label them "low confidence." Rejected because:

* Users consistently under-weight low-confidence labels
* Still allows hallucinated citations to appear in output
* Confidence scores from LLMs are not well-calibrated for legal accuracy

### Permissive with Hedging Language

Allow ungrounded citations but phrase them with "may also apply" hedges. Rejected because:

* Hedges do not prevent hallucinated article numbers from appearing
* Cannot be verified after the fact
* Does not solve the fundamental trust problem

### Post-Hoc Fact-Check

Let the LLM generate freely, then verify citations against an external fact-checker. Rejected because:

* Doubles LLM cost
* Fact-checker itself could make errors
* Strict grounding is architecturally simpler and equivalently effective

---

## Operational Learnings (Forward-Looking)

### Metrics to Watch

* Hallucination-retry rate: should be low
* "No violation identified" rate: should correlate with retrieval gaps
* Gold-set F1 over time: improvements come from retrieval, not from relaxing grounding

### When to Revisit

This decision should be revisited if:

* Users consistently report that correct answers are being missed
* Retrieval recall@15 stalls below 0.85 despite tuning
* A superior alternative (e.g., confidence-calibrated generation) emerges

---

## Follow-Up Actions

* Reason prompt explicitly forbids ungrounded citations
* `pipeline.validate` enforces grounding deterministically
* Orchestrator retries once on hallucination detection
* Gold-set evaluation reports zero hallucinations as a hard requirement