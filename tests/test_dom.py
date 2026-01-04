"""Tests for DOM intelligence module."""

import pytest

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


class TestBoundingBox:
    """Tests for BoundingBox model."""

    def test_bounding_box_center(self):
        """Test center coordinate calculation."""
        bbox = BoundingBox(x=100, y=200, width=50, height=30)
        assert bbox.center_x == 125
        assert bbox.center_y == 215

    def test_bounding_box_area(self):
        """Test area calculation."""
        bbox = BoundingBox(x=0, y=0, width=100, height=50)
        assert bbox.area == 5000

    def test_bounding_box_visibility(self):
        """Test visibility check."""
        bbox = BoundingBox(x=100, y=100, width=50, height=50)

        # Fully visible
        assert bbox.is_visible(1920, 1080) is True

        # Off screen left
        bbox = BoundingBox(x=-100, y=100, width=50, height=50)
        assert bbox.is_visible(1920, 1080) is False

        # Partially visible
        bbox = BoundingBox(x=-25, y=100, width=50, height=50)
        assert bbox.is_visible(1920, 1080) is True

    def test_bounding_box_to_dict(self):
        """Test serialization."""
        bbox = BoundingBox(x=10, y=20, width=30, height=40)
        d = bbox.to_dict()

        assert d["x"] == 10
        assert d["y"] == 20
        assert d["width"] == 30
        assert d["height"] == 40

    def test_bounding_box_from_dict(self):
        """Test deserialization."""
        bbox = BoundingBox.from_dict({"x": 10, "y": 20, "width": 30, "height": 40})
        assert bbox.x == 10
        assert bbox.y == 20


class TestDOMNode:
    """Tests for DOMNode model."""

    def test_dom_node_creation(self):
        """Test basic node creation."""
        node = DOMNode(
            tag="button",
            node_id="btn-1",
            text="Click me",
            attributes={"id": "submit-btn", "class": "btn primary"},
        )

        assert node.tag == "button"
        assert node.text == "Click me"
        assert node.id_attr == "submit-btn"
        assert node.class_list == ["btn", "primary"]

    def test_dom_node_properties(self):
        """Test computed properties."""
        node = DOMNode(
            tag="a",
            attributes={
                "href": "https://example.com",
                "aria-label": "Go to example",
                "role": "link",
            },
        )

        assert node.href == "https://example.com"
        assert node.aria_label == "Go to example"
        assert node.role == "link"

    def test_dom_node_input_properties(self):
        """Test input-specific properties."""
        node = DOMNode(
            tag="input",
            attributes={
                "type": "email",
                "name": "email",
                "placeholder": "Enter email",
            },
        )

        assert node.input_type == "email"
        assert node.name == "email"
        assert node.placeholder == "Enter email"


class TestDOMState:
    """Tests for DOMState model."""

    def test_dom_state_creation(self):
        """Test basic state creation."""
        state = DOMState(
            url="https://example.com",
            title="Example Page",
        )

        assert state.url == "https://example.com"
        assert state.title == "Example Page"
        assert state.interactive_count == 0

    def test_dom_state_get_by_text(self):
        """Test finding elements by text."""
        node1 = DOMNode(tag="button", text="Submit Form")
        node2 = DOMNode(tag="button", text="Cancel")

        state = DOMState(
            url="https://example.com",
            clickables=[
                ElementInfo(node=node1, selector="#submit", index=0),
                ElementInfo(node=node2, selector="#cancel", index=1),
            ],
        )

        results = state.get_by_text("submit")
        assert len(results) == 1
        assert results[0].node.text == "Submit Form"

    def test_dom_state_get_by_index(self):
        """Test finding element by index."""
        node = DOMNode(tag="button", text="Click")

        state = DOMState(
            url="https://example.com",
            clickables=[
                ElementInfo(node=node, selector="#btn", index=5),
            ],
        )

        elem = state.get_by_index(5)
        assert elem is not None
        assert elem.selector == "#btn"

        # Non-existent index
        assert state.get_by_index(99) is None


class TestClickableDetector:
    """Tests for ClickableDetector."""

    @pytest.fixture
    def detector(self):
        return ClickableDetector()

    def test_button_is_interactive(self, detector):
        """Test button detection."""
        node = DOMNode(tag="button", text="Click", is_visible=True)
        assert detector.is_interactive(node) is True

    def test_link_is_interactive(self, detector):
        """Test link detection."""
        node = DOMNode(tag="a", attributes={"href": "/page"}, is_visible=True)
        assert detector.is_interactive(node) is True

    def test_input_is_interactive(self, detector):
        """Test input detection."""
        node = DOMNode(tag="input", attributes={"type": "text"}, is_visible=True)
        assert detector.is_interactive(node) is True

    def test_div_with_role_is_interactive(self, detector):
        """Test ARIA role detection."""
        node = DOMNode(tag="div", attributes={"role": "button"}, is_visible=True)
        assert detector.is_interactive(node) is True

    def test_div_with_onclick_is_interactive(self, detector):
        """Test event handler detection."""
        node = DOMNode(tag="div", attributes={"onclick": "handleClick()"}, is_visible=True)
        assert detector.is_interactive(node) is True

    def test_div_with_pointer_cursor_is_interactive(self, detector):
        """Test cursor style detection."""
        node = DOMNode(
            tag="div",
            computed_style={"cursor": "pointer"},
            is_visible=True,
        )
        assert detector.is_interactive(node) is True

    def test_hidden_element_not_interactive(self, detector):
        """Test hidden elements are not interactive."""
        node = DOMNode(tag="button", is_visible=False)
        assert detector.is_interactive(node) is False

    def test_classify_button(self, detector):
        """Test button classification."""
        node = DOMNode(tag="button")
        elem_type, interaction = detector.classify_element(node)

        assert elem_type == ElementType.BUTTON
        assert interaction == InteractionType.CLICK

    def test_classify_input_text(self, detector):
        """Test text input classification."""
        node = DOMNode(tag="input", attributes={"type": "text"})
        elem_type, interaction = detector.classify_element(node)

        assert elem_type == ElementType.INPUT
        assert interaction == InteractionType.TYPE

    def test_classify_checkbox(self, detector):
        """Test checkbox classification."""
        node = DOMNode(tag="input", attributes={"type": "checkbox"})
        elem_type, interaction = detector.classify_element(node)

        assert elem_type == ElementType.CHECKBOX
        assert interaction == InteractionType.CLICK

    def test_find_all(self, detector):
        """Test finding all interactive elements."""
        root = DOMNode(
            tag="div",
            is_visible=True,
            children=[
                DOMNode(tag="button", text="Click", is_visible=True),
                DOMNode(tag="span", text="Text", is_visible=True),
                DOMNode(tag="a", attributes={"href": "#"}, is_visible=True),
            ],
        )

        interactive = detector.find_all(root)
        assert len(interactive) == 2  # button and link

    def test_get_description(self, detector):
        """Test element description generation."""
        node = DOMNode(
            tag="button",
            text="Submit Form",
            element_type=ElementType.BUTTON,
        )

        desc = detector.get_description(node)
        assert "Button" in desc
        assert "Submit Form" in desc


