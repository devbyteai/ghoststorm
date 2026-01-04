"""Behavior simulation plugins for human-like interactions."""

from ghoststorm.plugins.behavior.coherence_engine import (
    AttentionState,
    CircadianProfile,
    CoherenceConfig,
    CoherenceEngine,
    SessionPhase,
    SessionState,
    UserPersona,
    get_coherence_engine,
)
from ghoststorm.plugins.behavior.keyboard_plugin import KeyboardBehavior
from ghoststorm.plugins.behavior.ml_mouse import (
    MLMouseConfig,
    MLMouseGenerator,
    MLMousePlugin,
    MovementStyle,
    Point,
    Trajectory,
    get_ml_mouse_generator,
)
from ghoststorm.plugins.behavior.mouse_plugin import MouseBehavior
from ghoststorm.plugins.behavior.organic_browsing import (
    BrowseSessionResult,
    OrganicBrowsingBehavior,
    OrganicBrowsingConfig,
)
from ghoststorm.plugins.behavior.scroll_plugin import ScrollBehavior
from ghoststorm.plugins.behavior.timing_plugin import TimingBehavior
from ghoststorm.plugins.behavior.url_filter import URLFilter, URLFilterConfig
from ghoststorm.plugins.behavior.utm_injector import UTMConfig, UTMInjector

__all__ = [
    # Core behavior
    "MouseBehavior",
    "KeyboardBehavior",
    "ScrollBehavior",
    "TimingBehavior",
    # ML Mouse
    "MLMouseGenerator",
    "MLMouseConfig",
    "MLMousePlugin",
    "MovementStyle",
    "Trajectory",
    "Point",
    "get_ml_mouse_generator",
    # Coherence Engine
    "CoherenceEngine",
    "CoherenceConfig",
    "SessionState",
    "UserPersona",
    "AttentionState",
    "SessionPhase",
    "CircadianProfile",
    "get_coherence_engine",
    # Traffic behavior
    "OrganicBrowsingBehavior",
    "OrganicBrowsingConfig",
    "BrowseSessionResult",
    "UTMInjector",
    "UTMConfig",
    "URLFilter",
    "URLFilterConfig",
]
