"""Map a ``DataMap`` to retrieved legal chunks (GDPR corpus + v2 collections)."""

from __future__ import annotations

import logging

from gdpr_ai.compliance.schemas import DataMap, ThirdPartyRole
from gdpr_ai.config import settings
from gdpr_ai.models import ClassifiedTopics, ExtractedEntities, RetrievedChunk
from gdpr_ai.retriever import (
    retrieve,
    retrieve_gdpr_chunks_by_article_numbers,
    retrieve_multi_collection,
)

logger = logging.getLogger(__name__)

_MARKETING_EMAIL_SIGNALS: frozenset[str] = frozenset(
    (
        "marketing",
        "newsletter",
        "email",
        "campaign",
        "subscribe",
        "mailchimp",
        "signup",
        "mailing",
        "promotional",
    )
)

_INFRA_STORAGE_SIGNALS: frozenset[str] = frozenset(
    (
        "aws",
        "postgres",
        "postgresql",
        "mysql",
        "azure",
        "gcp",
        "cloud",
        "database",
        "hosted",
        "bucket",
        "s3",
        "kubernetes",
    )
)

_US_COUNTRY_TOKENS: frozenset[str] = frozenset(("us", "usa"))


def _dedupe_chunks(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    """Drop duplicate chunk ids while preserving order."""
    seen: set[str] = set()
    out: list[RetrievedChunk] = []
    for c in chunks:
        if c.chunk_id in seen:
            continue
        seen.add(c.chunk_id)
        out.append(c)
    return out


def _blob_for_topic_inference(dm: DataMap) -> str:
    """Concatenate free-text fields used to infer retrieval topic tags."""
    parts = [dm.system_description, *[p.purpose for p in dm.processing_purposes]]
    parts.extend(p.legal_basis_claimed or "" for p in dm.processing_purposes)
    for s in dm.storage:
        parts.append(s.location)
        parts.append(s.country or "")
        parts.append(s.retention_period or "")
    for tp in dm.third_parties:
        parts.append(tp.name)
        parts.append(tp.purpose)
        parts.append(tp.country or "")
    return " ".join(parts).lower()


def _third_country_transfer_signals(dm: DataMap) -> bool:
    """True when data crosses borders or a vendor is in a third country (e.g. US)."""
    if any(f.crosses_border for f in dm.data_flows):
        return True
    for f in dm.data_flows:
        dc = (f.destination_country or "").strip().lower().replace(".", "")
        if dc and (dc in _US_COUNTRY_TOKENS or dc.startswith("united states")):
            return True
    for tp in dm.third_parties:
        c = (tp.country or "").strip().lower().replace(".", "")
        if not c:
            continue
        if c in _US_COUNTRY_TOKENS or c.startswith("united states"):
            return True
    return False


def _security_processing_signals(dm: DataMap) -> bool:
    """True when storage exists or the narrative mentions hosting or database stack."""
    if dm.storage:
        return True
    blob = _blob_for_topic_inference(dm)
    return any(s in blob for s in _INFRA_STORAGE_SIGNALS)


def _topics_from_data_map(dm: DataMap) -> ClassifiedTopics:
    """Derive classifier-like topic tags so retrieval gets consent/transparency dense hints."""
    tags: set[str] = {"gdpr"}
    blob = _blob_for_topic_inference(dm)
    if any(s in blob for s in _MARKETING_EMAIL_SIGNALS):
        tags.update({"consent", "legal-basis", "direct-marketing", "object"})
        tags.update({"information", "data-subject-rights"})
    elif any("consent" in (p.legal_basis_claimed or "").lower() for p in dm.processing_purposes):
        tags.update({"consent", "legal-basis"})
    if _third_country_transfer_signals(dm):
        tags.add("transfers")
    if _security_processing_signals(dm):
        tags.update({"security-and-breaches", "security-of-processing"})
    if any(tp.role == ThirdPartyRole.PROCESSOR for tp in dm.third_parties):
        tags.update({"controller-processor"})
    rationale_tags = sorted(tags - {"gdpr"})
    rationale = "compliance mapping: " + ", ".join(rationale_tags[:16])
    return ClassifiedTopics(topics=sorted(tags), rationale=rationale[:500])


def _marketing_email_context(dm: DataMap) -> bool:
    """True when intake text suggests newsletter/marketing/list signup style processing."""
    return any(s in _blob_for_topic_inference(dm) for s in _MARKETING_EMAIL_SIGNALS)


def _mandatory_gdpr_article_numbers(dm: DataMap) -> list[str]:
    """Article numbers to always load by metadata for reliable LLM grounding."""
    nums: list[str] = []
    if _marketing_email_context(dm):
        nums.extend(["5", "7", "13"])
    if _security_processing_signals(dm):
        nums.append("32")
    if _third_country_transfer_signals(dm):
        nums.extend(["44", "46"])
    seen: set[str] = set()
    out: list[str] = []
    for n in nums:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def map_articles(data_map: DataMap) -> dict[str, list[RetrievedChunk]]:
    """For each aspect of the system, retrieve GDPR + auxiliary guidance chunks."""
    article_map: dict[str, list[RetrievedChunk]] = {}
    snapshot = data_map.model_dump_json(ensure_ascii=False)
    topics_ctx = _topics_from_data_map(data_map)

    for cat in data_map.data_categories:
        q = (
            f"GDPR and EDPB requirements for processing {cat.name} "
            f"(sensitivity {cat.sensitivity.value}, volume {cat.volume.value}) "
            f"for data subjects: {', '.join(cat.subjects)}. Context: {snapshot[:1500]}"
        )
        article_map[f"category:{cat.name}"] = _retrieve_merged(q, topics_ctx)

    for purpose in data_map.processing_purposes:
        q = (
            f"Lawful basis, transparency, and compliance for processing purpose "
            f'"{purpose.purpose}" involving data categories {purpose.data_categories}. '
            f"Claimed basis: {purpose.legal_basis_claimed or 'unspecified'}."
        )
        article_map[f"purpose:{purpose.purpose}"] = _retrieve_merged(q, topics_ctx)

    for flow in data_map.data_flows:
        border = (
            f"cross-border to {flow.destination_country}" if flow.crosses_border else "domestic"
        )
        q = (
            f"Data transfer and security requirements for flow {flow.source} -> "
            f"{flow.destination} ({border}) for categories {flow.data_categories}."
        )
        article_map[f"flow:{flow.source}->{flow.destination}"] = _retrieve_merged(q, topics_ctx)

    for tp in data_map.third_parties:
        q = (
            f"Controller and processor obligations for third party {tp.name} "
            f"as {tp.role.value} for {tp.purpose}."
        )
        article_map[f"third_party:{tp.name}"] = _retrieve_merged(q, topics_ctx)

    for store in data_map.storage:
        q = (
            f"Security and storage limitation for location {store.location} "
            f"({store.country or 'unspecified'}), retention "
            f"{store.retention_period or 'unspecified'}."
        )
        article_map[f"storage:{store.location}"] = _retrieve_merged(q, topics_ctx)

    if data_map.has_automated_decision_making or data_map.uses_ai_ml:
        q = (
            "GDPR automated decision-making Article 22, DPIA Article 35, transparency; "
            "EU AI Act deployer obligations for high-risk systems and personal data."
        )
        article_map["automation_and_ai"] = _retrieve_merged(q, topics_ctx)

    if data_map.processes_children_data:
        q = "Children's data Article 8 GDPR consent and information society services."
        article_map["children"] = _retrieve_merged(q, topics_ctx)

    if _marketing_email_context(data_map):
        anchor = (
            "GDPR Article 6 lawful basis; Article 7 conditions for consent; "
            "Articles 12 and 13 transparency and information when collecting personal data "
            "for electronic direct marketing and newsletters."
        )
        article_map["anchors:lawfulness_and_information"] = _retrieve_merged(anchor, topics_ctx)

    if _security_processing_signals(data_map) or _third_country_transfer_signals(data_map):
        anchor_st = (
            "GDPR Article 32 security of processing; Chapter V Articles 44 "
            "(general principle for transfers) and 46 (appropriate safeguards "
            "including standard contractual clauses) where personal data is "
            "sent to vendors or subprocessors outside the European Economic Area."
        )
        article_map["anchors:security_and_transfers"] = _retrieve_merged(anchor_st, topics_ctx)

    mandatory_nums = _mandatory_gdpr_article_numbers(data_map)
    if mandatory_nums:
        mandatory_chunks = retrieve_gdpr_chunks_by_article_numbers(mandatory_nums)
        article_map["mandatory:gdpr_article_text"] = mandatory_chunks
        logger.debug(
            "Compliance mandatory GDPR articles numbers=%s chunks=%s",
            mandatory_nums,
            len(mandatory_chunks),
        )

    return article_map


def _retrieve_merged(query: str, topics: ClassifiedTopics) -> list[RetrievedChunk]:
    """Combine main GDPR index retrieval with v2 auxiliary collections."""
    entities = ExtractedEntities(jurisdiction="EU", summary=query[:2000])
    try:
        main_k = max(14, settings.top_k // 2 + 2)
        main = retrieve(query, topics, entities, top_k=main_k, mode="compliance")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Main retrieval failed: %s", exc)
        main = []
    try:
        aux = retrieve_multi_collection(
            query,
            top_k_per_collection=9,
            top_k=20,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Auxiliary retrieval failed: %s", exc)
        aux = []
    merged = _dedupe_chunks(main + aux)
    return merged[: max(settings.top_k + 5, 41)]
