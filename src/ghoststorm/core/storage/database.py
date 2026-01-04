"""Database connection and session management.

Provides async database access with:
- SQLite (default) or PostgreSQL support
- Connection pooling
- Async session management
- Migration support via Alembic
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypeVar

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from ghoststorm.core.storage.models import (
    ApiKey,
    Base,
    EventLog,
    MetricSample,
    Proxy,
    ProxyHealthStatus,
    Task,
    TaskStatus,
)
from ghoststorm.core.storage.models import (
    Session as SessionModel,
)

logger = structlog.get_logger(__name__)

T = TypeVar("T")


@dataclass
class DatabaseConfig:
    """Database configuration."""

    # Connection
    url: str = "sqlite+aiosqlite:///ghoststorm.db"
    echo: bool = False  # Log SQL queries

    # Pool settings (PostgreSQL)
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: float = 30.0
    pool_recycle: int = 1800  # Recycle connections after 30 min

    # SQLite specific
    sqlite_path: Path | None = None


class Database:
    """Async database manager.

    Usage:
        db = Database(DatabaseConfig())
        await db.init()

        async with db.session() as session:
            task = Task(url="https://example.com")
            session.add(task)
            await session.commit()

        await db.close()
    """

    def __init__(self, config: DatabaseConfig | None = None) -> None:
        """Initialize database.

        Args:
            config: Database configuration
        """
        self.config = config or DatabaseConfig()
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None
        self._initialized = False

    async def init(self) -> None:
        """Initialize database connection and create tables."""
        if self._initialized:
            return

        # Build connection URL
        url = self.config.url
        if self.config.sqlite_path:
            url = f"sqlite+aiosqlite:///{self.config.sqlite_path}"

        # Create async engine
        engine_kwargs: dict[str, Any] = {
            "echo": self.config.echo,
        }

        if "sqlite" in url:
            # SQLite specific settings
            engine_kwargs["connect_args"] = {"check_same_thread": False}
            engine_kwargs["poolclass"] = StaticPool
        else:
            # PostgreSQL pool settings
            engine_kwargs["pool_size"] = self.config.pool_size
            engine_kwargs["max_overflow"] = self.config.max_overflow
            engine_kwargs["pool_timeout"] = self.config.pool_timeout
            engine_kwargs["pool_recycle"] = self.config.pool_recycle

        self._engine = create_async_engine(url, **engine_kwargs)

        # Create session factory
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        # Create tables
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        self._initialized = True
        logger.info("Database initialized", url=url.split("@")[-1])  # Hide credentials

    async def close(self) -> None:
        """Close database connection."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            self._initialized = False
            logger.info("Database connection closed")

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session context.

        Usage:
            async with db.session() as session:
                result = await session.execute(query)
        """
        if not self._session_factory:
            await self.init()

        session = self._session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    # ==================== Task Operations ====================

    async def create_task(
        self,
        url: str,
        task_type: str = "visit",
        batch_id: str | None = None,
        priority: int = 0,
        config: dict[str, Any] | None = None,
    ) -> Task:
        """Create a new task."""
        async with self.session() as session:
            task = Task(
                url=url,
                task_type=task_type,
                batch_id=batch_id,
                priority=priority,
                config=config,
            )
            session.add(task)
            await session.flush()
            await session.refresh(task)
            return task

    async def get_task(self, task_id: str) -> Task | None:
        """Get task by ID."""
        async with self.session() as session:
            return await session.get(Task, task_id)

    async def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        error_message: str | None = None,
        response_status: int | None = None,
        response_time_ms: float | None = None,
    ) -> None:
        """Update task status."""
        async with self.session() as session:
            task = await session.get(Task, task_id)
            if task:
                task.status = status
                task.error_message = error_message
                task.response_status = response_status
                task.response_time_ms = response_time_ms

                if status == TaskStatus.RUNNING:
                    task.started_at = datetime.now(UTC)
                    task.attempts += 1
                elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                    task.completed_at = datetime.now(UTC)

    async def get_pending_tasks(
        self,
        limit: int = 100,
        batch_id: str | None = None,
    ) -> list[Task]:
        """Get pending tasks."""
        async with self.session() as session:
            query = text("""
                SELECT * FROM tasks
                WHERE status = :status
                AND (attempts < max_attempts)
                AND (:batch_id IS NULL OR batch_id = :batch_id)
                ORDER BY priority DESC, created_at ASC
                LIMIT :limit
            """)
            result = await session.execute(
                query,
                {"status": TaskStatus.PENDING.value, "batch_id": batch_id, "limit": limit},
            )
            return list(result.scalars().all())

    # ==================== Proxy Operations ====================

    async def create_proxy(
        self,
        host: str,
        port: int,
        protocol: str = "http",
        username: str | None = None,
        password: str | None = None,
        country: str | None = None,
    ) -> Proxy:
        """Create or update a proxy."""
        async with self.session() as session:
            # Check if exists
            query = text("""
                SELECT id FROM proxies
                WHERE host = :host AND port = :port AND protocol = :protocol
            """)
            result = await session.execute(
                query, {"host": host, "port": port, "protocol": protocol}
            )
            existing = result.scalar()

            if existing:
                proxy = await session.get(Proxy, existing)
                proxy.username = username
                proxy.password = password
                proxy.country = country
            else:
                proxy = Proxy(
                    host=host,
                    port=port,
                    protocol=protocol,
                    username=username,
                    password=password,
                    country=country,
                )
                session.add(proxy)

            await session.flush()
            await session.refresh(proxy)
            return proxy

    async def update_proxy_health(
        self,
        proxy_id: str,
        health: ProxyHealthStatus,
        response_time_ms: float | None = None,
        success: bool = True,
    ) -> None:
        """Update proxy health status."""
        async with self.session() as session:
            proxy = await session.get(Proxy, proxy_id)
            if proxy:
                proxy.health = health
                proxy.last_check = datetime.now(UTC)
                proxy.total_requests += 1

                if success:
                    proxy.successful_requests += 1
                    proxy.last_success = datetime.now(UTC)
                    proxy.consecutive_failures = 0
                    if response_time_ms:
                        if proxy.avg_response_time_ms:
                            proxy.avg_response_time_ms = (
                                proxy.avg_response_time_ms * 0.9 + response_time_ms * 0.1
                            )
                        else:
                            proxy.avg_response_time_ms = response_time_ms
                else:
                    proxy.failed_requests += 1
                    proxy.last_failure = datetime.now(UTC)
                    proxy.consecutive_failures += 1

                # Update score
                proxy.score = self._calculate_proxy_score(proxy)

    def _calculate_proxy_score(self, proxy: Proxy) -> float:
        """Calculate proxy score."""
        if proxy.health == ProxyHealthStatus.BANNED:
            return 0.0

        base_score = proxy.success_rate * 60

        if proxy.avg_response_time_ms:
            time_penalty = min(20, proxy.avg_response_time_ms / 500)
            base_score -= time_penalty

        health_bonus = {
            ProxyHealthStatus.HEALTHY: 20,
            ProxyHealthStatus.DEGRADED: 5,
            ProxyHealthStatus.UNKNOWN: 0,
            ProxyHealthStatus.UNHEALTHY: -10,
        }
        base_score += health_bonus.get(proxy.health, 0)

        return max(0.0, min(100.0, base_score))

    async def get_healthy_proxies(self, limit: int = 100) -> list[Proxy]:
        """Get healthy proxies sorted by score."""
        async with self.session() as session:
            query = text("""
                SELECT * FROM proxies
                WHERE health IN (:healthy, :degraded, :unknown)
                ORDER BY score DESC
                LIMIT :limit
            """)
            result = await session.execute(
                query,
                {
                    "healthy": ProxyHealthStatus.HEALTHY.value,
                    "degraded": ProxyHealthStatus.DEGRADED.value,
                    "unknown": ProxyHealthStatus.UNKNOWN.value,
                    "limit": limit,
                },
            )
            return list(result.scalars().all())

    # ==================== Session Operations ====================

    async def create_session(
        self,
        fingerprint_id: str | None = None,
        user_persona: str | None = None,
    ) -> SessionModel:
        """Create a new browser session."""
        async with self.session() as db_session:
            session = SessionModel(
                fingerprint_id=fingerprint_id,
                user_persona=user_persona,
            )
            db_session.add(session)
            await db_session.flush()
            await db_session.refresh(session)
            return session

    async def update_session_activity(
        self,
        session_id: str,
        pages_visited: int | None = None,
        clicks: int | None = None,
        keystrokes: int | None = None,
        cookies: list[dict] | None = None,
    ) -> None:
        """Update session activity."""
        async with self.session() as db_session:
            session = await db_session.get(SessionModel, session_id)
            if session:
                session.last_activity = datetime.now(UTC)
                if pages_visited:
                    session.pages_visited = pages_visited
                if clicks:
                    session.total_clicks = clicks
                if keystrokes:
                    session.total_keystrokes = keystrokes
                if cookies:
                    session.cookies = cookies

    # ==================== Metrics Operations ====================

    async def record_metric(
        self,
        name: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Record a metric sample."""
        async with self.session() as session:
            sample = MetricSample(
                name=name,
                value=value,
                labels=labels or {},
            )
            session.add(sample)

    async def get_metrics(
        self,
        name: str,
        since: datetime | None = None,
        labels: dict[str, str] | None = None,
        limit: int = 1000,
    ) -> list[MetricSample]:
        """Get metric samples."""
        async with self.session() as session:
            query = "SELECT * FROM metric_samples WHERE name = :name"
            params: dict[str, Any] = {"name": name}

            if since:
                query += " AND timestamp >= :since"
                params["since"] = since

            query += " ORDER BY timestamp DESC LIMIT :limit"
            params["limit"] = limit

            result = await session.execute(text(query), params)
            return list(result.scalars().all())

    # ==================== Event Log Operations ====================

    async def log_event(
        self,
        event_type: str,
        message: str,
        severity: str = "info",
        task_id: str | None = None,
        proxy_id: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Log an event."""
        async with self.session() as session:
            event = EventLog(
                event_type=event_type,
                message=message,
                severity=severity,
                task_id=task_id,
                proxy_id=proxy_id,
                data=data,
            )
            session.add(event)

    # ==================== API Key Operations ====================

    async def create_api_key(
        self,
        key_hash: str,
        name: str | None = None,
        permissions: list[str] | None = None,
        rate_limit: int = 1000,
    ) -> ApiKey:
        """Create an API key."""
        async with self.session() as session:
            api_key = ApiKey(
                key_hash=key_hash,
                name=name,
                permissions=permissions or ["read"],
                rate_limit=rate_limit,
            )
            session.add(api_key)
            await session.flush()
            await session.refresh(api_key)
            return api_key

    async def validate_api_key(self, key_hash: str) -> ApiKey | None:
        """Validate an API key and update usage."""
        async with self.session() as session:
            query = text("""
                SELECT * FROM api_keys
                WHERE key_hash = :key_hash
                AND is_active = 1
                AND (expires_at IS NULL OR expires_at > :now)
            """)
            result = await session.execute(
                query, {"key_hash": key_hash, "now": datetime.now(UTC)}
            )
            api_key = result.scalar_one_or_none()

            if api_key:
                api_key.last_used = datetime.now(UTC)
                api_key.total_requests += 1

            return api_key


# Global database instance
_db: Database | None = None


async def get_database(config: DatabaseConfig | None = None) -> Database:
    """Get or create global database instance."""
    global _db
    if _db is None:
        _db = Database(config)
        await _db.init()
    return _db


async def close_database() -> None:
    """Close global database instance."""
    global _db
    if _db:
        await _db.close()
        _db = None
