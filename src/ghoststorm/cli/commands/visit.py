"""Visit command implementation."""

from __future__ import annotations

import asyncio
from pathlib import Path

from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from ghoststorm.core.engine.orchestrator import Orchestrator
from ghoststorm.core.models.config import Config, ProxyProviderConfig
from ghoststorm.core.models.task import Task, TaskConfig, TaskType

console = Console()


async def run_visit(
    urls_file: Path,
    workers: int,
    headless: bool,
    proxy_file: Path | None,
    screenshot: bool,
    output: Path,
    config_file: Path | None,
    engine: str,
    dwell_time: str,
) -> None:
    """Run the visit command."""
    # Load config
    config = Config()
    if config_file and config_file.exists():
        config = Config.from_yaml(config_file)

    # Override with CLI options
    config.concurrency.max_workers = workers
    config.engine.headless = headless
    config.engine.default = engine
    config.output.screenshots.enabled = screenshot
    config.output.screenshots.directory = output / "screenshots"
    config.output.data.directory = output / "data"

    # Parse dwell time
    try:
        parts = dwell_time.split("-")
        min_dwell = float(parts[0])
        max_dwell = float(parts[1]) if len(parts) > 1 else min_dwell
        config.behavior.dwell_time_s = (min_dwell, max_dwell)
    except Exception:
        pass

    # Add proxy provider if specified
    if proxy_file and proxy_file.exists():
        config.proxy.providers = [
            ProxyProviderConfig(
                type="file",
                path=str(proxy_file),
            )
        ]

    # Load URLs
    if not urls_file.exists():
        console.print(f"[red]URL file not found: {urls_file}[/red]")
        return

    urls = []
    with urls_file.open() as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)

    if not urls:
        console.print("[red]No URLs found in file[/red]")
        return

    console.print(f"[bold blue]GhostStorm[/bold blue] - Visiting {len(urls)} URLs")
    console.print(f"Workers: {workers}, Engine: {engine}, Headless: {headless}")

    # Create output directory
    output.mkdir(parents=True, exist_ok=True)

    # Create orchestrator
    orchestrator = Orchestrator(config)

    try:
        await orchestrator.start()

        # Create tasks
        tasks = []
        for url in urls:
            task = Task(
                url=url,
                task_type=TaskType.VISIT,
                config=TaskConfig(
                    take_screenshot=screenshot,
                    dwell_time=config.behavior.dwell_time_s,
                    human_simulation=config.behavior.human_simulation,
                ),
            )
            tasks.append(task)

        # Submit batch
        batch_id = await orchestrator.submit_batch(tasks)

        # Track progress
        completed = 0
        failed = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task_progress = progress.add_task(
                f"Visiting URLs (batch: {batch_id})",
                total=len(tasks),
            )

            while completed + failed < len(tasks):
                await asyncio.sleep(0.5)

                # Get current stats
                stats = orchestrator.get_stats()
                completed = stats["worker_pool"]["total_tasks_succeeded"]
                failed = stats["worker_pool"]["total_tasks_failed"]

                progress.update(task_progress, completed=completed + failed)

        # Print summary
        console.print()
        console.print("[bold]Summary:[/bold]")
        console.print(f"  Total: {len(tasks)}")
        console.print(f"  [green]Completed: {completed}[/green]")
        console.print(f"  [red]Failed: {failed}[/red]")

        if screenshot:
            console.print(f"  Screenshots: {output}/screenshots/")

    finally:
        await orchestrator.stop()