class TestSelectorGenerator:
    """Tests for SelectorGenerator."""

    @pytest.fixture
    def generator(self):
        return SelectorGenerator()

    def test_selector_by_id(self, generator):
        """Test ID-based selector."""
        node = DOMNode(tag="button", attributes={"id": "submit-btn"})
        selector = generator.generate(node)

        assert selector == "#submit-btn"

    def test_selector_by_test_attr(self, generator):
        """Test data-testid selector."""
        node = DOMNode(tag="button", attributes={"data-testid": "submit"})
        selector = generator.generate(node)

        assert selector == '[data-testid="submit"]'

    def test_selector_by_aria_label(self, generator):
        """Test aria-label selector."""
        node = DOMNode(tag="button", attributes={"aria-label": "Submit form"})
        selector = generator.generate(node)

        assert 'aria-label="Submit form"' in selector

    def test_selector_by_name(self, generator):
        """Test name attribute selector."""
        node = DOMNode(tag="input", attributes={"name": "email"})
        selector = generator.generate(node)

        assert 'name="email"' in selector

    def test_xpath_by_id(self, generator):
        """Test XPath with ID."""
        node = DOMNode(tag="button", attributes={"id": "submit"})
        xpath = generator.generate_xpath(node)

        assert xpath == '//*[@id="submit"]'

    def test_xpath_by_text(self, generator):
        """Test XPath with text content."""
        node = DOMNode(tag="button", text="Click me")
        xpath = generator.generate_xpath(node)

        assert "contains(text()" in xpath
        assert "Click me" in xpath


class TestDOMAnalyzer:
    """Tests for DOMAnalyzer."""

    @pytest.fixture
    def analyzer(self):
        return DOMAnalyzer()

    @pytest.fixture
    def sample_state(self):
        """Create sample DOM state for testing."""
        login_btn = DOMNode(
            tag="button",
            text="Login",
            element_type=ElementType.BUTTON,
            is_visible=True,
        )
        submit_btn = DOMNode(
            tag="button",
            text="Submit Form",
            element_type=ElementType.BUTTON,
            is_visible=True,
        )
        email_input = DOMNode(
            tag="input",
            attributes={"placeholder": "Enter email", "type": "email"},
            element_type=ElementType.INPUT,
            is_visible=True,
        )

        return DOMState(
            url="https://example.com",
            clickables=[
                ElementInfo(node=login_btn, selector="#login", index=0),
                ElementInfo(node=submit_btn, selector="#submit", index=1),
            ],
            inputs=[
                ElementInfo(node=email_input, selector="#email", index=2),
            ],
        )

    def test_find_by_exact_text(self, analyzer, sample_state):
        """Test finding element by exact text match."""
        matches = analyzer.find_matches(sample_state, '"Login"')

        assert len(matches) >= 1
        assert matches[0].node.text == "Login"

    def test_find_by_description(self, analyzer, sample_state):
        """Test finding element by description."""
        matches = analyzer.find_matches(sample_state, "click the login button")

        assert len(matches) >= 1
        # Login button should score highest due to keyword match
        texts = [m.node.text for m in matches]
        assert "Login" in texts

    def test_find_input_field(self, analyzer, sample_state):
        """Test finding input by placeholder."""
        matches = analyzer.find_matches(sample_state, "enter email")

        assert len(matches) >= 1

    def test_find_by_role(self, analyzer, sample_state):
        """Test finding by ARIA role."""
        # Create state with role
        node = DOMNode(
            tag="div",
            attributes={"role": "button", "aria-label": "Close dialog"},
            element_type=ElementType.BUTTON,
        )
        state = DOMState(
            url="https://example.com",
            clickables=[ElementInfo(node=node, selector="[role=button]", index=0)],
        )

        results = analyzer.find_by_role(state, "button", "close")
        assert len(results) == 1


class TestDOMConfig:
    """Tests for DOMConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = DOMConfig()

        assert config.include_hidden is False
        assert config.max_depth == 10
        assert config.viewport_only is True
        assert config.prefer_id is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = DOMConfig(
            include_hidden=True,
            max_depth=5,
            viewport_only=False,
        )

        assert config.include_hidden is True
        assert config.max_depth == 5
        assert config.viewport_only is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
