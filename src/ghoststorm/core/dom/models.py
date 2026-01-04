"""Data models for DOM intelligence."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ElementType(str, Enum):
    """Types of DOM elements."""

    BUTTON = "button"
    LINK = "link"
    INPUT = "input"
    SELECT = "select"
    TEXTAREA = "textarea"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    IMAGE = "image"
    VIDEO = "video"
    FORM = "form"
    CONTAINER = "container"
    TEXT = "text"
    UNKNOWN = "unknown"


class InteractionType(str, Enum):
    """Types of interactions possible with an element."""

    CLICK = "click"
    TYPE = "type"
    SELECT = "select"
    SCROLL = "scroll"
    HOVER = "hover"
    DRAG = "drag"
    UPLOAD = "upload"
    NONE = "none"


@dataclass
class BoundingBox:
    """Element bounding box coordinates."""

    x: float
    y: float
    width: float
    height: float

    @property
    def center_x(self) -> float:
        """Get center X coordinate."""
        return self.x + self.width / 2

    @property
    def center_y(self) -> float:
        """Get center Y coordinate."""
        return self.y + self.height / 2

    @property
    def area(self) -> float:
        """Calculate area of bounding box."""
        return self.width * self.height

    def is_visible(self, viewport_width: int, viewport_height: int) -> bool:
        """Check if element is within viewport."""
        return (
            self.x + self.width > 0
            and self.y + self.height > 0
            and self.x < viewport_width
            and self.y < viewport_height
        )

    def to_dict(self) -> dict[str, float]:
        """Convert to dictionary."""
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
        }

    @classmethod
    def from_dict(cls, data: dict[str, float]) -> BoundingBox:
        """Create from dictionary."""
        return cls(
            x=data.get("x", 0),
            y=data.get("y", 0),
            width=data.get("width", 0),
            height=data.get("height", 0),
        )


@dataclass
class DOMNode:
    """Represents a DOM element."""

    tag: str
    node_id: str = ""
    text: str = ""
    attributes: dict[str, str] = field(default_factory=dict)
    computed_style: dict[str, str] = field(default_factory=dict)
    bounding_box: BoundingBox | None = None
    children: list[DOMNode] = field(default_factory=list)
    parent_id: str | None = None
    depth: int = 0

    # Computed properties
    is_visible: bool = True
    is_interactive: bool = False
    element_type: ElementType = ElementType.UNKNOWN
    interaction_type: InteractionType = InteractionType.NONE

    @property
    def id_attr(self) -> str | None:
        """Get the id attribute."""
        return self.attributes.get("id")

    @property
    def class_list(self) -> list[str]:
        """Get list of CSS classes."""
        class_attr = self.attributes.get("class", "")
        return class_attr.split() if class_attr else []

    @property
    def role(self) -> str | None:
        """Get ARIA role."""
        return self.attributes.get("role")

    @property
    def aria_label(self) -> str | None:
        """Get aria-label."""
        return self.attributes.get("aria-label")

    @property
    def href(self) -> str | None:
        """Get href attribute for links."""
        return self.attributes.get("href")

    @property
    def name(self) -> str | None:
        """Get name attribute."""
        return self.attributes.get("name")

    @property
    def value(self) -> str | None:
        """Get value attribute."""
        return self.attributes.get("value")

    @property
    def placeholder(self) -> str | None:
        """Get placeholder attribute."""
        return self.attributes.get("placeholder")

    @property
    def input_type(self) -> str | None:
        """Get input type attribute."""
        return self.attributes.get("type")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tag": self.tag,
            "node_id": self.node_id,
            "text": self.text,
            "attributes": self.attributes,
            "bounding_box": self.bounding_box.to_dict() if self.bounding_box else None,
            "is_visible": self.is_visible,
            "is_interactive": self.is_interactive,
            "element_type": self.element_type.value,
            "interaction_type": self.interaction_type.value,
            "depth": self.depth,
            "children_count": len(self.children),
        }


@dataclass
class ElementInfo:
    """Information about an interactive element."""

    node: DOMNode
    selector: str
    xpath: str = ""
    confidence: float = 1.0
    description: str = ""
    index: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "node": self.node.to_dict(),
            "selector": self.selector,
            "xpath": self.xpath,
            "confidence": self.confidence,
            "description": self.description,
            "index": self.index,
        }


@dataclass
class DOMState:
    """Complete DOM state snapshot."""

    url: str
    title: str = ""
    tree: DOMNode | None = None
    clickables: list[ElementInfo] = field(default_factory=list)
    inputs: list[ElementInfo] = field(default_factory=list)
    links: list[ElementInfo] = field(default_factory=list)
    selector_map: dict[str, ElementInfo] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    viewport_width: int = 1920
    viewport_height: int = 1080

    @property
    def interactive_count(self) -> int:
        """Count of all interactive elements."""
        return len(self.clickables) + len(self.inputs) + len(self.links)

    def get_by_index(self, index: int) -> ElementInfo | None:
        """Get element by index from all interactive elements."""
        all_elements = self.clickables + self.inputs + self.links
        for elem in all_elements:
            if elem.index == index:
                return elem
        return None

    def get_by_text(self, text: str, fuzzy: bool = True) -> list[ElementInfo]:
        """Find elements containing the given text."""
        results = []
        all_elements = self.clickables + self.inputs + self.links

        for elem in all_elements:
            node_text = elem.node.text.lower()
            search_text = text.lower()

            if fuzzy:
                if search_text in node_text:
                    results.append(elem)
            else:
                if node_text == search_text:
                    results.append(elem)

        return results

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "url": self.url,
            "title": self.title,
            "timestamp": self.timestamp.isoformat(),
            "viewport": {
                "width": self.viewport_width,
                "height": self.viewport_height,
            },
            "counts": {
                "clickables": len(self.clickables),
                "inputs": len(self.inputs),
                "links": len(self.links),
                "total_interactive": self.interactive_count,
            },
            "clickables": [e.to_dict() for e in self.clickables[:20]],  # Limit for serialization
            "inputs": [e.to_dict() for e in self.inputs[:20]],
            "links": [e.to_dict() for e in self.links[:20]],
        }

    def to_prompt(self, max_elements: int = 30) -> str:
        """Convert to LLM-friendly prompt format."""
        lines = [
            f"Page: {self.title}",
            f"URL: {self.url}",
            f"Viewport: {self.viewport_width}x{self.viewport_height}",
            "",
            "Interactive Elements:",
        ]

        all_elements = (self.clickables + self.inputs + self.links)[:max_elements]

        for elem in all_elements:
            node = elem.node
            text = node.text[:50] if node.text else ""
            aria = node.aria_label or ""
            placeholder = node.placeholder or ""

            label = text or aria or placeholder or node.tag

            lines.append(
                f"[{elem.index}] {node.element_type.value}: {label} "
                f"(selector: {elem.selector})"
            )

        return "\n".join(lines)


@dataclass
class DOMConfig:
    """Configuration for DOM extraction."""

    include_hidden: bool = False
    max_depth: int = 10
    extract_styles: bool = False
    extract_computed_styles: bool = False
    viewport_only: bool = True
    interactive_only: bool = False
    max_elements: int = 1000

    # Selector generation preferences
    prefer_id: bool = True
    prefer_data_testid: bool = True
    prefer_aria: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "include_hidden": self.include_hidden,
            "max_depth": self.max_depth,
            "extract_styles": self.extract_styles,
            "extract_computed_styles": self.extract_computed_styles,
            "viewport_only": self.viewport_only,
            "interactive_only": self.interactive_only,
            "max_elements": self.max_elements,
        }
