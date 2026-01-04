"""Proxy command implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table

from ghoststorm.plugins.proxies.file_provider import FileProxyProvider

if TYPE_CHECKING:
    from pathlib import Path

console = Console()


async def run_proxy_command(
    action: str,
    file: Path | None,
    test_url: str,
    concurrent: int,
) -> None:
    """Run proxy management commands."""
    if action == "test":
        await test_proxies(file, test_url, concurrent)
    elif action == "list":
        await list_proxies(file)
    else:
        console.print(f"[red]Unknown action: {action}[/red]")
        console.print("Available actions: test, list")


async def test_proxies(
    file: Path | None,
    test_url: str,
    concurrent: int,
) -> None:
    """Test proxies from a file."""
    if not file or not file.exists():
        console.print("[red]Proxy file not found[/red]")
        return

    provider = FileProxyProvider(file_path=file)
    await provider.initialize()

    total = provider.total_proxies
    console.print(f"[bold]Testing {total} proxies against {test_url}[/bold]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        task = progress.add_task("Testing proxies...", total=total)

        results = await provider.health_check(
            test_url=test_url,
            concurrent=concurrent,
        )

        progress.update(task, completed=total)

    # Display results
    healthy = [r for r in results if r.is_healthy]
    failed = [r for r in results if not r.is_healthy]

    console.print()
    console.print(f"[green]Healthy: {len(healthy)}[/green]")
    console.print(f"[red]Failed: {len(failed)}[/red]")

    if healthy:
        table = Table(title="Healthy Proxies")
        table.add_column("Proxy", style="cyan")
        table.add_column("Latency (ms)", style="green")
        table.add_column("Success Rate", style="yellow")

        for result in sorted(healthy, key=lambda x: x.latency_ms or 9999)[:20]:
            table.add_row(
                result.proxy.id,
                f"{result.latency_ms:.0f}" if result.latency_ms else "N/A",
                f"{result.success_rate * 100:.0f}%",
            )

        console.print(table)

    if failed:
        console.print()
        console.print("[bold]Failed Proxies:[/bold]")
        for result in failed[:10]:
            console.print(f"  [red]{result.proxy.id}[/red]: {result.error_message}")


async def list_proxies(file: Path | None) -> None:
    """List proxies from a file."""
    if not file or not file.exists():
        console.print("[red]Proxy file not found[/red]")
        return

    provider = FileProxyProvider(file_path=file)
    await provider.initialize()

    table = Table(title=f"Proxies from {file}")
    table.add_column("#", style="dim")
    table.add_column("Host", style="cyan")
    table.add_column("Port", style="green")
    table.add_column("Type", style="yellow")
    table.add_column("Auth", style="magenta")
    table.add_column("Country", style="blue")

    count = 0
    async for proxy in provider.get_all():
        count += 1
        table.add_row(
            str(count),
            proxy.host,
            str(proxy.port),
            proxy.proxy_type.value,
            "Yes" if proxy.has_auth else "No",
            proxy.country or "-",
        )

        if count >= 50:
            break

    console.print(table)

    if provider.total_proxies > 50:
        console.print(f"[dim]... and {provider.total_proxies - 50} more[/dim]")
