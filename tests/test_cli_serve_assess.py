"""CLI smoke tests for assess and serve commands."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from gdpr_ai.cli import app as cli_app
from gdpr_ai.compliance.schemas import (
    ComplianceAssessment,
    ComplianceStatus,
    DataCategory,
    DataMap,
    Finding,
    ProcessingPurpose,
    Sensitivity,
    Volume,
)


def _assessment() -> ComplianceAssessment:
    dm = DataMap(
        system_name="CLI",
        system_description="Test",
        data_categories=[
            DataCategory(
                name="email",
                sensitivity=Sensitivity.STANDARD,
                volume=Volume.LOW,
                subjects=["u"],
            )
        ],
        processing_purposes=[
            ProcessingPurpose(
                purpose="n",
                legal_basis_claimed="consent",
                data_categories=["email"],
            )
        ],
        data_flows=[],
        third_parties=[],
        storage=[],
    )
    return ComplianceAssessment(
        system_name="CLI",
        overall_risk_level="low",
        findings=[
            Finding(
                area="a",
                status=ComplianceStatus.COMPLIANT,
                relevant_articles=["Art. 6 GDPR"],
                description="d",
            )
        ],
        summary="s",
        data_map=dm,
    )


def test_assess_mocked_runs() -> None:
    runner = CliRunner()
    with patch("gdpr_ai.cli.run_compliance_assessment", new_callable=AsyncMock) as m:
        m.return_value = _assessment()
        result = runner.invoke(
            cli_app,
            ["assess", "We process emails for a newsletter with consent banners."],
        )
    assert result.exit_code == 0
    assert "CLI" in result.stdout


def test_serve_invokes_uvicorn() -> None:
    runner = CliRunner()
    with patch("uvicorn.run") as m:
        result = runner.invoke(cli_app, ["serve", "--port", "8765"])
    assert result.exit_code == 0
    m.assert_called_once()
    call_kw = m.call_args.kwargs
    assert call_kw["port"] == 8765
