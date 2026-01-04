"""Smart selector generator for DOM elements."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from ghoststorm.core.dom.models import DOMNode

logger = structlog.get_logger(__name__)


class SelectorGenerator:
    """
    Generates robust CSS selectors and XPaths for DOM elements.

    Prioritizes selectors in this order:
    1. ID (most reliable)
    2. data-testid / data-cy / data-test (testing attributes)
    3. ARIA attributes (accessible)
    4. Name attribute
    5. Unique class combinations
    6. Position-based (last resort)
    """

    # Testing-related data attributes
    TEST_ATTRIBUTES = [
        "data-testid",
        "data-test-id",
        "data-test",
        "data-cy",
        "data-qa",
        "data-automation",
    ]

    def __init__(
        self,
        prefer_id: bool = True,
        prefer_test_attrs: bool = True,
        prefer_aria: bool = True,
    ) -> None:
        """
        Initialize selector generator.

        Args:
            prefer_id: Prefer ID selectors when available
            prefer_test_attrs: Prefer data-testid and similar
            prefer_aria: Prefer ARIA-based selectors
        """
        self.prefer_id = prefer_id
        self.prefer_test_attrs = prefer_test_attrs
        self.prefer_aria = prefer_aria

    def generate(self, node: DOMNode, parent_chain: list[DOMNode] | None = None) -> str:
        """
        Generate the best CSS selector for an element.

        Args:
            node: DOM node to generate selector for
            parent_chain: Optional list of parent nodes for context

        Returns:
            CSS selector string
        """
        # Try ID first (most reliable)
        if self.prefer_id and node.id_attr:
            selector = self._selector_by_id(node)
            if selector:
                return selector

        # Try test attributes
        if self.prefer_test_attrs:
            selector = self._selector_by_test_attr(node)
            if selector:
                return selector

        # Try ARIA attributes
        if self.prefer_aria:
            selector = self._selector_by_aria(node)
            if selector:
                return selector

        # Try name attribute
        selector = self._selector_by_name(node)
        if selector:
            return selector

        # Try unique class combination
        selector = self._selector_by_classes(node)
        if selector:
            return selector

        # Try tag + text content match
        selector = self._selector_by_text(node)
        if selector:
            return selector

        # Fall back to nth-child path
        if parent_chain:
            return self._selector_by_path(node, parent_chain)

        # Last resort: tag only
        return node.tag.lower()

    def generate_xpath(self, node: DOMNode, parent_chain: list[DOMNode] | None = None) -> str:
        """
        Generate XPath for an element.

        Args:
            node: DOM node to generate XPath for
            parent_chain: Optional list of parent nodes

        Returns:
            XPath string
        """
        # Try ID
        if node.id_attr:
            return f'//*[@id="{node.id_attr}"]'

        # Try test attributes
        for attr in self.TEST_ATTRIBUTES:
            if attr in node.attributes:
                value = node.attributes[attr]
                return f'//*[@{attr}="{value}"]'

        # Try ARIA label
        if node.aria_label:
            return f'//*[@aria-label="{node.aria_label}"]'

        # Try text content
        if node.text and len(node.text) < 50:
            # Escape quotes
            text = node.text.replace('"', '\\"')
            return f'//{node.tag.lower()}[contains(text(), "{text}")]'

        # Build path from parent chain
        if parent_chain:
            return self._xpath_by_path(node, parent_chain)

        return f"//{node.tag.lower()}"

    def _selector_by_id(self, node: DOMNode) -> str | None:
        """Generate selector using ID attribute."""
        if not node.id_attr:
            return None

        # Validate ID (must be valid CSS identifier)
        id_value = node.id_attr
        if not self._is_valid_id(id_value):
            return None

        # Check if ID starts with a number (needs escaping)
        if id_value[0].isdigit():
            return f'[id="{id_value}"]'

        return f"#{id_value}"

    def _selector_by_test_attr(self, node: DOMNode) -> str | None:
        """Generate selector using test attributes."""
        for attr in self.TEST_ATTRIBUTES:
            if attr in node.attributes:
                value = node.attributes[attr]
                return f'[{attr}="{value}"]'
        return None

    def _selector_by_aria(self, node: DOMNode) -> str | None:
        """Generate selector using ARIA attributes."""
        # Try aria-label
        if node.aria_label:
            return f'{node.tag.lower()}[aria-label="{node.aria_label}"]'

        # Try role + other attributes
        if node.role:
            if node.attributes.get("aria-labelledby"):
                return f'[role="{node.role}"][aria-labelledby="{node.attributes["aria-labelledby"]}"]'

        return None

    def _selector_by_name(self, node: DOMNode) -> str | None:
        """Generate selector using name attribute."""
        name = node.name
        if name:
            return f'{node.tag.lower()}[name="{name}"]'
        return None

    def _selector_by_classes(self, node: DOMNode) -> str | None:
        """Generate selector using class combination."""
        classes = node.class_list
        if not classes:
            return None

        # Filter out utility classes and common names
        meaningful_classes = [
            c for c in classes
            if not self._is_utility_class(c)
        ]

        if not meaningful_classes:
            return None

        # Use up to 3 most specific classes
        classes_to_use = meaningful_classes[:3]

        # Build selector
        class_selector = ".".join(f".{c}" for c in classes_to_use)
        return f"{node.tag.lower()}{class_selector}"

    def _selector_by_text(self, node: DOMNode) -> str | None:
        """Generate selector by text content match."""
        # Only for buttons and links
        if node.tag.lower() not in ("button", "a", "span"):
            return None

        text = node.text.strip()
        if not text or len(text) > 30:
            return None

        # Use contains for partial match
        # Note: This returns a selector that uses :contains() which isn't standard CSS
        # but works with Playwright/Puppeteer
        return f'{node.tag.lower()}:has-text("{text}")'

    def _selector_by_path(self, node: DOMNode, parent_chain: list[DOMNode]) -> str:
        """Generate selector using parent path."""
        parts = []

        # Build path from parents
        for parent in parent_chain[-3:]:  # Last 3 parents
            if parent.id_attr:
                parts.append(f"#{parent.id_attr}")
                break
            elif parent.class_list:
                class_part = ".".join(parent.class_list[:2])
                parts.append(f"{parent.tag.lower()}.{class_part}")
            else:
                parts.append(parent.tag.lower())

        # Add the target node
        if node.class_list:
            parts.append(f"{node.tag.lower()}.{node.class_list[0]}")
        else:
            parts.append(node.tag.lower())

        return " > ".join(parts)

    def _xpath_by_path(self, node: DOMNode, parent_chain: list[DOMNode]) -> str:
        """Generate XPath using parent path."""
        parts = []

        for parent in parent_chain:
            if parent.id_attr:
                parts.append(f'//*[@id="{parent.id_attr}"]')
                break
            else:
                parts.append(parent.tag.lower())

        parts.append(node.tag.lower())

        return "//" + "/".join(parts)

    def _is_valid_id(self, id_value: str) -> bool:
        """Check if ID is valid for CSS selector."""
        if not id_value:
            return False

        # Must not contain certain characters
        if any(c in id_value for c in " .:[]()"):
            return False

        return True

    def _is_utility_class(self, class_name: str) -> bool:
        """Check if class is a utility class (Tailwind, Bootstrap, etc.)."""
        # Common utility class patterns
        utility_patterns = [
            r"^(m|p|w|h|flex|grid|block|inline)-",  # Tailwind spacing/display
            r"^(text|bg|border|rounded)-",  # Tailwind styling
            r"^(col|row|container|d-)-",  # Bootstrap
            r"^(u-|js-|is-|has-)",  # Common prefixes
            r"^[a-z]{1,2}-\d+$",  # Short utilities like "p-4"
        ]

        for pattern in utility_patterns:
            if re.match(pattern, class_name, re.IGNORECASE):
                return True

        return False

    def generate_all(self, node: DOMNode, parent_chain: list[DOMNode] | None = None) -> dict[str, str]:
        """
        Generate multiple selector types for an element.

        Returns:
            Dictionary with 'css', 'xpath', 'best' keys
        """
        css = self.generate(node, parent_chain)
        xpath = self.generate_xpath(node, parent_chain)

        return {
            "css": css,
            "xpath": xpath,
            "best": css,  # CSS is generally preferred
        }
