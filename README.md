# GDPR AI

RAG-powered tool that analyzes a scenario and returns the violated GDPR articles
with scenario-specific explanations. German-market focused (GDPR + BDSG + TTDSG).

## Status

🚧 Active development — v0.1.0

## Architecture

```
Scenario → [Extract] → [Classify] → [Retrieve] → [Reason] → Report
            Haiku       Haiku       ChromaDB      Sonnet
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for details.

## Quick start

```bash
# Install dependencies
uv sync

# Set your API key
cp .env.example .env
# edit .env — add ANTHROPIC_API_KEY

# Build the knowledge base (one-time, ~1 hour)
uv run python scripts/scrape_gdpr.py
uv run python scripts/scrape_bdsg.py
uv run python scripts/scrape_ttdsg.py
uv run python scripts/scrape_gdprhub.py
uv run python scripts/chunk_and_embed.py
uv run python scripts/build_index.py

# Run a query
uv run gdpr-check "Scenario here..."
```

## Knowledge sources

See [docs/KNOWLEDGE_SOURCES.md](docs/KNOWLEDGE_SOURCES.md).

## Disclaimer

This tool provides informational guidance only. It is **not legal advice**.
Consult a qualified data protection lawyer for specific compliance decisions.
