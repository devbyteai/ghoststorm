"""DOM extraction and analysis service."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Protocol

import structlog

from ghoststorm.core.dom.analyzer import DOMAnalyzer
from ghoststorm.core.dom.clickable import ClickableDetector
from ghoststorm.core.dom.models import (
    BoundingBox,
    DOMConfig,
    DOMNode,
    DOMState,
    ElementInfo,
    ElementType,
)
from ghoststorm.core.dom.selector import SelectorGenerator

if TYPE_CHECKING:
    pass

logger = structlog.get_logger(__name__)


class IPage(Protocol):
    """Protocol for browser page interface."""

    async def evaluate(self, expression: str) -> Any:
        """Evaluate JavaScript expression."""
        ...

    async def url(self) -> str:
        """Get current page URL."""
        ...

    async def title(self) -> str:
        """Get page title."""
        ...

    @property
    def viewport_size(self) -> dict[str, int] | None:
        """Get viewport size."""
        ...


# JavaScript for DOM extraction
DOM_EXTRACTION_SCRIPT = """
() => {
    const extractNode = (element, depth = 0, maxDepth = 10) => {
        if (depth > maxDepth || !element || element.nodeType !== 1) {
            return null;
        }

        const tag = element.tagName.toLowerCase();
        const rect = element.getBoundingClientRect();
        const style = window.getComputedStyle(element);

        // Check visibility
        const isVisible = rect.width > 0 && rect.height > 0 &&
            style.display !== 'none' &&
            style.visibility !== 'hidden' &&
            parseFloat(style.opacity) > 0;

        // Get attributes
        const attributes = {};
        for (const attr of element.attributes) {
            attributes[attr.name] = attr.value;
        }

        // Get text content (direct text only, not children)
        let text = '';
        for (const child of element.childNodes) {
            if (child.nodeType === 3) {  // Text node
                text += child.textContent.trim();
            }
        }

        // Get computed styles we care about
        const computedStyle = {
            cursor: style.cursor,
            display: style.display,
            visibility: style.visibility,
        };

        const node = {
            tag,
            nodeId: element.dataset.psNodeId || Math.random().toString(36).substr(2, 9),
            text: text.substring(0, 200),
            attributes,
            computedStyle,
            boundingBox: {
                x: rect.x,
                y: rect.y,
                width: rect.width,
                height: rect.height
            },
            isVisible,
            depth,
            children: []
        };

        // Store node ID for reference
        element.dataset.psNodeId = node.nodeId;

        // Process children
        for (const child of element.children) {
            const childNode = extractNode(child, depth + 1, maxDepth);
            if (childNode) {
                childNode.parentId = node.nodeId;
                node.children.push(childNode);
            }
        }

        return node;
    };

    // Start from body
    return extractNode(document.body, 0, 10);
}
"""


class DOMService:
    """
    Service for extracting and analyzing DOM structure.

    Provides:
    - Full DOM tree extraction
    - Interactive element detection
    - Smart selector generation
    - Natural language element matching
    """

    def __init__(self, config: DOMConfig | None = None) -> None:
        """
        Initialize DOM service.

        Args:
            config: Optional configuration
        """
        self.config = config or DOMConfig()
        self.analyzer = DOMAnalyzer()
        self.clickable_detector = ClickableDetector()
        self.selector_generator = SelectorGenerator(
            prefer_id=self.config.prefer_id,
            prefer_test_attrs=self.config.prefer_data_testid,
            prefer_aria=self.config.prefer_aria,
        )

    async def extract_dom(self, page: IPage) -> DOMState:
        """
        Extract complete DOM state from a page.

        Args:
            page: Browser page to extract from

        Returns:
            DOMState with full DOM tree and interactive elements
        """
        logger.debug("Extracting DOM")

        # Get page info
        url = await page.url()
        title = await page.title()

        viewport = page.viewport_size or {"width": 1920, "height": 1080}
        viewport_width = viewport["width"]
        viewport_height = viewport["height"]

        # Extract raw DOM
        raw_dom = await page.evaluate(DOM_EXTRACTION_SCRIPT)

        if not raw_dom:
            logger.warning("DOM extraction returned empty")
            return DOMState(
                url=url,
                title=title,
                viewport_width=viewport_width,
                viewport_height=viewport_height,
            )

        # Build structured tree
        dom_tree = self._build_tree(raw_dom)

        # Find interactive elements
        interactive = self.clickable_detector.find_all(dom_tree)

        # Filter by visibility if configured
        if self.config.viewport_only:
            interactive = self.clickable_detector.filter_visible_in_viewport(
                interactive, viewport_width, viewport_height
            )

        # Generate selectors and create ElementInfo list
        clickables: list[ElementInfo] = []
        inputs: list[ElementInfo] = []
        links: list[ElementInfo] = []
        selector_map: dict[str, ElementInfo] = {}

        index = 0
        for node in interactive:
            selector = self.selector_generator.generate(node)
            xpath = self.selector_generator.generate_xpath(node)
            description = self.clickable_detector.get_description(node)

            elem_info = ElementInfo(
                node=node,
                selector=selector,
                xpath=xpath,
                description=description,
                index=index,
            )

            # Categorize by type
            if node.element_type in (ElementType.BUTTON, ElementType.CHECKBOX, ElementType.RADIO):
                clickables.append(elem_info)
            elif node.element_type in (ElementType.INPUT, ElementType.TEXTAREA, ElementType.SELECT):
                inputs.append(elem_info)
            elif node.element_type == ElementType.LINK:
                links.append(elem_info)
            else:
                clickables.append(elem_info)

            selector_map[selector] = elem_info
            index += 1

        logger.info(
            "DOM extracted",
            url=url,
            clickables=len(clickables),
            inputs=len(inputs),
            links=len(links),
        )

        return DOMState(
            url=url,
            title=title,
            tree=dom_tree,
            clickables=clickables,
            inputs=inputs,
            links=links,
            selector_map=selector_map,
            timestamp=datetime.now(),
            viewport_width=viewport_width,
            viewport_height=viewport_height,
        )

    def _build_tree(self, raw_node: dict) -> DOMNode:
        """Build DOMNode tree from raw extraction data."""
        bounding_box = None
        if "boundingBox" in raw_node:
            bb = raw_node["boundingBox"]
            bounding_box = BoundingBox(
                x=bb.get("x", 0),
                y=bb.get("y", 0),
                width=bb.get("width", 0),
                height=bb.get("height", 0),
            )

        node = DOMNode(
            tag=raw_node.get("tag", "unknown"),
            node_id=raw_node.get("nodeId", ""),
            text=raw_node.get("text", ""),
            attributes=raw_node.get("attributes", {}),
            computed_style=raw_node.get("computedStyle", {}),
            bounding_box=bounding_box,
            is_visible=raw_node.get("isVisible", True),
            depth=raw_node.get("depth", 0),
            parent_id=raw_node.get("parentId"),
        )

        # Recursively build children
        for child_data in raw_node.get("children", []):
            child_node = self._build_tree(child_data)
            node.children.append(child_node)

        return node

    async def find_element(
        self,
        page: IPage,
        description: str,
        element_type: ElementType | None = None,
    ) -> ElementInfo | None:
        """
        Find an element matching a natural language description.

        Args:
            page: Browser page to search
            description: Natural language description
            element_type: Optional filter by type

        Returns:
            Matching ElementInfo or None
        """
        dom_state = await self.extract_dom(page)
        return self.analyzer.find_best_match(dom_state, description, element_type)

    async def find_elements(
        self,
        page: IPage,
        description: str,
        element_type: ElementType | None = None,
        max_results: int = 5,
    ) -> list[ElementInfo]:
        """
        Find multiple elements matching a description.

        Args:
            page: Browser page to search
            description: Natural language description
            element_type: Optional filter by type
            max_results: Maximum results to return

        Returns:
            List of matching ElementInfo
        """
        dom_state = await self.extract_dom(page)
        return self.analyzer.find_matches(dom_state, description, element_type, max_results)

    async def get_clickable_elements(self, page: IPage) -> list[ElementInfo]:
        """Get all clickable elements on the page."""
        dom_state = await self.extract_dom(page)
        return dom_state.clickables

    async def get_input_elements(self, page: IPage) -> list[ElementInfo]:
        """Get all input elements on the page."""
        dom_state = await self.extract_dom(page)
        return dom_state.inputs

    async def get_links(self, page: IPage) -> list[ElementInfo]:
        """Get all links on the page."""
        dom_state = await self.extract_dom(page)
        return dom_state.links

    async def get_form_fields(self, page: IPage) -> dict[str, ElementInfo]:
        """Get form fields mapped by label/name."""
        dom_state = await self.extract_dom(page)
        return self.analyzer.find_form_fields(dom_state)
