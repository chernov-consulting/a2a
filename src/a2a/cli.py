"""CLI entry-point: `a2a sim`, `a2a report`, `a2a site`."""

from __future__ import annotations

from typing import TYPE_CHECKING

import typer

if TYPE_CHECKING:
    from pathlib import Path

app = typer.Typer(name="a2a", add_completion=False, help="Agent-to-agent commerce simulator.")


@app.command()
def sim(
    experiment: Path = typer.Option(..., help="Path to experiment config.yaml"),
    dry_run: bool = typer.Option(False, help="Validate config without running LLM calls"),
) -> None:
    """Run a simulation experiment."""
    from a2a.runner.orchestrator import Orchestrator

    orchestrator = Orchestrator.from_config_file(experiment)
    if dry_run:
        typer.echo(f"Config loaded: {orchestrator.config.slug}")
        raise typer.Exit(0)
    orchestrator.run()


@app.command()
def report(
    experiment: Path = typer.Option(..., help="Path to experiment directory"),
    open_browser: bool = typer.Option(False, help="Open the report in the default browser"),
) -> None:
    """Generate an HTML report from experiment results."""
    from a2a.reporting.generator import ReportGenerator

    gen = ReportGenerator(experiment)
    report_path = gen.build()
    typer.echo(f"Report: {report_path}")
    if open_browser:
        import webbrowser

        webbrowser.open(str(report_path))


@app.command()
def bench(
    protocol: str = typer.Argument(help="Protocol to benchmark: ap2 | mcp | a2a | x402 | ucp"),
    output: Path | None = typer.Option(None, help="Write ledger record to this JSONL file"),
) -> None:
    """Run a single-transaction benchmark for a payment protocol."""
    import importlib

    module = importlib.import_module(f"a2a.protocols.{protocol.replace('-', '_')}.bench")
    module.run(output_path=output)


if __name__ == "__main__":
    app()
