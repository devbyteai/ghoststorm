"""Main CLI application."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from ghoststorm import __version__

# Create main app
app = typer.Typer(
    name="ghoststorm",
    help="Production-grade browser automation platform",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

console = Console()


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        console.print(f"[bold blue]GhostStorm[/bold blue] v{__version__}")
        raise typer.Exit()


@app.callback()
def main_callback(
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            "-v",
            help="Show version",
            callback=version_callback,
            is_eager=True,
        ),
    ] = None,
) -> None:
    """GhostStorm - Production-grade browser automation platform."""
    pass


@app.command()
def visit(
    urls_file: Annotated[
        Path,
        typer.Argument(help="File containing URLs to visit (one per line)"),
    ],
    workers: Annotated[
        int,
        typer.Option("--workers", "-w", help="Number of concurrent workers"),
    ] = 10,
    headless: Annotated[
        bool,
        typer.Option("--headless/--no-headless", help="Run in headless mode"),
    ] = True,
    proxy_file: Annotated[
        Path | None,
        typer.Option("--proxy-file", "-p", help="File containing proxies"),
    ] = None,
    screenshot: Annotated[
        bool,
        typer.Option("--screenshot", "-s", help="Take screenshots"),
    ] = False,
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Output directory"),
    ] = Path("./output"),
    config: Annotated[
        Path | None,
        typer.Option("--config", "-c", help="Config file path"),
    ] = None,
    engine: Annotated[
        str,
        typer.Option("--engine", "-e", help="Browser engine to use"),
    ] = "patchright",
    dwell_time: Annotated[
        str,
        typer.Option("--dwell-time", help="Time to stay on page (e.g., '5-15')"),
    ] = "5-15",
) -> None:
    """Visit URLs from a file with configurable options."""
    from ghoststorm.cli.commands.visit import run_visit

    asyncio.run(
        run_visit(
            urls_file=urls_file,
            workers=workers,
            headless=headless,
            proxy_file=proxy_file,
            screenshot=screenshot,
            output=output,
            config_file=config,
            engine=engine,
            dwell_time=dwell_time,
        )
    )


@app.command()
def scrape(
    urls_file: Annotated[
        Path,
        typer.Argument(help="File containing URLs to scrape"),
    ],
    extract: Annotated[
        list[str],
        typer.Option("--extract", "-x", help="Extraction rules (name=selector)"),
    ] = [],
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Output file"),
    ] = Path("./output/data.json"),
    format: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format (json, csv)"),
    ] = "json",
    workers: Annotated[
        int,
        typer.Option("--workers", "-w", help="Number of concurrent workers"),
    ] = 5,
    proxy_file: Annotated[
        Path | None,
        typer.Option("--proxy-file", "-p", help="File containing proxies"),
    ] = None,
) -> None:
    """Scrape data from URLs using extraction rules."""
    console.print("[bold]Scraping URLs...[/bold]")
    console.print(f"URLs: {urls_file}")
    console.print(f"Extractions: {extract}")
    console.print(f"Output: {output}")
    # TODO: Implement scraping


@app.command(name="load-test")
def load_test(
    url: Annotated[str, typer.Argument(help="URL to load test")],
    concurrent: Annotated[
        int,
        typer.Option("--concurrent", "-c", help="Concurrent users"),
    ] = 10,
    duration: Annotated[
        int,
        typer.Option("--duration", "-d", help="Test duration in seconds"),
    ] = 60,
    ramp_up: Annotated[
        int,
        typer.Option("--ramp-up", help="Ramp-up time in seconds"),
    ] = 10,
) -> None:
    """Run load testing against a URL."""
    console.print(f"[bold]Load testing {url}...[/bold]")
    console.print(f"Concurrent: {concurrent}, Duration: {duration}s")
    # TODO: Implement load testing


@app.command()
def proxy(
    action: Annotated[
        str,
        typer.Argument(help="Action: test, list, add"),
    ],
    file: Annotated[
        Path | None,
        typer.Option("--file", "-f", help="Proxy file"),
    ] = None,
    test_url: Annotated[
        str,
        typer.Option("--test-url", help="URL to test proxies against"),
    ] = "https://httpbin.org/ip",
    concurrent: Annotated[
        int,
        typer.Option("--concurrent", "-c", help="Concurrent tests"),
    ] = 10,
) -> None:
    """Manage and test proxies."""
    from ghoststorm.cli.commands.proxy import run_proxy_command

    asyncio.run(
        run_proxy_command(
            action=action,
            file=file,
            test_url=test_url,
            concurrent=concurrent,
        )
    )


@app.command()
def profile(
    action: Annotated[
        str,
        typer.Argument(help="Action: list, generate, import"),
    ],
    file: Annotated[
        Path | None,
        typer.Option("--file", "-f", help="Profile file"),
    ] = None,
    count: Annotated[
        int,
        typer.Option("--count", "-n", help="Number of profiles to generate"),
    ] = 10,
    browser: Annotated[
        str | None,
        typer.Option("--browser", "-b", help="Filter by browser"),
    ] = None,
    os: Annotated[
        str | None,
        typer.Option("--os", help="Filter by OS"),
    ] = None,
) -> None:
    """Manage fingerprint profiles."""
    if action == "list":
        console.print("[bold]Available profiles:[/bold]")
        # TODO: List profiles
    elif action == "generate":
        console.print(f"[bold]Generating {count} profiles...[/bold]")
        # TODO: Generate profiles
    elif action == "import":
        if file:
            console.print(f"[bold]Importing profiles from {file}...[/bold]")
        # TODO: Import profiles


@app.command()
def plugin(
    action: Annotated[
        str,
        typer.Argument(help="Action: list, info"),
    ],
    name: Annotated[
        str | None,
        typer.Option("--name", "-n", help="Plugin name"),
    ] = None,
) -> None:
    """Manage plugins."""
    from ghoststorm.core.registry.manager import PluginManager

    pm = PluginManager()
    pm.load_builtin_plugins()

    if action == "list":
        table = Table(title="Loaded Plugins")
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="green")

        for name in pm.list_plugins():
            table.add_row(name, "built-in")

        console.print(table)

        # Show registered providers
        console.print("\n[bold]Browser Engines:[/bold]")
        for engine in pm.list_browser_engines():
            console.print(f"  - {engine}")

        console.print("\n[bold]Proxy Providers:[/bold]")
        for provider in pm.list_proxy_providers():
            console.print(f"  - {provider}")

        console.print("\n[bold]Fingerprint Generators:[/bold]")
        for gen in pm.list_fingerprint_generators():
            console.print(f"  - {gen}")


@app.command()
def config(
    action: Annotated[
        str,
        typer.Argument(help="Action: show, validate, init"),
    ],
    file: Annotated[
        Path | None,
        typer.Option("--file", "-f", help="Config file"),
    ] = None,
) -> None:
    """Manage configuration."""
    from ghoststorm.core.models.config import Config

    if action == "show":
        cfg = Config()
        if file and file.exists():
            cfg = Config.from_yaml(file)

        console.print("[bold]Current Configuration:[/bold]")
        console.print_json(data=cfg.model_dump())

    elif action == "validate":
        if file:
            try:
                cfg = Config.from_yaml(file)
                console.print(f"[green]Config file {file} is valid![/green]")
            except Exception as e:
                console.print(f"[red]Config validation failed: {e}[/red]")
                raise typer.Exit(1)

    elif action == "init":
        output_path = file or Path("./config/default.yaml")
        cfg = Config()
        cfg.to_yaml(output_path)
        console.print(f"[green]Config initialized at {output_path}[/green]")


@app.command()
def serve(
    port: Annotated[
        int,
        typer.Option("--port", "-p", help="Port to listen on"),
    ] = 8080,
    host: Annotated[
        str,
        typer.Option("--host", "-h", help="Host to bind to"),
    ] = "0.0.0.0",
    reload: Annotated[
        bool,
        typer.Option("--reload", help="Enable auto-reload for development"),
    ] = False,
    workers_count: Annotated[
        int,
        typer.Option("--workers", "-w", help="Number of uvicorn workers"),
    ] = 1,
) -> None:
    """Start the web UI control panel.

    Access the control panel at http://localhost:PORT after starting.
    """
    import uvicorn

    from ghoststorm.api import create_app

    console.print("[bold green]Starting GhostStorm Web UI[/bold green]")
    console.print(f"  Host: {host}")
    console.print(f"  Port: {port}")
    console.print(f"  URL: [link=http://{host if host != '0.0.0.0' else 'localhost'}:{port}]http://localhost:{port}[/link]")
    console.print()

    # Create app
    app_instance = create_app()

    # Run with uvicorn
    uvicorn.run(
        "ghoststorm.api:create_app",
        host=host,
        port=port,
        reload=reload,
        workers=workers_count if not reload else 1,
        factory=True,
    )


def main() -> None:
    """Entry point."""
    app()


if __name__ == "__main__":
    main()
