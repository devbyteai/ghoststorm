"""Page context and state models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ghoststorm.core.interfaces.browser import IPage
    from ghoststorm.core.models.fingerprint import Fingerprint
    from ghoststorm.core.models.proxy import Proxy


@dataclass
class PageMetrics:
    """Page performance metrics."""

    # Timing
    navigation_start: float | None = None
    dom_content_loaded: float | None = None
    load_complete: float | None = None
    first_paint: float | None = None
    first_contentful_paint: float | None = None

    # Resources
    total_resources: int = 0
    total_bytes: int = 0
    cached_resources: int = 0

    # Errors
    js_errors: list[str] = field(default_factory=list)
    console_errors: list[str] = field(default_factory=list)
    failed_requests: list[str] = field(default_factory=list)

    @property
    def load_time_ms(self) -> float | None:
        """Calculate total page load time."""
        if self.navigation_start and self.load_complete:
            return self.load_complete - self.navigation_start
        return None


@dataclass
class RequestInfo:
    """Information about a network request."""

    url: str
    method: str
    resource_type: str
    status: int | None = None
    headers: dict[str, str] = field(default_factory=dict)
    response_headers: dict[str, str] = field(default_factory=dict)
    size_bytes: int = 0
    timing_ms: float | None = None
    from_cache: bool = False
    blocked: bool = False
    error: str | None = None


@dataclass
class PageState:
    """Current state of a page."""

    url: str
    title: str = ""
    status_code: int | None = None

    # State flags
    is_loaded: bool = False
    is_navigating: bool = False
    has_errors: bool = False

    # Content
    html_length: int = 0
    visible_text_length: int = 0

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    loaded_at: datetime | None = None
    last_activity: datetime = field(default_factory=datetime.now)

    # Metrics
    metrics: PageMetrics = field(default_factory=PageMetrics)

    # Request log
    requests: list[RequestInfo] = field(default_factory=list)

    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.now()

    def mark_loaded(self, status_code: int | None = None) -> None:
        """Mark page as loaded."""
        self.is_loaded = True
        self.is_navigating = False
        self.loaded_at = datetime.now()
        self.status_code = status_code
        self.update_activity()

    def add_request(self, request: RequestInfo) -> None:
        """Add a request to the log."""
        self.requests.append(request)
        self.metrics.total_resources += 1
        if request.size_bytes:
            self.metrics.total_bytes += request.size_bytes
        if request.from_cache:
            self.metrics.cached_resources += 1
        if request.error:
            self.metrics.failed_requests.append(request.url)
            self.has_errors = True

    def add_error(self, error: str, is_js_error: bool = True) -> None:
        """Add an error to the log."""
        self.has_errors = True
        if is_js_error:
            self.metrics.js_errors.append(error)
        else:
            self.metrics.console_errors.append(error)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "url": self.url,
            "title": self.title,
            "status_code": self.status_code,
            "is_loaded": self.is_loaded,
            "has_errors": self.has_errors,
            "html_length": self.html_length,
            "created_at": self.created_at.isoformat(),
            "loaded_at": self.loaded_at.isoformat() if self.loaded_at else None,
            "load_time_ms": self.metrics.load_time_ms,
            "total_requests": self.metrics.total_resources,
            "total_bytes": self.metrics.total_bytes,
            "error_count": len(self.metrics.js_errors) + len(self.metrics.failed_requests),
        }


@dataclass
class PageContext:
    """Extended context for a page including automation metadata."""

    page: IPage
    state: PageState

    # Identity
    session_id: str = ""
    context_id: str = ""

    # Resources
    proxy: Proxy | None = None
    fingerprint: Fingerprint | None = None

    # Tracking
    pages_visited: int = 0
    actions_performed: int = 0
    screenshots_taken: int = 0

    # Session data
    cookies_set: int = 0
    storage_items: int = 0

    # Flags
    captcha_encountered: bool = False
    bot_detection_triggered: bool = False
    rate_limited: bool = False

    def increment_visits(self) -> None:
        """Increment page visit counter."""
        self.pages_visited += 1

    def increment_actions(self, count: int = 1) -> None:
        """Increment action counter."""
        self.actions_performed += count

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "context_id": self.context_id,
            "url": self.state.url,
            "proxy_id": self.proxy.id if self.proxy else None,
            "fingerprint_id": self.fingerprint.id if self.fingerprint else None,
            "pages_visited": self.pages_visited,
            "actions_performed": self.actions_performed,
            "captcha_encountered": self.captcha_encountered,
            "bot_detection_triggered": self.bot_detection_triggered,
            "state": self.state.to_dict(),
        }
