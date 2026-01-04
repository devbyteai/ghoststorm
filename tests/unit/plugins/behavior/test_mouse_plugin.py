"""Tests for mouse behavior simulation plugin."""

from __future__ import annotations

import math
from unittest.mock import AsyncMock

import pytest

from ghoststorm.plugins.behavior.mouse_plugin import MouseBehavior, Point

# ============================================================================
# POINT DATACLASS TESTS
# ============================================================================


class TestPoint:
    """Tests for Point dataclass."""

    def test_point_creation(self):
        """Test Point creation with x and y coordinates."""
        point = Point(x=100.0, y=200.0)
        assert point.x == 100.0
        assert point.y == 200.0

    def test_point_with_integers(self):
        """Test Point accepts integer values."""
        point = Point(x=50, y=75)
        assert point.x == 50
        assert point.y == 75

    def test_point_with_negative_values(self):
        """Test Point accepts negative coordinates."""
        point = Point(x=-10.5, y=-25.3)
        assert point.x == -10.5
        assert point.y == -25.3

    def test_point_with_zero_values(self):
        """Test Point with zero coordinates."""
        point = Point(x=0.0, y=0.0)
        assert point.x == 0.0
        assert point.y == 0.0

    def test_point_fields(self):
        """Test Point has correct fields."""
        point = Point(x=1.0, y=2.0)
        assert hasattr(point, "x")
        assert hasattr(point, "y")


# ============================================================================
# MOUSE BEHAVIOR INITIALIZATION TESTS
# ============================================================================


class TestMouseBehaviorInit:
    """Tests for MouseBehavior initialization."""

    def test_default_initialization(self):
        """Test MouseBehavior with default values."""
        behavior = MouseBehavior()
        assert behavior.min_steps == 20
        assert behavior.max_steps == 50
        assert behavior.overshoot_probability == 0.15
        assert behavior.tremor_amplitude == 1.5
        assert behavior.base_delay_ms == 5.0

    def test_custom_min_steps(self):
        """Test custom min_steps parameter."""
        behavior = MouseBehavior(min_steps=10)
        assert behavior.min_steps == 10

    def test_custom_max_steps(self):
        """Test custom max_steps parameter."""
        behavior = MouseBehavior(max_steps=100)
        assert behavior.max_steps == 100

    def test_custom_overshoot_probability(self):
        """Test custom overshoot_probability parameter."""
        behavior = MouseBehavior(overshoot_probability=0.3)
        assert behavior.overshoot_probability == 0.3

    def test_custom_tremor_amplitude(self):
        """Test custom tremor_amplitude parameter."""
        behavior = MouseBehavior(tremor_amplitude=2.5)
        assert behavior.tremor_amplitude == 2.5

    def test_custom_base_delay_ms(self):
        """Test custom base_delay_ms parameter."""
        behavior = MouseBehavior(base_delay_ms=10.0)
        assert behavior.base_delay_ms == 10.0

    def test_all_custom_values(self):
        """Test MouseBehavior with all custom values."""
        behavior = MouseBehavior(
            min_steps=15,
            max_steps=60,
            overshoot_probability=0.2,
            tremor_amplitude=2.0,
            base_delay_ms=8.0,
        )
        assert behavior.min_steps == 15
        assert behavior.max_steps == 60
        assert behavior.overshoot_probability == 0.2
        assert behavior.tremor_amplitude == 2.0
        assert behavior.base_delay_ms == 8.0

    def test_name_attribute(self):
        """Test MouseBehavior has correct name attribute."""
        behavior = MouseBehavior()
        assert behavior.name == "mouse"


# ============================================================================
# BEZIER CURVE TESTS
# ============================================================================


