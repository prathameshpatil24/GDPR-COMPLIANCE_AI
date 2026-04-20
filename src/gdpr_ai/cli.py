"""CLI entry point: `gdpr-check "my scenario"`."""
import typer
from rich.console import Console

app = typer.Typer(help="GDPR AI — find violated articles from a scenario.")
console = Console()


@app.command()
def check(scenario: str = typer.Argument(..., help="Scenario to analyze.")):
    """Analyze a scenario and return violated GDPR articles."""
    console.print(f"[bold cyan]Scenario:[/bold cyan] {scenario}")
    console.print("[yellow]⚠️  Pipeline not yet implemented.[/yellow]")
    # TODO: wire up pipeline


@app.command()
def version():
    """Show version."""
    console.print("gdpr-ai v0.1.0")


if __name__ == "__main__":
    app()
