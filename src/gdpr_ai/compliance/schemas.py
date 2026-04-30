"""Pydantic models for compliance assessment (v2)."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from gdpr_ai.models import AnalysisConfidence, ConfidenceLevel


class Sensitivity(StrEnum):
    """Approximate data sensitivity tier."""

    STANDARD = "standard"
    SPECIAL_CATEGORY = "special_category"
    CRIMINAL = "criminal"


class Volume(StrEnum):
    """Rough volume band for a data category."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ThirdPartyRole(StrEnum):
    """Relationship under GDPR."""

    PROCESSOR = "processor"
    JOINT_CONTROLLER = "joint_controller"
    INDEPENDENT_CONTROLLER = "independent_controller"


class ComplianceStatus(StrEnum):
    """Posture for one assessment finding."""

    COMPLIANT = "compliant"
    AT_RISK = "at_risk"
    NON_COMPLIANT = "non_compliant"
    INSUFFICIENT_INFO = "insufficient_info"


class DataCategory(BaseModel):
    """One category of personal data processed."""

    name: str = Field(..., description="e.g. email addresses, IP addresses")
    sensitivity: Sensitivity = Sensitivity.STANDARD
    volume: Volume = Volume.MEDIUM
    subjects: list[str] = Field(
        ...,
        description="e.g. customers, employees",
    )


class ProcessingPurpose(BaseModel):
    """Purpose of processing linked to data categories by name."""

    purpose: str = Field(..., description="e.g. marketing emails, analytics")
    legal_basis_claimed: str | None = None
    data_categories: list[str] = Field(
        ...,
        description="Names referencing DataCategory.name entries",
    )


class DataFlow(BaseModel):
    """Movement of data between systems or organisations."""

    source: str = Field(..., description="e.g. web form, API, third-party")
    destination: str = Field(..., description="e.g. PostgreSQL, analytics provider")
    data_categories: list[str]
    crosses_border: bool = False
    destination_country: str | None = None

    @field_validator("crosses_border", mode="before")
    @classmethod
    def _coerce_crosses_border(cls, v: Any) -> bool:
        """LLM extracts often emit null; treat as False."""
        if v is None:
            return False
        if isinstance(v, bool):
            return v
        return bool(v)


class ThirdParty(BaseModel):
    """Processor or controller relationship."""

    name: str
    role: ThirdPartyRole
    purpose: str
    dpa_in_place: bool | None = None
    country: str | None = None


class StorageInfo(BaseModel):
    """Where data is stored and how long."""

    location: str = Field(..., description="e.g. AWS eu-central-1")
    country: str | None = None
    encryption_at_rest: bool | None = None
    encryption_in_transit: bool | None = None
    retention_period: str | None = None


class DataMap(BaseModel):
    """Normalised description of a system under assessment."""

    system_name: str
    system_description: str
    data_categories: list[DataCategory]
    processing_purposes: list[ProcessingPurpose]
    data_flows: list[DataFlow]
    third_parties: list[ThirdParty]
    storage: list[StorageInfo]
    has_automated_decision_making: bool = False
    processes_children_data: bool = False
    uses_ai_ml: bool = False


class Finding(BaseModel):
    """Single compliance finding."""

    area: str = Field(..., description="e.g. consent, data_breach_notification")
    status: ComplianceStatus
    relevant_articles: list[str]
    description: str
    remediation: str | None = None
    technical_guidance: str | None = None
    confidence_level: ConfidenceLevel | None = None
    source_articles: list[str] = Field(default_factory=list)
    confidence_notes: str = ""


class ComplianceAssessment(BaseModel):
    """Full assessment output for document generation."""

    system_name: str
    overall_risk_level: str
    findings: list[Finding]
    summary: str
    data_map: DataMap
    analysis_confidence: AnalysisConfidence | None = None
