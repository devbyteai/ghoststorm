"""Tests for the watchdog system."""

import asyncio
import pytest
from datetime import datetime

# Test models
from ghoststorm.core.watchdog.models import (
    HealthLevel,
    HealthStatus,
    FailureInfo,
    RecoveryAction,
    RecoveryResult,
    WatchdogConfig,
    WatchdogState,
    WatchdogAlert,
)


class TestWatchdogModels:
    """Tests for watchdog data models."""

    def test_health_level_values(self):
        """Test HealthLevel enum values."""
        assert HealthLevel.HEALTHY == "healthy"
        assert HealthLevel.DEGRADED == "degraded"
        assert HealthLevel.UNHEALTHY == "unhealthy"
        assert HealthLevel.CRITICAL == "critical"
        assert HealthLevel.UNKNOWN == "unknown"

    def test_recovery_action_values(self):
        """Test RecoveryAction enum values."""
        assert RecoveryAction.RESTART_BROWSER == "restart_browser"
        assert RecoveryAction.RETRY_PAGE == "retry_page"
        assert RecoveryAction.ROTATE_PROXY == "rotate_proxy"
        assert RecoveryAction.BACKOFF == "backoff"
        assert RecoveryAction.NONE == "none"

    def test_watchdog_config_defaults(self):
        """Test WatchdogConfig default values."""
        config = WatchdogConfig()
        assert config.enabled is True
        assert config.health_check_interval == 30.0
        assert config.auto_recovery is True
        assert config.max_recovery_attempts == 3
        assert config.recovery_cooldown == 5.0
        assert config.alert_threshold == 3
        assert config.browser_timeout == 60.0
        assert config.page_timeout == 30.0
        assert config.network_timeout == 15.0

    def test_watchdog_config_validation(self):
        """Test WatchdogConfig validation."""
        # Test minimum health_check_interval
        config = WatchdogConfig(health_check_interval=0.5)
        assert config.health_check_interval == 1.0  # Should be clamped

        # Test minimum max_recovery_attempts
        config = WatchdogConfig(max_recovery_attempts=0)
        assert config.max_recovery_attempts == 1  # Should be clamped

    def test_health_status_is_healthy(self):
        """Test HealthStatus.is_healthy property."""
        healthy = HealthStatus(level=HealthLevel.HEALTHY, message="OK")
        degraded = HealthStatus(level=HealthLevel.DEGRADED, message="Degraded")
        unhealthy = HealthStatus(level=HealthLevel.UNHEALTHY, message="Bad")
        critical = HealthStatus(level=HealthLevel.CRITICAL, message="Critical")

        assert healthy.is_healthy is True
        assert degraded.is_healthy is True  # Degraded is still operational
        assert unhealthy.is_healthy is False
        assert critical.is_healthy is False

    def test_health_status_score(self):
        """Test HealthStatus.score calculation."""
        status = HealthStatus(
            level=HealthLevel.HEALTHY,
            message="OK",
            checks_passed=8,
            checks_failed=2,
        )
        assert status.score == 0.8

        # Empty checks should return 1.0 for healthy
        status = HealthStatus(level=HealthLevel.HEALTHY, message="OK")
        assert status.score == 1.0

        # Empty checks should return 0.0 for unhealthy
        status = HealthStatus(level=HealthLevel.UNHEALTHY, message="Bad")
        assert status.score == 0.0

    def test_health_status_to_dict(self):
        """Test HealthStatus serialization."""
        status = HealthStatus(
            level=HealthLevel.HEALTHY,
            message="All good",
            details={"test": "value"},
            checks_passed=5,
            checks_failed=1,
        )
        d = status.to_dict()

        assert d["level"] == "healthy"
        assert d["message"] == "All good"
        assert d["details"] == {"test": "value"}
        assert d["checks_passed"] == 5
        assert d["checks_failed"] == 1
        assert "timestamp" in d
        assert "score" in d

    def test_failure_info_creation(self):
        """Test FailureInfo creation."""
        failure = FailureInfo(
            watchdog_name="TestWatchdog",
            failure_type="test_failure",
            error="Something went wrong",
            error_type="TestError",
            context={"key": "value"},
            severity=HealthLevel.UNHEALTHY,
            recoverable=True,
            suggested_action=RecoveryAction.RETRY_PAGE,
        )

        assert failure.watchdog_name == "TestWatchdog"
        assert failure.failure_type == "test_failure"
        assert failure.error == "Something went wrong"
        assert failure.recoverable is True
        assert failure.suggested_action == RecoveryAction.RETRY_PAGE

    def test_failure_info_to_dict(self):
        """Test FailureInfo serialization."""
        failure = FailureInfo(
            watchdog_name="TestWatchdog",
            failure_type="test_failure",
            error="Error message",
        )
        d = failure.to_dict()

        assert d["watchdog_name"] == "TestWatchdog"
        assert d["failure_type"] == "test_failure"
        assert d["error"] == "Error message"
        assert "timestamp" in d

    def test_recovery_result_creation(self):
        """Test RecoveryResult creation."""
        result = RecoveryResult(
            success=True,
            action_taken=RecoveryAction.RESTART_BROWSER,
            message="Browser restarted",
            duration_ms=1500.0,
            attempts=2,
        )

        assert result.success is True
        assert result.action_taken == RecoveryAction.RESTART_BROWSER
        assert result.message == "Browser restarted"
        assert result.duration_ms == 1500.0
        assert result.attempts == 2

    def test_watchdog_state_defaults(self):
        """Test WatchdogState default values."""
        state = WatchdogState(name="TestWatchdog")

        assert state.name == "TestWatchdog"
        assert state.enabled is True
        assert state.running is False
        assert state.total_events == 0
        assert state.failures_detected == 0
        assert state.recoveries_attempted == 0
        assert state.recoveries_successful == 0

    def test_watchdog_state_recovery_rate(self):
        """Test WatchdogState.recovery_success_rate calculation."""
        state = WatchdogState(
            name="TestWatchdog",
            recoveries_attempted=10,
            recoveries_successful=8,
        )
        assert state.recovery_success_rate == 0.8

        # No attempts should return 1.0
        state = WatchdogState(name="TestWatchdog")
        assert state.recovery_success_rate == 1.0

    def test_watchdog_alert_creation(self):
        """Test WatchdogAlert creation."""
        failure = FailureInfo(
            watchdog_name="TestWatchdog",
            failure_type="test",
            error="Error",
        )
        alert = WatchdogAlert(
            watchdog_name="TestWatchdog",
            level=HealthLevel.CRITICAL,
            title="Critical Alert",
            message="Something critical happened",
            failure=failure,
        )

        assert alert.watchdog_name == "TestWatchdog"
        assert alert.level == HealthLevel.CRITICAL
        assert alert.title == "Critical Alert"
        assert alert.failure is not None