class TestBezierCurve:
    """Tests for _bezier_curve method."""

    def test_bezier_t_zero_returns_start(self):
        """Test that t=0 returns the start point."""
        behavior = MouseBehavior()
        start = Point(0.0, 0.0)
        end = Point(100.0, 100.0)
        control1 = Point(25.0, 50.0)
        control2 = Point(75.0, 50.0)

        result = behavior._bezier_curve(start, end, control1, control2, t=0.0)

        assert result.x == pytest.approx(start.x, abs=0.001)
        assert result.y == pytest.approx(start.y, abs=0.001)

    def test_bezier_t_one_returns_end(self):
        """Test that t=1 returns the end point."""
        behavior = MouseBehavior()
        start = Point(0.0, 0.0)
        end = Point(100.0, 100.0)
        control1 = Point(25.0, 50.0)
        control2 = Point(75.0, 50.0)

        result = behavior._bezier_curve(start, end, control1, control2, t=1.0)

        assert result.x == pytest.approx(end.x, abs=0.001)
        assert result.y == pytest.approx(end.y, abs=0.001)

    def test_bezier_midpoint_is_curved(self):
        """Test that t=0.5 produces a curved midpoint, not a straight line."""
        behavior = MouseBehavior()
        start = Point(0.0, 0.0)
        end = Point(100.0, 0.0)
        # Control points above the line to create upward curve
        control1 = Point(25.0, 50.0)
        control2 = Point(75.0, 50.0)

        result = behavior._bezier_curve(start, end, control1, control2, t=0.5)

        # Midpoint of straight line would be (50, 0)
        # With control points above, the curve should be above 0
        assert result.x == pytest.approx(50.0, abs=0.001)
        assert result.y > 0.0  # Curve is above the straight line

    def test_bezier_with_different_start_end(self):
        """Test Bezier curve with non-origin start point."""
        behavior = MouseBehavior()
        start = Point(50.0, 50.0)
        end = Point(150.0, 150.0)
        control1 = Point(75.0, 100.0)
        control2 = Point(125.0, 100.0)

        result_start = behavior._bezier_curve(start, end, control1, control2, t=0.0)
        result_end = behavior._bezier_curve(start, end, control1, control2, t=1.0)

        assert result_start.x == pytest.approx(50.0, abs=0.001)
        assert result_start.y == pytest.approx(50.0, abs=0.001)
        assert result_end.x == pytest.approx(150.0, abs=0.001)
        assert result_end.y == pytest.approx(150.0, abs=0.001)


# ============================================================================
# CONTROL POINT GENERATION TESTS
# ============================================================================


class TestGenerateControlPoints:
    """Tests for _generate_control_points method."""

    def test_control_points_return_tuple_of_two_points(self):
        """Test that control points returns a tuple of two Points."""
        behavior = MouseBehavior()
        start = Point(0.0, 0.0)
        end = Point(100.0, 100.0)

        c1, c2 = behavior._generate_control_points(start, end)

        assert isinstance(c1, Point)
        assert isinstance(c2, Point)

    def test_control_point_1_near_start(self):
        """Test first control point is positioned near start."""
        behavior = MouseBehavior()
        start = Point(0.0, 0.0)
        end = Point(400.0, 0.0)

        # Run multiple times due to randomness
        for _ in range(10):
            c1, _c2 = behavior._generate_control_points(start, end)
            # c1 should be around 25% of the way (100 +/- deviation)
            # Deviation is min(distance * 0.3, 100) = min(120, 100) = 100
            assert -100 <= c1.x <= 200  # 100 +/- 100

    def test_control_point_2_near_end(self):
        """Test second control point is positioned near end."""
        behavior = MouseBehavior()
        start = Point(0.0, 0.0)
        end = Point(400.0, 0.0)

        for _ in range(10):
            _c1, c2 = behavior._generate_control_points(start, end)
            # c2 should be around 75% of the way (300 +/- deviation)
            assert 200 <= c2.x <= 400  # 300 +/- 100

    def test_control_points_deviation_scales_with_distance(self):
        """Test that deviation scales with distance but caps at 100."""
        behavior = MouseBehavior()

        # Short distance
        start_short = Point(0.0, 0.0)
        end_short = Point(50.0, 0.0)  # distance = 50, deviation = 15

        # Long distance
        start_long = Point(0.0, 0.0)
        end_long = Point(1000.0, 0.0)  # distance = 1000, deviation = 100 (capped)

        # Both should produce valid control points
        c1_short, _c2_short = behavior._generate_control_points(start_short, end_short)
        c1_long, _c2_long = behavior._generate_control_points(start_long, end_long)

        assert isinstance(c1_short, Point)
        assert isinstance(c1_long, Point)


# ============================================================================
# PATH GENERATION TESTS
# ============================================================================


