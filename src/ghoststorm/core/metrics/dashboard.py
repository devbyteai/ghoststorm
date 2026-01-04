"""Real-time dashboard for GhostStorm monitoring.

Provides a simple web-based dashboard showing:
- Task statistics and progress
- Proxy health overview
- Browser session status
- CAPTCHA solving rates
- System resource usage

Uses Server-Sent Events (SSE) for real-time updates.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class DashboardStats:
    """Current dashboard statistics."""

    # Timestamp
    timestamp: str

    # Task stats
    tasks_pending: int = 0
    tasks_running: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    tasks_per_minute: float = 0.0

    # Proxy stats
    proxies_total: int = 0
    proxies_healthy: int = 0
    proxies_degraded: int = 0
    proxies_unhealthy: int = 0

    # Browser stats
    sessions_active: int = 0
    pages_visited: int = 0
    detection_events: int = 0

    # CAPTCHA stats
    captchas_solved: int = 0
    captchas_failed: int = 0
    captcha_success_rate: float = 0.0

    # System stats
    memory_mb: float = 0.0
    cpu_percent: float = 0.0
    workers_active: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class DashboardConfig:
    """Dashboard configuration."""

    # HTTP server
    host: str = "0.0.0.0"
    port: int = 8080

    # Update interval
    update_interval: float = 2.0  # seconds

    # History retention
    history_minutes: int = 60


class Dashboard:
    """Real-time monitoring dashboard.

    Usage:
        dashboard = Dashboard(DashboardConfig(port=8080))
        await dashboard.start()

        # Update stats
        dashboard.update_task_stats(pending=10, running=5, completed=100)

        # Stop
        await dashboard.stop()
    """

    def __init__(self, config: DashboardConfig | None = None) -> None:
        """Initialize dashboard.

        Args:
            config: Dashboard configuration
        """
        self.config = config or DashboardConfig()
        self._stats = DashboardStats(timestamp=datetime.now(UTC).isoformat())
        self._running = False
        self._update_task: asyncio.Task | None = None
        self._history: list[DashboardStats] = []

        # Counters for rate calculation
        self._tasks_completed_last = 0
        self._last_rate_calc = time.time()

    @property
    def stats(self) -> DashboardStats:
        """Get current stats."""
        return self._stats

    def update_task_stats(
        self,
        pending: int | None = None,
        running: int | None = None,
        completed: int | None = None,
        failed: int | None = None,
    ) -> None:
        """Update task statistics."""
        if pending is not None:
            self._stats.tasks_pending = pending
        if running is not None:
            self._stats.tasks_running = running
        if completed is not None:
            # Calculate rate
            now = time.time()
            elapsed = now - self._last_rate_calc
            if elapsed >= 60:
                completed_diff = completed - self._tasks_completed_last
                self._stats.tasks_per_minute = completed_diff / (elapsed / 60)
                self._tasks_completed_last = completed
                self._last_rate_calc = now

            self._stats.tasks_completed = completed
        if failed is not None:
            self._stats.tasks_failed = failed

    def update_proxy_stats(
        self,
        total: int | None = None,
        healthy: int | None = None,
        degraded: int | None = None,
        unhealthy: int | None = None,
    ) -> None:
        """Update proxy statistics."""
        if total is not None:
            self._stats.proxies_total = total
        if healthy is not None:
            self._stats.proxies_healthy = healthy
        if degraded is not None:
            self._stats.proxies_degraded = degraded
        if unhealthy is not None:
            self._stats.proxies_unhealthy = unhealthy

    def update_browser_stats(
        self,
        sessions_active: int | None = None,
        pages_visited: int | None = None,
        detection_events: int | None = None,
    ) -> None:
        """Update browser statistics."""
        if sessions_active is not None:
            self._stats.sessions_active = sessions_active
        if pages_visited is not None:
            self._stats.pages_visited = pages_visited
        if detection_events is not None:
            self._stats.detection_events = detection_events

    def update_captcha_stats(
        self,
        solved: int | None = None,
        failed: int | None = None,
    ) -> None:
        """Update CAPTCHA statistics."""
        if solved is not None:
            self._stats.captchas_solved = solved
        if failed is not None:
            self._stats.captchas_failed = failed

        total = self._stats.captchas_solved + self._stats.captchas_failed
        if total > 0:
            self._stats.captcha_success_rate = self._stats.captchas_solved / total

    def update_system_stats(
        self,
        memory_mb: float | None = None,
        cpu_percent: float | None = None,
        workers_active: int | None = None,
    ) -> None:
        """Update system statistics."""
        if memory_mb is not None:
            self._stats.memory_mb = memory_mb
        if cpu_percent is not None:
            self._stats.cpu_percent = cpu_percent
        if workers_active is not None:
            self._stats.workers_active = workers_active

    async def start(self) -> None:
        """Start dashboard server."""
        if self._running:
            return

        self._running = True

        # Start periodic stat collection
        self._update_task = asyncio.create_task(self._collect_stats())

        logger.info(
            "Dashboard started",
            host=self.config.host,
            port=self.config.port,
        )

    async def stop(self) -> None:
        """Stop dashboard server."""
        self._running = False

        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass

        logger.info("Dashboard stopped")

    async def _collect_stats(self) -> None:
        """Periodic stats collection."""
        while self._running:
            try:
                # Update timestamp
                self._stats.timestamp = datetime.now(UTC).isoformat()

                # Collect system stats
                try:
                    import os

                    import psutil

                    process = psutil.Process(os.getpid())
                    self._stats.memory_mb = process.memory_info().rss / (1024 * 1024)
                    self._stats.cpu_percent = process.cpu_percent()
                except ImportError:
                    pass

                # Store in history
                self._history.append(DashboardStats(**asdict(self._stats)))

                # Trim history
                max_entries = int(self.config.history_minutes * 60 / self.config.update_interval)
                if len(self._history) > max_entries:
                    self._history = self._history[-max_entries:]

                await asyncio.sleep(self.config.update_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error collecting stats", error=str(e))
                await asyncio.sleep(self.config.update_interval)

    def get_stats_json(self) -> str:
        """Get current stats as JSON."""
        return json.dumps(self._stats.to_dict())

    def get_history_json(self, minutes: int = 10) -> str:
        """Get stats history as JSON."""
        entries = int(minutes * 60 / self.config.update_interval)
        history = self._history[-entries:] if entries < len(self._history) else self._history
        return json.dumps([s.to_dict() for s in history])

    async def sse_stream(self) -> AsyncIterator[str]:
        """Server-Sent Events stream for real-time updates."""
        while self._running:
            yield f"data: {self.get_stats_json()}\n\n"
            await asyncio.sleep(self.config.update_interval)

    def get_html_dashboard(self) -> str:
        """Get HTML dashboard page."""
        return """<!DOCTYPE html>