class TestAsyncWatchdogComponents:
    """Async tests for watchdog components."""

    @pytest.fixture
    def event_bus(self):
        """Create event bus for testing."""
        from ghoststorm.core.events.bus import AsyncEventBus
        return AsyncEventBus()

    @pytest.fixture
    def watchdog_config(self):
        """Create watchdog config for testing."""
        return WatchdogConfig(
            health_check_interval=1.0,  # Fast for testing
            auto_recovery=True,
            max_recovery_attempts=3,
        )

    @pytest.mark.asyncio
    async def test_event_bus_start_stop(self, event_bus):
        """Test event bus lifecycle."""
        assert event_bus.is_running is False

        await event_bus.start()
        assert event_bus.is_running is True

        await event_bus.stop()
        assert event_bus.is_running is False

    @pytest.mark.asyncio
    async def test_watchdog_manager_lifecycle(self, event_bus, watchdog_config):
        """Test WatchdogManager start/stop."""
        from ghoststorm.core.watchdog import WatchdogManager

        manager = WatchdogManager(event_bus, watchdog_config)

        assert manager.is_running is False
        assert manager.watchdog_count == 0

        await event_bus.start()
        await manager.start()

        assert manager.is_running is True

        await manager.stop()
        assert manager.is_running is False

        await event_bus.stop()

    @pytest.mark.asyncio
    async def test_watchdog_manager_register(self, event_bus, watchdog_config):
        """Test registering watchdogs with manager."""
        from ghoststorm.core.watchdog import (
            WatchdogManager,
            BrowserWatchdog,
            PageWatchdog,
        )

        manager = WatchdogManager(event_bus, watchdog_config)

        # Register watchdogs
        browser_wd = BrowserWatchdog(event_bus, watchdog_config)
        page_wd = PageWatchdog(event_bus, watchdog_config)

        manager.register(browser_wd)
        manager.register(page_wd)

        assert manager.watchdog_count == 2
        assert manager.get("BrowserWatchdog") is browser_wd
        assert manager.get("PageWatchdog") is page_wd

        # Test duplicate registration
        with pytest.raises(ValueError):
            manager.register(browser_wd)

    @pytest.mark.asyncio
    async def test_browser_watchdog_health_check(self, event_bus, watchdog_config):
        """Test BrowserWatchdog health check."""
        from ghoststorm.core.watchdog import BrowserWatchdog

        watchdog = BrowserWatchdog(event_bus, watchdog_config)

        # Before any browser events, should be unhealthy
        health = await watchdog.check_health()
        assert health.level == HealthLevel.UNHEALTHY
        assert "not running" in health.message.lower()

    @pytest.mark.asyncio
    async def test_page_watchdog_health_check(self, event_bus, watchdog_config):
        """Test PageWatchdog health check."""
        from ghoststorm.core.watchdog import PageWatchdog

        watchdog = PageWatchdog(event_bus, watchdog_config)

        # With no activity, should be healthy
        health = await watchdog.check_health()
        assert health.level == HealthLevel.HEALTHY

    @pytest.mark.asyncio
    async def test_network_watchdog_health_check(self, event_bus, watchdog_config):
        """Test NetworkWatchdog health check."""
        from ghoststorm.core.watchdog import NetworkWatchdog

        watchdog = NetworkWatchdog(event_bus, watchdog_config)

        # With no activity, should be healthy
        health = await watchdog.check_health()
        assert health.level == HealthLevel.HEALTHY

    @pytest.mark.asyncio
    async def test_health_watchdog_health_check(self, event_bus, watchdog_config):
        """Test HealthWatchdog health check."""
        from ghoststorm.core.watchdog import HealthWatchdog

        watchdog = HealthWatchdog(event_bus, watchdog_config)

        # Engine not running should be unhealthy
        health = await watchdog.check_health()
        assert health.level == HealthLevel.UNHEALTHY
        assert "not running" in health.message.lower()

    @pytest.mark.asyncio
    async def test_watchdog_event_handling(self, event_bus, watchdog_config):
        """Test watchdog receives and processes events."""
        from ghoststorm.core.watchdog import BrowserWatchdog
        from ghoststorm.core.events.types import EventType

        watchdog = BrowserWatchdog(event_bus, watchdog_config)

        await event_bus.start()
        await watchdog.start()

        # Emit browser launched event
        await event_bus.emit(
            EventType.BROWSER_LAUNCHED,
            {"engine": "test"},
            source="test",
        )

        # Give event time to process
        await asyncio.sleep(0.1)

        # Check that state was updated
        assert watchdog.state.total_events >= 1

        # Now browser should be healthy
        health = await watchdog.check_health()
        assert health.level == HealthLevel.HEALTHY

        await watchdog.stop()
        await event_bus.stop()

    @pytest.mark.asyncio
    async def test_manager_aggregate_health(self, event_bus, watchdog_config):
        """Test WatchdogManager aggregates health from all watchdogs."""
        from ghoststorm.core.watchdog import (
            WatchdogManager,
            PageWatchdog,
            NetworkWatchdog,
        )

        manager = WatchdogManager(event_bus, watchdog_config)

        # Register healthy watchdogs only
        manager.register(PageWatchdog(event_bus, watchdog_config))
        manager.register(NetworkWatchdog(event_bus, watchdog_config))

        await event_bus.start()
        await manager.start()

        health = await manager.check_health()
        # Both should be healthy
        assert health.level == HealthLevel.HEALTHY

        await manager.stop()
        await event_bus.stop()

    @pytest.mark.asyncio
    async def test_manager_stats(self, event_bus, watchdog_config):
        """Test WatchdogManager stats collection."""
        from ghoststorm.core.watchdog import WatchdogManager, PageWatchdog

        manager = WatchdogManager(event_bus, watchdog_config)
        manager.register(PageWatchdog(event_bus, watchdog_config))

        await event_bus.start()
        await manager.start()

        stats = manager.get_stats()

        assert "running" in stats
        assert stats["running"] is True
        assert "watchdog_count" in stats
        assert stats["watchdog_count"] == 1
        assert "watchdogs" in stats

        await manager.stop()
        await event_bus.stop()


class TestWatchdogIntegration:
    """Integration tests for watchdog with orchestrator."""

    @pytest.mark.asyncio
    async def test_config_has_watchdog_settings(self):
        """Test that Config includes watchdog settings."""
        from ghoststorm.core.models.config import Config

        config = Config()

        assert hasattr(config, "watchdog")
        assert config.watchdog.enabled is True
        assert config.watchdog.health_check_interval == 30.0

    @pytest.mark.asyncio
    async def test_orchestrator_has_watchdog_manager(self):
        """Test that Orchestrator initializes WatchdogManager."""
        from ghoststorm.core.models.config import Config
        from ghoststorm.core.engine.orchestrator import Orchestrator

        config = Config()
        orchestrator = Orchestrator(config)

        assert hasattr(orchestrator, "watchdog_manager")
        assert orchestrator.watchdog_manager is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
