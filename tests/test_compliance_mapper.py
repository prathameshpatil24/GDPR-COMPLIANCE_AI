"""Tests for compliance article mapper topic inference and retrieval wiring."""

from __future__ import annotations

from gdpr_ai.compliance.mapper import (
    _marketing_email_context,
    _topics_from_data_map,
)
from gdpr_ai.compliance.schemas import (
    DataCategory,
    DataFlow,
    DataMap,
    ProcessingPurpose,
    Sensitivity,
    StorageInfo,
    ThirdParty,
    ThirdPartyRole,
    Volume,
)

_NEWSLETTER_DM = DataMap(
    system_name="Test",
    system_description="B2B newsletter; Mailchimp sends campaigns.",
    data_categories=[
        DataCategory(
            name="email addresses",
            sensitivity=Sensitivity.STANDARD,
            volume=Volume.MEDIUM,
            subjects=["customers"],
        )
    ],
    processing_purposes=[
        ProcessingPurpose(
            purpose="marketing emails",
            legal_basis_claimed=None,
            data_categories=["email addresses"],
        )
    ],
    data_flows=[
        DataFlow(
            source="API",
            destination="Mailchimp",
            data_categories=["email addresses"],
            crosses_border=True,
            destination_country="US",
        )
    ],
    third_parties=[
        ThirdParty(
            name="Mailchimp",
            role=ThirdPartyRole.PROCESSOR,
            purpose="email delivery",
            dpa_in_place=False,
            country="US",
        )
    ],
    storage=[
        StorageInfo(location="eu-central-1", country="DE", retention_period=None),
    ],
)


def test_topics_from_newsletter_scenario_includes_consent_and_information() -> None:
    """Marketing/newsletter intake should tag consent + transparency for dense retrieval hints."""
    dm = _NEWSLETTER_DM
    ct = _topics_from_data_map(dm)
    assert "consent" in ct.topics
    assert "information" in ct.topics
    assert "transfers" in ct.topics
    assert "controller-processor" in ct.topics
    assert "security-and-breaches" in ct.topics
    assert "security-of-processing" in ct.topics


def test_marketing_email_context_detects_newsletter_product() -> None:
    assert _marketing_email_context(_NEWSLETTER_DM) is True
