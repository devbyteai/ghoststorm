"""Clickable element detector."""

from __future__ import annotations

import structlog

from ghoststorm.core.dom.models import (
    DOMNode,
    ElementType,
    InteractionType,
)

logger = structlog.get_logger(__name__)


class ClickableDetector:
    """
    Detects interactive/clickable elements in the DOM.

    Uses multiple strategies:
    1. Tag-based detection (button, a, input, etc.)
    2. ARIA role detection
    3. Event handler detection (onclick, onmousedown, etc.)
    4. Cursor style detection
    5. Contenteditable detection
    """

    # Tags that are inherently interactive
    INTERACTIVE_TAGS = {
        "button",
        "a",
        "input",
        "select",
        "textarea",
        "label",
        "option",
        "details",
        "summary",
    }

    # ARIA roles that indicate interactivity
    INTERACTIVE_ROLES = {
        "button",
        "link",
        "checkbox",
        "radio",
        "menuitem",
        "menuitemcheckbox",
        "menuitemradio",
        "tab",
        "switch",
        "option",
        "combobox",
        "listbox",
        "slider",
        "spinbutton",
        "searchbox",
        "textbox",
        "treeitem",
        "gridcell",
    }

    # Event handler attributes that indicate interactivity
    EVENT_HANDLERS = {
        "onclick",
        "onmousedown",
        "onmouseup",
        "ontouchstart",
        "ontouchend",
        "onkeydown",
        "onkeyup",
        "onkeypress",
        "onchange",
        "oninput",
        "onfocus",
        "onblur",
    }

    # Map of tags to element types
    TAG_TO_TYPE = {
        "button": ElementType.BUTTON,
        "a": ElementType.LINK,
        "input": ElementType.INPUT,
        "select": ElementType.SELECT,
        "textarea": ElementType.TEXTAREA,
        "img": ElementType.IMAGE,
        "video": ElementType.VIDEO,
        "form": ElementType.FORM,
        "div": ElementType.CONTAINER,
        "span": ElementType.TEXT,
    }

    # Map of input types to element types
    INPUT_TYPE_MAP = {
        "checkbox": ElementType.CHECKBOX,
        "radio": ElementType.RADIO,
        "submit": ElementType.BUTTON,
        "button": ElementType.BUTTON,
        "image": ElementType.IMAGE,
    }

    def __init__(self) -> None:
        """Initialize the detector."""
        pass

    def is_interactive(self, node: DOMNode) -> bool:
        """
        Determine if a node is interactive.

        Args:
            node: DOM node to check

        Returns:
            True if the node is interactive
        """
        # Must be visible
        if not node.is_visible:
            return False

        # Check tag
        if node.tag.lower() in self.INTERACTIVE_TAGS:
            return True

        # Check ARIA role
        role = node.role
        if role and role.lower() in self.INTERACTIVE_ROLES:
            return True

        # Check for event handlers
        for attr in node.attributes:
            if attr.lower() in self.EVENT_HANDLERS:
                return True

        # Check cursor style
        cursor = node.computed_style.get("cursor", "").lower()
        if cursor == "pointer":
            return True

        # Check contenteditable
        if node.attributes.get("contenteditable") == "true":
            return True

        # Check tabindex (positive tabindex makes element focusable)
        tabindex = node.attributes.get("tabindex")
        if tabindex is not None:
            try:
                if int(tabindex) >= 0:
                    return True
            except ValueError:
                pass

        # Check for data attributes that often indicate interactivity
        for attr in node.attributes:
            if attr.startswith("data-") and any(
                keyword in attr.lower()
                for keyword in ["click", "action", "toggle", "trigger", "open", "close"]
            ):
                return True

        return False

    def classify_element(self, node: DOMNode) -> tuple[ElementType, InteractionType]:
        """
        Classify the element type and interaction type.

        Args:
            node: DOM node to classify

        Returns:
            Tuple of (ElementType, InteractionType)
        """
        tag = node.tag.lower()

        # Handle input elements specially
        if tag == "input":
            input_type = node.input_type or "text"
            input_type = input_type.lower()

            if input_type in self.INPUT_TYPE_MAP:
                elem_type = self.INPUT_TYPE_MAP[input_type]
            else:
                elem_type = ElementType.INPUT

            if input_type in ("checkbox", "radio"):
                return elem_type, InteractionType.CLICK
            elif input_type in ("submit", "button", "image"):
                return elem_type, InteractionType.CLICK
            elif input_type == "file":
                return ElementType.INPUT, InteractionType.UPLOAD
            else:
                return elem_type, InteractionType.TYPE

        # Handle other tags
        if tag in self.TAG_TO_TYPE:
            elem_type = self.TAG_TO_TYPE[tag]
        else:
            elem_type = ElementType.UNKNOWN

        # Determine interaction type
        if tag in ("button", "a"):
            return elem_type, InteractionType.CLICK
        elif tag in ("textarea",):
            return elem_type, InteractionType.TYPE
        elif tag == "select":
            return elem_type, InteractionType.SELECT

        # Check ARIA role
        role = node.role
        if role:
            role = role.lower()
            if role in ("button", "link", "menuitem", "tab"):
                return ElementType.BUTTON, InteractionType.CLICK
            elif role in ("checkbox", "radio", "switch"):
                return ElementType.CHECKBOX, InteractionType.CLICK
            elif role in ("textbox", "searchbox"):
                return ElementType.INPUT, InteractionType.TYPE
            elif role in ("combobox", "listbox"):
                return ElementType.SELECT, InteractionType.SELECT
            elif role == "slider":
                return ElementType.INPUT, InteractionType.DRAG

        # Default: if interactive, assume clickable
        if self.is_interactive(node):
            return elem_type, InteractionType.CLICK

        return elem_type, InteractionType.NONE

    def find_all(self, root: DOMNode) -> list[DOMNode]:
        """
        Find all interactive elements in the DOM tree.

        Args:
            root: Root node to search from

        Returns:
            List of interactive DOM nodes
        """
        interactive = []
        self._find_recursive(root, interactive)
        return interactive

    def _find_recursive(self, node: DOMNode, results: list[DOMNode]) -> None:
        """Recursively find interactive elements."""
        if self.is_interactive(node):
            # Classify the element
            elem_type, interaction_type = self.classify_element(node)
            node.is_interactive = True
            node.element_type = elem_type
            node.interaction_type = interaction_type
            results.append(node)

        # Continue searching children
        for child in node.children:
            self._find_recursive(child, results)

    def filter_by_type(
        self, nodes: list[DOMNode], element_type: ElementType
    ) -> list[DOMNode]:
        """Filter nodes by element type."""
        return [n for n in nodes if n.element_type == element_type]

    def filter_visible_in_viewport(
        self,
        nodes: list[DOMNode],
        viewport_width: int,
        viewport_height: int,
    ) -> list[DOMNode]:
        """Filter to only nodes visible in viewport."""
        visible = []
        for node in nodes:
            if node.bounding_box:
                if node.bounding_box.is_visible(viewport_width, viewport_height):
                    visible.append(node)
        return visible

    def get_description(self, node: DOMNode) -> str:
        """
        Generate a human-readable description of an element.

        Args:
            node: DOM node to describe

        Returns:
            Description string
        """
        parts = []

        # Element type
        parts.append(node.element_type.value.title())

        # Text content
        if node.text:
            text = node.text[:50]
            if len(node.text) > 50:
                text += "..."
            parts.append(f'"{text}"')

        # ARIA label
        if node.aria_label:
            parts.append(f"[aria-label: {node.aria_label}]")

        # Placeholder
        if node.placeholder:
            parts.append(f"[placeholder: {node.placeholder}]")

        # href for links
        if node.href:
            href = node.href[:50]
            if len(node.href) > 50:
                href += "..."
            parts.append(f"-> {href}")

        return " ".join(parts)
