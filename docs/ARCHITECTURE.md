# Architecture

## Overview

Four-stage pipeline: Extract → Classify → Retrieve → Reason.

## Components

### 1. Extract (Claude Haiku)
Pulls structured entities from the free-text scenario:
- Data subject (employee, customer, patient, child, etc.)
- Data type (contact, biometric, health, financial, etc.)
- Controller role
- Processing purpose
- Legal basis claimed (if any)
- Jurisdiction context (Germany-specific?)
- Special categories present?

### 2. Classify (Claude Haiku)
Maps the scenario to a fixed topic taxonomy (legal basis, consent,
data subject rights, security, transfers, employment, etc.) to
filter the retrieval scope.

### 3. Retrieve (ChromaDB + BM25)
Hybrid retrieval:
- Dense: sentence-transformers (bge-m3) similarity
- Sparse: BM25 keyword match
Returns top-15 chunks filtered by classified topics.

### 4. Reason (Claude Sonnet)
Given scenario + retrieved chunks, produces structured output.
Strict grounding: every cited article must exist in retrieved set.
Validation layer rejects and retries if hallucinated.

## Data flow

See pipeline/ for implementation.
