"""Prometheus metrics export for GhostStorm.

Provides real-time metrics for:
- Task execution (success/failure rates, timing)
- Proxy health and performance
- Browser session statistics
- CAPTCHA solving rates
- System resource usage

Exposes metrics via HTTP endpoint for Prometheus scraping.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import structlog

logger = structlog.get_logger(__name__)

# Try to import prometheus_client
try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        CollectorRegistry,
        Counter,
        Gauge,
        Histogram,
        Info,
        generate_latest,
        start_http_server,
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("prometheus_client not installed. Metrics disabled.")


@dataclass
class MetricsConfig:
    """Metrics configuration."""

    # HTTP server settings
    port: int = 9090
    host: str = "0.0.0.0"

    # Metric prefix
    prefix: str = "ghoststorm"

    # Collection intervals
    collection_interval: float = 15.0  # seconds

    # Enable specific metrics
    enable_task_metrics: bool = True
    enable_proxy_metrics: bool = True
    enable_browser_metrics: bool = True
    enable_captcha_metrics: bool = True
    enable_system_metrics: bool = True


class MetricsCollector:
    """Prometheus metrics collector for GhostStorm.

    Usage:
        collector = MetricsCollector(MetricsConfig(port=9090))
        await collector.start()

        # Record metrics
        collector.task_started("visit", "example.com")
        collector.task_completed("visit", "example.com", success=True, duration=1.5)

        # Stop when done
        await collector.stop()
    """

    def __init__(self, config: MetricsConfig | None = None) -> None:
        """Initialize metrics collector.

        Args:
            config: Metrics configuration
        """
        self.config = config or MetricsConfig()
        self._registry = CollectorRegistry() if PROMETHEUS_AVAILABLE else None
        self._running = False
        self._collection_task: asyncio.Task | None = None

        if PROMETHEUS_AVAILABLE:
            self._init_metrics()

    def _init_metrics(self) -> None:
        """Initialize Prometheus metrics."""
        prefix = self.config.prefix

        # ========== Task Metrics ==========
        if self.config.enable_task_metrics:
            self.tasks_total = Counter(
                f"{prefix}_tasks_total",
                "Total number of tasks processed",
                ["task_type", "status"],
                registry=self._registry,
            )

            self.tasks_in_progress = Gauge(
                f"{prefix}_tasks_in_progress",
                "Number of tasks currently in progress",
                ["task_type"],
                registry=self._registry,
            )

            self.task_duration_seconds = Histogram(
                f"{prefix}_task_duration_seconds",
                "Task execution duration in seconds",
                ["task_type"],
                buckets=[0.5, 1, 2, 5, 10, 30, 60, 120, 300],
                registry=self._registry,
            )

            self.task_queue_size = Gauge(
                f"{prefix}_task_queue_size",
                "Number of tasks in queue",
                registry=self._registry,
            )

        # ========== Proxy Metrics ==========
        if self.config.enable_proxy_metrics:
            self.proxy_requests_total = Counter(
                f"{prefix}_proxy_requests_total",
                "Total proxy requests",
                ["proxy_id", "status"],
                registry=self._registry,
            )

            self.proxy_health = Gauge(
                f"{prefix}_proxy_health",
                "Proxy health score (0-100)",
                ["proxy_id"],
                registry=self._registry,
            )

            self.proxy_response_time_seconds = Histogram(
                f"{prefix}_proxy_response_time_seconds",
                "Proxy response time in seconds",
                ["proxy_id"],
                buckets=[0.1, 0.25, 0.5, 1, 2, 5, 10],
                registry=self._registry,
            )

            self.proxies_available = Gauge(
                f"{prefix}_proxies_available",
                "Number of available proxies by health",
                ["health"],
                registry=self._registry,
            )

        # ========== Browser Metrics ==========
        if self.config.enable_browser_metrics:
            self.browser_sessions_active = Gauge(
                f"{prefix}_browser_sessions_active",
                "Number of active browser sessions",
                ["engine"],
                registry=self._registry,
            )

            self.browser_pages_visited = Counter(
                f"{prefix}_browser_pages_visited_total",
                "Total pages visited",
                ["engine"],
                registry=self._registry,
            )

            self.browser_detection_events = Counter(
                f"{prefix}_browser_detection_events_total",
                "Bot detection events",
                ["detection_type"],
                registry=self._registry,
            )

        # ========== CAPTCHA Metrics ==========
        if self.config.enable_captcha_metrics:
            self.captcha_attempts_total = Counter(
                f"{prefix}_captcha_attempts_total",
                "Total CAPTCHA solving attempts",
                ["captcha_type", "solver", "success"],
                registry=self._registry,
            )

            self.captcha_solve_time_seconds = Histogram(
                f"{prefix}_captcha_solve_time_seconds",
                "CAPTCHA solve time in seconds",
                ["captcha_type", "solver"],
                buckets=[1, 2, 5, 10, 20, 30, 60],
                registry=self._registry,
            )

        # ========== System Metrics ==========
        if self.config.enable_system_metrics:
            self.system_info = Info(
                f"{prefix}_system",
                "System information",
                registry=self._registry,
            )

            self.memory_usage_bytes = Gauge(
                f"{prefix}_memory_usage_bytes",
                "Process memory usage in bytes",
                registry=self._registry,
            )

            self.cpu_usage_percent = Gauge(
                f"{prefix}_cpu_usage_percent",
                "Process CPU usage percentage",
                registry=self._registry,
            )

            self.workers_active = Gauge(
                f"{prefix}_workers_active",
                "Number of active worker threads/processes",
                registry=self._registry,
            )

    async def start(self) -> None:
        """Start metrics server and collection."""
        if not PROMETHEUS_AVAILABLE:
            logger.warning("Prometheus client not available, metrics disabled")
            return

        if self._running:
            return

        # Start HTTP server for Prometheus scraping
        start_http_server(
            self.config.port,
            addr=self.config.host,
            registry=self._registry,
        )

        self._running = True

        # Start background collection
        if self.config.enable_system_metrics:
            self._collection_task = asyncio.create_task(self._collect_system_metrics())

        logger.info(
            "Metrics server started",
            host=self.config.host,
            port=self.config.port,
        )

    async def stop(self) -> None:
        """Stop metrics collection."""
        self._running = False

        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass

        logger.info("Metrics collection stopped")

    async def _collect_system_metrics(self) -> None:
        """Background task to collect system metrics."""
        import os

        while self._running:
            try:
                # Collect memory usage
                try:
                    import psutil
                    process = psutil.Process(os.getpid())
                    self.memory_usage_bytes.set(process.memory_info().rss)
                    self.cpu_usage_percent.set(process.cpu_percent())
                except ImportError:
                    pass

                await asyncio.sleep(self.config.collection_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error collecting system metrics", error=str(e))
                await asyncio.sleep(self.config.collection_interval)

    # ========== Task Metric Methods ==========

    def task_started(self, task_type: str, domain: str | None = None) -> None:
        """Record task start."""
        if not PROMETHEUS_AVAILABLE or not self.config.enable_task_metrics:
            return
        self.tasks_in_progress.labels(task_type=task_type).inc()

    def task_completed(
        self,
        task_type: str,
        domain: str | None = None,
        success: bool = True,
        duration: float = 0.0,
    ) -> None:
        """Record task completion."""
        if not PROMETHEUS_AVAILABLE or not self.config.enable_task_metrics:
            return

        status = "success" if success else "failed"
        self.tasks_total.labels(task_type=task_type, status=status).inc()
        self.tasks_in_progress.labels(task_type=task_type).dec()
        self.task_duration_seconds.labels(task_type=task_type).observe(duration)

    def set_queue_size(self, size: int) -> None:
        """Update task queue size."""
        if not PROMETHEUS_AVAILABLE or not self.config.enable_task_metrics:
            return
        self.task_queue_size.set(size)

    # ========== Proxy Metric Methods ==========

    def proxy_request(
        self,
        proxy_id: str,
        success: bool = True,
        response_time: float = 0.0,
    ) -> None:
        """Record proxy request."""
        if not PROMETHEUS_AVAILABLE or not self.config.enable_proxy_metrics:
            return

        status = "success" if success else "failed"
        self.proxy_requests_total.labels(proxy_id=proxy_id, status=status).inc()

        if response_time > 0:
            self.proxy_response_time_seconds.labels(proxy_id=proxy_id).observe(
                response_time
            )

    def set_proxy_health(self, proxy_id: str, score: float) -> None:
        """Update proxy health score."""
        if not PROMETHEUS_AVAILABLE or not self.config.enable_proxy_metrics:
            return
        self.proxy_health.labels(proxy_id=proxy_id).set(score)

    def set_proxies_available(self, health: str, count: int) -> None:
        """Update available proxies count by health."""
        if not PROMETHEUS_AVAILABLE or not self.config.enable_proxy_metrics:
            return
        self.proxies_available.labels(health=health).set(count)

    # ========== Browser Metric Methods ==========

    def browser_session_started(self, engine: str) -> None:
        """Record browser session start."""
        if not PROMETHEUS_AVAILABLE or not self.config.enable_browser_metrics:
            return
        self.browser_sessions_active.labels(engine=engine).inc()

    def browser_session_ended(self, engine: str) -> None:
        """Record browser session end."""
        if not PROMETHEUS_AVAILABLE or not self.config.enable_browser_metrics:
            return
        self.browser_sessions_active.labels(engine=engine).dec()

    def page_visited(self, engine: str) -> None:
        """Record page visit."""
        if not PROMETHEUS_AVAILABLE or not self.config.enable_browser_metrics:
            return
        self.browser_pages_visited.labels(engine=engine).inc()

    def detection_event(self, detection_type: str) -> None:
        """Record bot detection event."""
        if not PROMETHEUS_AVAILABLE or not self.config.enable_browser_metrics:
            return
        self.browser_detection_events.labels(detection_type=detection_type).inc()

    # ========== CAPTCHA Metric Methods ==========

    def captcha_attempt(
        self,
        captcha_type: str,
        solver: str,
        success: bool,
        solve_time: float = 0.0,
    ) -> None:
        """Record CAPTCHA solving attempt."""
        if not PROMETHEUS_AVAILABLE or not self.config.enable_captcha_metrics:
            return

        self.captcha_attempts_total.labels(
            captcha_type=captcha_type,
            solver=solver,
            success=str(success).lower(),
        ).inc()

        if solve_time > 0:
            self.captcha_solve_time_seconds.labels(
                captcha_type=captcha_type,
                solver=solver,
            ).observe(solve_time)

    # ========== Worker Metric Methods ==========

    def set_workers_active(self, count: int) -> None:
        """Update active worker count."""
        if not PROMETHEUS_AVAILABLE or not self.config.enable_system_metrics:
            return
        self.workers_active.set(count)

    def get_metrics(self) -> bytes:
        """Get current metrics in Prometheus format."""
        if not PROMETHEUS_AVAILABLE:
            return b""
        return generate_latest(self._registry)


# Global metrics collector
_collector: MetricsCollector | None = None


def get_metrics_collector(config: MetricsConfig | None = None) -> MetricsCollector:
    """Get or create global metrics collector."""
    global _collector
    if _collector is None:
        _collector = MetricsCollector(config)
    return _collector


async def start_metrics_server(config: MetricsConfig | None = None) -> MetricsCollector:
    """Start metrics server with config."""
    collector = get_metrics_collector(config)
    await collector.start()
    return collector
