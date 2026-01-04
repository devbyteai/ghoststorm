"""DOM analyzer for element matching and scoring."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import TYPE_CHECKING

import structlog

from ghoststorm.core.dom.models import DOMNode, DOMState, ElementInfo, ElementType

if TYPE_CHECKING:
    pass

logger = structlog.get_logger(__name__)


class DOMAnalyzer:
    """
    Analyzes DOM structure and finds elements matching descriptions.

    Features:
    - Natural language element matching
    - Text similarity scoring
    - Semantic element matching
    - Priority-based element ranking
    """

    # Keywords for different element types
    TYPE_KEYWORDS = {
        ElementType.BUTTON: ["button", "btn", "click", "submit", "press", "tap"],
        ElementType.LINK: ["link", "go to", "navigate", "open", "visit"],
        ElementType.INPUT: ["input", "field", "type", "enter", "write", "fill"],
        ElementType.CHECKBOX: ["checkbox", "check", "toggle", "tick"],
        ElementType.RADIO: ["radio", "option", "select", "choose"],
        ElementType.SELECT: ["dropdown", "select", "choose", "pick"],
        ElementType.TEXTAREA: ["textarea", "text area", "message", "comment"],
    }

    # Common action verbs
    ACTION_VERBS = [
        "click",
        "tap",
        "press",
        "select",
        "choose",
        "enter",
        "type",
        "fill",
        "submit",
        "search",
        "find",
        "open",
        "close",
        "toggle",
    ]

    def __init__(self) -> None:
        """Initialize the analyzer."""
        pass

    def find_best_match(
        self,
        dom_state: DOMState,
        description: str,
        element_type: ElementType | None = None,
    ) -> ElementInfo | None:
        """
        Find the element that best matches a natural language description.

        Args:
            dom_state: Current DOM state
            description: Natural language description (e.g., "click the login button")
            element_type: Optional filter by element type

        Returns:
            Best matching ElementInfo or None
        """
        matches = self.find_matches(dom_state, description, element_type)

        if matches:
            return matches[0]
        return None

    def find_matches(
        self,
        dom_state: DOMState,
        description: str,
        element_type: ElementType | None = None,
        max_results: int = 5,
    ) -> list[ElementInfo]:
        """
        Find elements matching a description, ranked by relevance.

        Args:
            dom_state: Current DOM state
            description: Natural language description
            element_type: Optional filter by element type
            max_results: Maximum number of results to return

        Returns:
            List of matching ElementInfo, sorted by score (highest first)
        """
        # Parse the description
        parsed = self._parse_description(description)

        # Get candidate elements
        candidates = self._get_candidates(dom_state, element_type)

        # Score each candidate
        scored = []
        for elem in candidates:
            score = self._score_element(elem, parsed)
            if score > 0:
                scored.append((score, elem))

        # Sort by score (descending)
        scored.sort(key=lambda x: x[0], reverse=True)

        # Return top results
        return [elem for _, elem in scored[:max_results]]

    def _parse_description(self, description: str) -> dict:
        """
        Parse a natural language description into structured components.

        Args:
            description: The description to parse

        Returns:
            Dictionary with parsed components
        """
        description = description.lower().strip()

        # Extract action verb
        action = None
        for verb in self.ACTION_VERBS:
            if verb in description:
                action = verb
                break

        # Extract quoted text (exact match targets)
        quoted_matches = re.findall(r'"([^"]+)"', description)
        quoted_text = quoted_matches[0] if quoted_matches else None

        # Extract element type hints
        type_hints = []
        for elem_type, keywords in self.TYPE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in description:
                    type_hints.append(elem_type)
                    break

        # Extract remaining keywords
        # Remove action and common words
        stop_words = {"the", "a", "an", "to", "on", "in", "for", "with", "that", "this"}
        words = description.split()
        keywords = [
            w for w in words
            if w not in stop_words
            and w not in self.ACTION_VERBS
            and len(w) > 2
        ]

        return {
            "original": description,
            "action": action,
            "quoted_text": quoted_text,
            "type_hints": type_hints,
            "keywords": keywords,
        }

    def _get_candidates(
        self,
        dom_state: DOMState,
        element_type: ElementType | None,
    ) -> list[ElementInfo]:
        """Get candidate elements for matching."""
        all_elements = dom_state.clickables + dom_state.inputs + dom_state.links

        if element_type:
            return [e for e in all_elements if e.node.element_type == element_type]

        return all_elements

    def _score_element(self, elem: ElementInfo, parsed: dict) -> float:
        """
        Score how well an element matches the parsed description.

        Args:
            elem: Element to score
            parsed: Parsed description components

        Returns:
            Score from 0 to 1
        """
        node = elem.node
        score = 0.0

        # Exact quoted text match (highest priority)
        if parsed["quoted_text"]:
            quoted = parsed["quoted_text"].lower()

            # Check text content
            if node.text and quoted in node.text.lower():
                score += 0.5
            elif node.text and node.text.lower() == quoted:
                score += 0.7

            # Check aria-label
            if node.aria_label and quoted in node.aria_label.lower():
                score += 0.5

            # Check placeholder
            if node.placeholder and quoted in node.placeholder.lower():
                score += 0.4

        # Element type match
        if parsed["type_hints"]:
            if node.element_type in parsed["type_hints"]:
                score += 0.2

        # Keyword matching
        keywords = parsed["keywords"]
        if keywords:
            # Combine all text sources for matching
            element_text = " ".join(filter(None, [
                node.text,
                node.aria_label,
                node.placeholder,
                node.id_attr,
                " ".join(node.class_list),
            ])).lower()

            keyword_matches = sum(1 for kw in keywords if kw in element_text)
            if keywords:
                score += (keyword_matches / len(keywords)) * 0.3

        # Fuzzy text similarity
        if node.text:
            similarity = self._text_similarity(
                parsed["original"],
                node.text.lower()
            )
            score += similarity * 0.2

        # Bonus for visible elements
        if node.bounding_box and node.bounding_box.area > 0:
            score += 0.05

        # Bonus for elements with accessible labels
        if node.aria_label:
            score += 0.05

        return min(score, 1.0)

    def _text_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity using SequenceMatcher."""
        return SequenceMatcher(None, text1, text2).ratio()

    def find_by_selector(
        self,
        dom_state: DOMState,
        selector: str,
    ) -> ElementInfo | None:
        """
        Find element by CSS selector.

        Args:
            dom_state: Current DOM state
            selector: CSS selector

        Returns:
            Matching ElementInfo or None
        """
        return dom_state.selector_map.get(selector)

    def find_by_role(
        self,
        dom_state: DOMState,
        role: str,
        name: str | None = None,
    ) -> list[ElementInfo]:
        """
        Find elements by ARIA role.

        Args:
            dom_state: Current DOM state
            role: ARIA role to match
            name: Optional accessible name to match

        Returns:
            List of matching ElementInfo
        """
        all_elements = dom_state.clickables + dom_state.inputs + dom_state.links
        results = []

        for elem in all_elements:
            if elem.node.role == role:
                if name is None:
                    results.append(elem)
                elif elem.node.aria_label and name.lower() in elem.node.aria_label.lower():
                    results.append(elem)
                elif elem.node.text and name.lower() in elem.node.text.lower():
                    results.append(elem)

        return results

    def find_form_fields(self, dom_state: DOMState) -> dict[str, ElementInfo]:
        """
        Find form fields and map them by label/name.

        Returns:
            Dictionary mapping field labels to ElementInfo
        """
        fields = {}

        for elem in dom_state.inputs:
            node = elem.node

            # Use name attribute
            if node.name:
                fields[node.name] = elem

            # Use label/aria-label
            if node.aria_label:
                fields[node.aria_label.lower()] = elem

            # Use placeholder
            if node.placeholder:
                fields[node.placeholder.lower()] = elem

        return fields

    def get_clickables_summary(self, dom_state: DOMState, max_items: int = 10) -> str:
        """
        Get a summary of clickable elements for LLM context.

        Args:
            dom_state: Current DOM state
            max_items: Maximum items to include

        Returns:
            Formatted string summary
        """
        lines = []

        for i, elem in enumerate(dom_state.clickables[:max_items]):
            node = elem.node
            text = node.text[:30] if node.text else ""
            label = node.aria_label[:30] if node.aria_label else ""
            display = text or label or node.tag

            lines.append(f"{i + 1}. [{node.element_type.value}] {display}")

        if len(dom_state.clickables) > max_items:
            lines.append(f"... and {len(dom_state.clickables) - max_items} more")

        return "\n".join(lines)
