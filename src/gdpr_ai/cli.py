"""Typer CLI for GDPR AI."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table

from gdpr_ai import __version__
from gdpr_ai.compliance import run_compliance_assessment
from gdpr_ai.exceptions import GDPRAIError
from gdpr_ai.logger import get_query, get_stats, list_recent_queries, set_feedback
from gdpr_ai.models import AnalysisReport
from gdpr_ai.pipeline import run_pipeline

app = typer.Typer(help="GDPR AI — grounded GDPR article analysis from scenarios.")
console = Console()


def _render_report(report: AnalysisReport) -> None:
    sev = report.severity_level.upper()
    palette = {
        "LOW": "green",
        "MEDIUM": "yellow",
        "HIGH": "red",
        "CRITICAL": "red",
        "UNKNOWN": "white",
    }
    color = palette.get(sev, "white")
    console.print(f"[bold]Summary[/bold]\n{report.scenario_summary}\n")
    console.print(f"[bold]Severity[/bold] [{color}]{sev}[/{color}] — {report.severity_rationale}\n")

    if report.violations:
        table = Table("Article / instrument", "Confidence", "Source", "Explanation")
        for v in report.violations:
            table.add_row(
                v.article_reference,
                f"{v.confidence:.2f}",
                v.source_url,
                v.description[:240] + ("…" if len(v.description) > 240 else ""),
            )
        console.print(table)
    else:
        console.print("[yellow]No grounded violations identified from retrieved sources.[/yellow]")

    if report.recommendations:
        console.print("\n[bold]Recommendations[/bold]")
        for r in report.recommendations:
            console.print(f"- {r}")

    if report.unsupported_notes:
        console.print("\n[bold]Not grounded (retrieval gap)[/bold]")
        for n in report.unsupported_notes:
            console.print(f"- {n}")

    if report.citations:
        console.print("\n[bold]Citations[/bold]")
        for c in report.citations:
            console.print(f"- {c}")

    console.print(f"\n[dim]{report.disclaimer}[/dim]")


@app.command("analyze")
def analyze(
    scenario: str | None = typer.Argument(None, help="Scenario text to analyze."),
    file: Path | None = typer.Option(
        None,
        "--file",
        "-f",
        help="Read scenario from a text file.",
    ),
    as_json: bool = typer.Option(False, "--json", help="Emit raw JSON only."),
) -> None:
    """Run the full RAG pipeline on a scenario."""
    if file:
        text = file.read_text(encoding="utf-8").strip()
    elif scenario:
        text = scenario.strip()
    else:
        raise typer.BadParameter("Provide scenario text or --file.")
    if len(text) < 10:
        raise typer.BadParameter("Scenario is too short (min 10 characters).")
    if len(text) > 8000:
        raise typer.BadParameter("Scenario is too long for v1 (max 8000 characters).")

    try:
        report = asyncio.run(run_pipeline(text))
    except GDPRAIError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=2) from exc

    if as_json:
        console.print_json(data=report.model_dump())
    else:
        _render_report(report)


@app.command("assess")
def assess(
    description: str | None = typer.Argument(None, help="Free-text system description."),
    file: Path | None = typer.Option(
        None,
        "--file",
        "-f",
        help="JSON file matching the DataMap schema.",
    ),
    as_json: bool = typer.Option(False, "--json", help="Emit raw JSON only."),
) -> None:
    """Run compliance assessment (v2) on a system description or structured JSON."""
    if file:
        raw = json.loads(file.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise typer.BadParameter("JSON root must be an object.")
    elif description:
        text = description.strip()
        if len(text) < 20:
            raise typer.BadParameter("Description is too short (min 20 characters).")
        if len(text) > 32000:
            raise typer.BadParameter("Description is too long (max 32000 characters).")
        raw = text
    else:
        raise typer.BadParameter("Provide description text or --file.")

    try:
        assessment = asyncio.run(run_compliance_assessment(raw))
    except (GDPRAIError, ValidationError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=2) from exc

    if as_json:
        console.print_json(data=assessment.model_dump())
        return

    console.print(f"[bold]System[/bold] {assessment.system_name}\n")
    console.print(f"[bold]Overall risk[/bold] {assessment.overall_risk_level}\n")
    console.print(f"{assessment.summary}\n")
    if assessment.findings:
        table = Table("Area", "Status", "Articles", "Detail")
        for f in assessment.findings:
            arts = ", ".join(f.relevant_articles)
            table.add_row(
                f.area,
                f.status.value,
                arts[:120] + ("…" if len(arts) > 120 else ""),
                f.description[:200] + ("…" if len(f.description) > 200 else ""),
            )
        console.print(table)
    console.print(
        "\n[dim]This output is not legal advice. "
        "Review findings with a qualified professional.[/dim]"
    )


@app.command("serve")
def serve(
    host: str = typer.Option("127.0.0.1", "--host", help="Bind address."),
    port: int = typer.Option(8000, "--port", help="TCP port."),
) -> None:
    """Start the local HTTP API (FastAPI + uvicorn)."""
    import uvicorn

    uvicorn.run(
        "gdpr_ai.api.app:app",
        host=host,
        port=port,
        log_level="info",
    )


@app.command("stats")
def stats() -> None:
    """Show aggregate stats from the on-disk query log."""
    data = get_stats()
    n = int(data["total_queries"])
    if not n:
        console.print("No logged queries yet.")
        return
    console.print(f"Total queries: {n}")
    console.print(f"Avg latency: {data['avg_latency_ms'] / 1000.0:.1f} s")
    console.print(f"Avg cost: €{data['avg_cost_eur']:.4f}")
    console.print(f"Total cost: €{data['total_cost_eur']:.4f}")
    console.print(f"Total tokens: {int(data['total_tokens']):,}")
    console.print(f"Avg violations per query: {data['avg_violations_per_query']:.1f}")


@app.command("history")
def history(
    last: int = typer.Option(10, "--last", "-n", help="List the most recent queries."),
    query_id: str | None = typer.Option(None, "--id", help="Show full detail for one query id."),
) -> None:
    """Inspect logged queries."""
    if query_id:
        rec = get_query(query_id)
        if not rec:
            console.print(f"[red]No query found for id {query_id!r}.[/red]")
            raise typer.Exit(code=1)
        console.print_json(
            json.loads(
                json.dumps(
                    {
                        "id": rec.id,
                        "timestamp": rec.timestamp,
                        "scenario_text": rec.scenario_text,
                        "severity": rec.severity,
                        "violations_count": rec.violations_count,
                        "latency_total_ms": rec.latency_total_ms,
                        "estimated_cost_eur": rec.estimated_cost_eur,
                        "total_tokens": rec.total_tokens,
                        "feedback": rec.feedback,
                    }
                )
            )
        )
        return
    rows = list_recent_queries(limit=last)
    if not rows:
        console.print("No logged queries yet.")
        return
    table = Table("id", "timestamp", "scenario", "severity", "latency_ms", "cost_eur")
    for r in rows:
        scen = r.scenario_text.replace("\n", " ")[:56]
        ts = (r.timestamp or "")[:19]
        table.add_row(
            r.id,
            ts,
            scen + ("…" if len(r.scenario_text) > 56 else ""),
            r.severity or "",
            str(r.latency_total_ms),
            f"{r.estimated_cost_eur:.4f}",
        )
    console.print(table)
    console.print("[dim]Pass --id with a full id from the first column for JSON detail.[/dim]")


@app.command("feedback")
def feedback_cmd(
    query_id: str = typer.Option(..., "--id", help="Query log id."),
    rating: str = typer.Option(..., "--rating", help="up or down"),
) -> None:
    """Attach thumbs up/down feedback to a logged query."""
    if rating not in {"up", "down"}:
        raise typer.BadParameter("rating must be 'up' or 'down'")
    if not set_feedback(query_id, rating):
        console.print(f"[red]No query found for id {query_id!r}.[/red]")
        raise typer.Exit(code=1)
    console.print("Feedback saved.")


@app.command("version")
def version_cmd() -> None:
    """Print package version."""
    console.print(f"gdpr-ai v{__version__}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