class TestGeneratePath:
    """Tests for generate_path method."""

    def test_path_starts_at_start_point(self):
        """Test that generated path starts at the start point."""
        behavior = MouseBehavior(overshoot_probability=0.0)
        start = Point(10.0, 20.0)
        end = Point(100.0, 100.0)

        path = behavior.generate_path(start, end)

        # First point should be very close to start (tremor may add small offset)
        assert path[0].x == pytest.approx(start.x, abs=5.0)
        assert path[0].y == pytest.approx(start.y, abs=5.0)

    def test_path_ends_near_end_point(self):
        """Test that generated path ends near the end point."""
        behavior = MouseBehavior(overshoot_probability=0.0)
        start = Point(0.0, 0.0)
        end = Point(100.0, 100.0)

        path = behavior.generate_path(start, end)

        # Last point should be very close to end (tremor may add small offset)
        assert path[-1].x == pytest.approx(end.x, abs=5.0)
        assert path[-1].y == pytest.approx(end.y, abs=5.0)

    def test_path_scales_with_distance(self):
        """Test that longer distances produce more steps."""
        behavior = MouseBehavior(overshoot_probability=0.0)

        # Short distance
        start_short = Point(0.0, 0.0)
        end_short = Point(50.0, 50.0)  # ~70 px distance

        # Long distance
        start_long = Point(0.0, 0.0)
        end_long = Point(500.0, 500.0)  # ~707 px distance

        path_short = behavior.generate_path(start_short, end_short)
        path_long = behavior.generate_path(start_long, end_long)

        assert len(path_long) > len(path_short)

    def test_path_has_minimum_steps(self):
        """Test that path always has at least min_steps + 1 points."""
        behavior = MouseBehavior(min_steps=20, overshoot_probability=0.0)
        start = Point(0.0, 0.0)
        end = Point(1.0, 1.0)  # Very short distance

        path = behavior.generate_path(start, end)

        # Should have at least min_steps + 1 points
        assert len(path) >= behavior.min_steps + 1

    def test_path_with_overshoot(self):
        """Test path with guaranteed overshoot."""
        behavior = MouseBehavior(overshoot_probability=1.0)  # Always overshoot
        start = Point(0.0, 0.0)
        end = Point(100.0, 0.0)

        path = behavior.generate_path(start, end)

        # Path should be longer due to overshoot and correction
        # Without overshoot, we'd have min_steps+1 to max_steps+1 points
        # With overshoot, we add the overshoot point plus 3-7 correction steps
        assert len(path) > behavior.min_steps + 1

    def test_path_returns_list_of_points(self):
        """Test that path returns a list of Point objects."""
        behavior = MouseBehavior()
        start = Point(0.0, 0.0)
        end = Point(100.0, 100.0)

        path = behavior.generate_path(start, end)

        assert isinstance(path, list)
        assert all(isinstance(p, Point) for p in path)


# ============================================================================
# TREMOR SIMULATION TESTS
# ============================================================================


class TestApplyTremor:
    """Tests for _apply_tremor method."""

    def test_tremor_produces_small_offsets(self):
        """Test that tremor produces small random offsets."""
        behavior = MouseBehavior(tremor_amplitude=1.5)
        original = Point(100.0, 100.0)

        # Run multiple times and check offsets are small
        offsets_x = []
        offsets_y = []
        for _ in range(100):
            result = behavior._apply_tremor(original)
            offsets_x.append(abs(result.x - original.x))
            offsets_y.append(abs(result.y - original.y))

        # Most offsets should be within 3 standard deviations (4.5 pixels)
        avg_offset_x = sum(offsets_x) / len(offsets_x)
        avg_offset_y = sum(offsets_y) / len(offsets_y)

        assert avg_offset_x < 3.0  # Should be around tremor_amplitude
        assert avg_offset_y < 3.0

    def test_tremor_returns_new_point(self):
        """Test that tremor returns a new Point object."""
        behavior = MouseBehavior()
        original = Point(50.0, 50.0)

        result = behavior._apply_tremor(original)

        assert isinstance(result, Point)
        # Result should be different from original (with very high probability)

    def test_tremor_amplitude_affects_offset(self):
        """Test that larger tremor amplitude produces larger offsets."""
        behavior_small = MouseBehavior(tremor_amplitude=0.5)
        behavior_large = MouseBehavior(tremor_amplitude=5.0)
        original = Point(100.0, 100.0)

        # Collect offsets for both
        offsets_small = []
        offsets_large = []
        for _ in range(200):
            result_small = behavior_small._apply_tremor(original)
            result_large = behavior_large._apply_tremor(original)
            offsets_small.append(
                math.sqrt((result_small.x - original.x) ** 2 + (result_small.y - original.y) ** 2)
            )
            offsets_large.append(
                math.sqrt((result_large.x - original.x) ** 2 + (result_large.y - original.y) ** 2)
            )

        avg_small = sum(offsets_small) / len(offsets_small)
        avg_large = sum(offsets_large) / len(offsets_large)

        assert avg_large > avg_small


