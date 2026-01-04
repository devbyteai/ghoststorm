"""DOM intelligence module for smart element detection and analysis."""

from ghoststorm.core.dom.analyzer import DOMAnalyzer
from ghoststorm.core.dom.clickable import ClickableDetector
from ghoststorm.core.dom.models import (
    BoundingBox,
    DOMConfig,
    DOMNode,
    DOMState,
    ElementInfo,
    ElementType,
    InteractionType,
)
from ghoststorm.core.dom.selector import SelectorGenerator
from ghoststorm.core.dom.service import DOMService

__all__ = [
    "BoundingBox",
    "ClickableDetector",
    # Components
    "DOMAnalyzer",
    # Models
    "DOMConfig",
    "DOMNode",
    # Main service
    "DOMService",
    "DOMState",
    "ElementInfo",
    "ElementType",
    "InteractionType",
    "SelectorGenerator",
]
