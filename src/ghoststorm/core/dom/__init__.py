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
    # Main service
    "DOMService",
    # Components
    "DOMAnalyzer",
    "ClickableDetector",
    "SelectorGenerator",
    # Models
    "DOMConfig",
    "DOMState",
    "DOMNode",
    "ElementInfo",
    "BoundingBox",
    "ElementType",
    "InteractionType",
]