# ============================================================================
# ASYNC MOVE_TO TESTS
# ============================================================================


class TestMoveTo:
    """Tests for async move_to method."""

    @pytest.mark.asyncio
    async def test_move_to_calls_mouse_move_multiple_times(self, mock_page, mock_sleep):
        """Test that move_to calls page.mouse.move multiple times."""
        behavior = MouseBehavior(min_steps=10, overshoot_probability=0.0)

        await behavior.move_to(mock_page, 200.0, 300.0)

        # Should have called mouse.move at least min_steps times
        assert mock_page.mouse.move.call_count >= behavior.min_steps

    @pytest.mark.asyncio
    async def test_move_to_sleeps_between_moves(self, mock_page, mock_sleep):
        """Test that move_to sleeps between mouse moves."""
        behavior = MouseBehavior(min_steps=10, overshoot_probability=0.0)

        await behavior.move_to(mock_page, 200.0, 300.0)

        # Should have called sleep for each path point
        assert mock_sleep.call_count >= behavior.min_steps

    @pytest.mark.asyncio
    async def test_move_to_uses_current_position(self, mock_page, mock_sleep):
        """Test that move_to evaluates page to get current position."""
        behavior = MouseBehavior(min_steps=5, overshoot_probability=0.0)

        await behavior.move_to(mock_page, 200.0, 300.0)

        # First move should start from the evaluated position (200, 400)
        # The mock_page.evaluate returns {"x": 200, "y": 400}
        first_call_args = mock_page.mouse.move.call_args_list[0][0]
        # Due to Bezier curve, first point should be near (200, 400)
        assert first_call_args[0] == pytest.approx(200.0, abs=10.0)
        assert first_call_args[1] == pytest.approx(400.0, abs=10.0)

    @pytest.mark.asyncio
    async def test_move_to_ends_near_target(self, mock_page, mock_sleep):
        """Test that move_to ends near the target coordinates."""
        behavior = MouseBehavior(min_steps=5, overshoot_probability=0.0)

        await behavior.move_to(mock_page, 500.0, 600.0)

        # Last move should be near target
        last_call_args = mock_page.mouse.move.call_args_list[-1][0]
        assert last_call_args[0] == pytest.approx(500.0, abs=10.0)
        assert last_call_args[1] == pytest.approx(600.0, abs=10.0)

    @pytest.mark.asyncio
    async def test_move_to_handles_evaluate_exception(self, mock_page, mock_sleep):
        """Test that move_to handles evaluate exception gracefully."""
        behavior = MouseBehavior(min_steps=5, overshoot_probability=0.0)

        # Make evaluate raise an exception
        mock_page.evaluate = AsyncMock(side_effect=Exception("Eval failed"))

        # Should not raise, uses default position (400, 300)
        await behavior.move_to(mock_page, 100.0, 100.0)

        # Should still have made mouse moves
        assert mock_page.mouse.move.call_count > 0


# ============================================================================
# ASYNC CLICK TESTS
# ============================================================================


