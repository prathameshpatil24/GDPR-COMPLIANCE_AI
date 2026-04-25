"""Domain-specific exceptions for GDPR AI."""


class GDPRAIError(Exception):
    """Base error."""


class ConfigurationError(GDPRAIError):
    """Missing or invalid configuration."""


class KnowledgeBaseError(GDPRAIError):
    """ChromaDB or BM25 index unavailable."""


class NoChunksRetrieved(KnowledgeBaseError):
    """Retrieval returned zero chunks."""


class LLMError(GDPRAIError):
    """Anthropic API failure."""


class PipelineError(GDPRAIError):
    """Pipeline stage failure."""


class ExtractionFailed(PipelineError):
    """Entity extraction could not produce valid JSON."""


class ClassificationFailed(PipelineError):
    """Topic classification failed."""


class ReasoningFailed(PipelineError):
    """Reasoning stage failed."""


class HallucinationDetected(PipelineError):
    """Validator rejected draft report."""