<html>
<head>
    <title>GhostStorm Dashboard</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e;
            color: #eee;
            padding: 20px;
        }
        .header { text-align: center; margin-bottom: 30px; }
        .header h1 { color: #00d4ff; font-size: 2em; }
        .header .subtitle { color: #888; margin-top: 5px; }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            max-width: 1400px;
            margin: 0 auto;
        }
        .card {
            background: #16213e;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }
        .card-title {
            font-size: 0.9em;
            color: #888;
            text-transform: uppercase;
            margin-bottom: 15px;
            letter-spacing: 1px;
        }
        .stat-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid #2a3f5f;
        }
        .stat-row:last-child { border-bottom: none; }
        .stat-label { color: #aaa; }
        .stat-value { font-size: 1.5em; font-weight: bold; }
        .stat-value.success { color: #00ff88; }
        .stat-value.warning { color: #ffaa00; }
        .stat-value.error { color: #ff4466; }
        .stat-value.info { color: #00d4ff; }
        .progress-bar {
            width: 100%;
            height: 8px;
            background: #2a3f5f;
            border-radius: 4px;
            margin-top: 10px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #00d4ff, #00ff88);
            transition: width 0.3s ease;
        }
        .timestamp {
            text-align: center;
            color: #666;
            margin-top: 20px;
            font-size: 0.85em;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>GhostStorm Dashboard</h1>
        <div class="subtitle">Real-time Monitoring</div>
    </div>

    <div class="grid">
        <div class="card">
            <div class="card-title">Task Statistics</div>
            <div class="stat-row">
                <span class="stat-label">Pending</span>
                <span class="stat-value info" id="tasks-pending">0</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Running</span>
                <span class="stat-value warning" id="tasks-running">0</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Completed</span>
                <span class="stat-value success" id="tasks-completed">0</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Failed</span>
                <span class="stat-value error" id="tasks-failed">0</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Rate</span>
                <span class="stat-value" id="tasks-rate">0/min</span>
            </div>
        </div>

        <div class="card">
            <div class="card-title">Proxy Health</div>
            <div class="stat-row">
                <span class="stat-label">Total</span>
                <span class="stat-value" id="proxies-total">0</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Healthy</span>
                <span class="stat-value success" id="proxies-healthy">0</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Degraded</span>
                <span class="stat-value warning" id="proxies-degraded">0</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Unhealthy</span>
                <span class="stat-value error" id="proxies-unhealthy">0</span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill" id="proxy-health-bar" style="width: 0%"></div>
            </div>
        </div>

        <div class="card">
            <div class="card-title">Browser Sessions</div>
            <div class="stat-row">
                <span class="stat-label">Active</span>
                <span class="stat-value info" id="sessions-active">0</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Pages Visited</span>
                <span class="stat-value" id="pages-visited">0</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Detections</span>
                <span class="stat-value error" id="detection-events">0</span>
            </div>
        </div>

        <div class="card">
            <div class="card-title">CAPTCHA Solving</div>
            <div class="stat-row">
                <span class="stat-label">Solved</span>
                <span class="stat-value success" id="captchas-solved">0</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Failed</span>
                <span class="stat-value error" id="captchas-failed">0</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Success Rate</span>
                <span class="stat-value" id="captcha-rate">0%</span>
            </div>
        </div>

        <div class="card">
            <div class="card-title">System Resources</div>
            <div class="stat-row">
                <span class="stat-label">Memory</span>
                <span class="stat-value" id="memory-usage">0 MB</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">CPU</span>
                <span class="stat-value" id="cpu-usage">0%</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Workers</span>
                <span class="stat-value info" id="workers-active">0</span>
            </div>
        </div>
    </div>

    <div class="timestamp" id="timestamp">Last updated: --</div>

    <script>
        const eventSource = new EventSource('/events');

        eventSource.onmessage = function(event) {
            const data = JSON.parse(event.data);
            updateDashboard(data);
        };

        function updateDashboard(data) {
            document.getElementById('tasks-pending').textContent = data.tasks_pending;
            document.getElementById('tasks-running').textContent = data.tasks_running;
            document.getElementById('tasks-completed').textContent = data.tasks_completed;
            document.getElementById('tasks-failed').textContent = data.tasks_failed;
            document.getElementById('tasks-rate').textContent = data.tasks_per_minute.toFixed(1) + '/min';

            document.getElementById('proxies-total').textContent = data.proxies_total;
            document.getElementById('proxies-healthy').textContent = data.proxies_healthy;
            document.getElementById('proxies-degraded').textContent = data.proxies_degraded;
            document.getElementById('proxies-unhealthy').textContent = data.proxies_unhealthy;

            const healthPercent = data.proxies_total > 0
                ? (data.proxies_healthy / data.proxies_total * 100)
                : 0;
            document.getElementById('proxy-health-bar').style.width = healthPercent + '%';

            document.getElementById('sessions-active').textContent = data.sessions_active;
            document.getElementById('pages-visited').textContent = data.pages_visited;
            document.getElementById('detection-events').textContent = data.detection_events;

            document.getElementById('captchas-solved').textContent = data.captchas_solved;
            document.getElementById('captchas-failed').textContent = data.captchas_failed;
            document.getElementById('captcha-rate').textContent =
                (data.captcha_success_rate * 100).toFixed(1) + '%';

            document.getElementById('memory-usage').textContent = data.memory_mb.toFixed(1) + ' MB';
            document.getElementById('cpu-usage').textContent = data.cpu_percent.toFixed(1) + '%';
            document.getElementById('workers-active').textContent = data.workers_active;

            document.getElementById('timestamp').textContent = 'Last updated: ' + data.timestamp;
        }
    </script>
</body>
</html>"""


# Global dashboard instance
_dashboard: Dashboard | None = None


def get_dashboard(config: DashboardConfig | None = None) -> Dashboard:
    """Get or create global dashboard."""
    global _dashboard
    if _dashboard is None:
        _dashboard = Dashboard(config)
    return _dashboard