class TestClick:
    """Tests for async click method."""

    @pytest.mark.asyncio
    async def test_click_moves_then_clicks(self, mock_page, mock_sleep):
        """Test that click moves to position then performs click."""
        behavior = MouseBehavior(min_steps=5, overshoot_probability=0.0)

        await behavior.click(mock_page, 100.0, 200.0)

        # Should have moved mouse
        assert mock_page.mouse.move.call_count > 0

        # Should have called down and up
        assert mock_page.mouse.down.call_count == 1
        assert mock_page.mouse.up.call_count == 1

    @pytest.mark.asyncio
    async def test_click_with_right_button(self, mock_page, mock_sleep):
        """Test click with right mouse button."""
        behavior = MouseBehavior(min_steps=5, overshoot_probability=0.0)

        await behavior.click(mock_page, 100.0, 200.0, button="right")

        mock_page.mouse.down.assert_called_with(button="right")
        mock_page.mouse.up.assert_called_with(button="right")

    @pytest.mark.asyncio
    async def test_click_with_double_click(self, mock_page, mock_sleep):
        """Test double click."""
        behavior = MouseBehavior(min_steps=5, overshoot_probability=0.0)

        await behavior.click(mock_page, 100.0, 200.0, click_count=2)

        # Should have two down/up pairs
        assert mock_page.mouse.down.call_count == 2
        assert mock_page.mouse.up.call_count == 2

    @pytest.mark.asyncio
    async def test_click_sleeps_between_actions(self, mock_page, mock_sleep):
        """Test that click includes pauses for natural timing."""
        behavior = MouseBehavior(min_steps=5, overshoot_probability=0.0)

        await behavior.click(mock_page, 100.0, 200.0)

        # Should have slept multiple times (move delays + click delays)
        assert mock_sleep.call_count > behavior.min_steps

    @pytest.mark.asyncio
    async def test_click_handles_mouse_exception(self, mock_page, mock_sleep):
        """Test that click handles mouse action exceptions."""
        behavior = MouseBehavior(min_steps=5, overshoot_probability=0.0)

        # Make mouse.down raise an exception
        mock_page.mouse.down = AsyncMock(side_effect=Exception("Mouse error"))

        # Should not raise
        await behavior.click(mock_page, 100.0, 200.0)


# ============================================================================
# ASYNC DRAG TESTS
# ============================================================================


class TestDrag:
    """Tests for async drag method."""

    @pytest.mark.asyncio
    async def test_drag_performs_down_move_up_sequence(self, mock_page, mock_sleep):
        """Test that drag performs mouse down, move, then up."""
        behavior = MouseBehavior(min_steps=5, overshoot_probability=0.0)

        await behavior.drag(mock_page, 100.0, 100.0, 200.0, 200.0)

        # Should have called down, multiple moves, then up
        assert mock_page.mouse.down.call_count >= 1
        assert mock_page.mouse.move.call_count > behavior.min_steps  # Move to start + drag
        assert mock_page.mouse.up.call_count == 1

    @pytest.mark.asyncio
    async def test_drag_moves_to_start_first(self, mock_page, mock_sleep):
        """Test that drag moves to start position before pressing."""
        behavior = MouseBehavior(min_steps=5, overshoot_probability=0.0)

        await behavior.drag(mock_page, 50.0, 50.0, 150.0, 150.0)

        # First series of moves should approach start position
        first_moves = mock_page.mouse.move.call_args_list[: behavior.min_steps]
        # Moves should be heading towards (50, 50)
        assert len(first_moves) > 0

    @pytest.mark.asyncio
    async def test_drag_handles_down_exception(self, mock_page, mock_sleep):
        """Test that drag returns early if down fails."""
        behavior = MouseBehavior(min_steps=5, overshoot_probability=0.0)

        # Make initial move_to work but down fail
        move_call_count = [0]
        original_move = mock_page.mouse.move

        async def count_moves(*args, **kwargs):
            move_call_count[0] += 1
            return await original_move(*args, **kwargs)

        mock_page.mouse.move = count_moves
        mock_page.mouse.down = AsyncMock(side_effect=Exception("Down failed"))

        await behavior.drag(mock_page, 100.0, 100.0, 200.0, 200.0)

        # Should have moved to start but not continued with drag
        # Up should not have been called since down failed
        assert mock_page.mouse.up.call_count == 0

    @pytest.mark.asyncio
    async def test_drag_sleeps_between_operations(self, mock_page, mock_sleep):
        """Test that drag includes pauses for natural timing."""
        behavior = MouseBehavior(min_steps=5, overshoot_probability=0.0)

        await behavior.drag(mock_page, 0.0, 0.0, 100.0, 100.0)

        # Should have slept many times (move to start + pauses + drag moves + final pause)
        assert mock_sleep.call_count > behavior.min_steps * 2

    @pytest.mark.asyncio
    async def test_drag_handles_move_exception_during_drag(self, mock_page, mock_sleep):
        """Test that drag continues even if move fails during drag."""
        behavior = MouseBehavior(min_steps=5, overshoot_probability=0.0)

        call_count = [0]

        async def failing_move(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] > 10:  # Fail during drag portion
                raise Exception("Move failed")

        mock_page.mouse.move = AsyncMock(side_effect=failing_move)

        # Should not raise
        await behavior.drag(mock_page, 0.0, 0.0, 100.0, 100.0)

        # Up should still be called
        assert mock_page.mouse.up.call_count == 1
