"""ML-based mouse movement generation.

Generates human-like mouse trajectories using mathematical models based on
BeCAPTCHA-Mouse research and optionally ONNX neural network models.

Key Features:
- GAN-style trajectory synthesis (when model available)
- Velocity-aware acceleration curves
- Micro-tremor patterns from real human data
- Distance-aware trajectory complexity
- Sigma-lognormal kinematic theory implementation

Research References:
- BeCAPTCHA-Mouse: Synthetic mouse trajectories for CAPTCHA evasion
- Sigma-Lognormal model for human movement
- Fitts' Law for movement time prediction
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from pathlib import Path

logger = structlog.get_logger(__name__)


class MovementStyle(str, Enum):
    """Mouse movement style presets."""

    NATURAL = "natural"  # Default human-like
    FAST = "fast"  # Quick, direct movements
    SLOW = "slow"  # Careful, deliberate movements
    NERVOUS = "nervous"  # Jittery, uncertain
    CONFIDENT = "confident"  # Smooth, precise


@dataclass
class Point:
    """2D point with optional timestamp."""

    x: float
    y: float
    t: float = 0.0  # Timestamp in ms

    def distance_to(self, other: Point) -> float:
        """Calculate Euclidean distance to another point."""
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)


@dataclass
class Trajectory:
    """Mouse movement trajectory."""

    points: list[Point] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.points)

    def __iter__(self):
        return iter(self.points)

    @property
    def duration(self) -> float:
        """Total trajectory duration in ms."""
        if len(self.points) < 2:
            return 0.0
        return self.points[-1].t - self.points[0].t

    @property
    def total_distance(self) -> float:
        """Total path distance in pixels."""
        if len(self.points) < 2:
            return 0.0
        return sum(
            self.points[i].distance_to(self.points[i + 1]) for i in range(len(self.points) - 1)
        )


@dataclass
class MLMouseConfig:
    """Configuration for ML mouse movement generator."""

    # Movement style preset
    style: MovementStyle = MovementStyle.NATURAL

    # Base speed factor (1.0 = normal)
    speed_factor: float = 1.0

    # Add micro-tremors (hand shake)
    tremor_enabled: bool = True
    tremor_amplitude: float = 0.5  # pixels

    # Add acceleration/deceleration curves
    kinematic_enabled: bool = True

    # Randomize movement parameters
    randomize: bool = True

    # Minimum points per trajectory
    min_points: int = 20

    # ONNX model path (optional)
    model_path: Path | None = None

    # Overshoot probability (miss target and correct)
    overshoot_probability: float = 0.15

    # Pause probability at intermediate points
    pause_probability: float = 0.1


class SigmaLognormalModel:
    """Sigma-Lognormal model for human motor control.

    Based on the kinematic theory of rapid human movements.
    Each stroke is modeled as a lognormal velocity profile.
    """

    def __init__(
        self,
        t0: float = 0.0,  # Start time
        d: float = 1.0,  # Amplitude
        mu: float = 0.5,  # Log-time delay
        sigma: float = 0.4,  # Log-response time
    ) -> None:
        self.t0 = t0
        self.d = d
        self.mu = mu
        self.sigma = sigma

    def velocity(self, t: float) -> float:
        """Calculate velocity at time t."""
        if t <= self.t0:
            return 0.0

        dt = t - self.t0
        if dt <= 0:
            return 0.0

        # Lognormal velocity profile
        exponent = -((math.log(dt) - self.mu) ** 2) / (2 * self.sigma**2)
        return (self.d / (dt * self.sigma * math.sqrt(2 * math.pi))) * math.exp(exponent)

    def displacement(self, t: float, num_steps: int = 100) -> float:
        """Integrate velocity to get displacement."""
        if t <= self.t0:
            return 0.0

        dt = (t - self.t0) / num_steps
        displacement = 0.0
        for i in range(num_steps):
            displacement += self.velocity(self.t0 + i * dt) * dt

        return displacement


class BezierCurve:
    """Bezier curve for smooth trajectory generation."""

    def __init__(self, points: list[Point]) -> None:
        """Initialize with control points."""
        self.points = points

    def evaluate(self, t: float) -> Point:
        """Evaluate curve at parameter t (0 to 1)."""
        n = len(self.points) - 1
        x = 0.0
        y = 0.0

        for i, p in enumerate(self.points):
            # Bernstein polynomial
            coeff = self._binomial(n, i) * (t**i) * ((1 - t) ** (n - i))
            x += coeff * p.x
            y += coeff * p.y

        return Point(x=x, y=y)

    @staticmethod
    def _binomial(n: int, k: int) -> int:
        """Calculate binomial coefficient."""
        if k < 0 or k > n:
            return 0
        if k == 0 or k == n:
            return 1

        result = 1
        for i in range(min(k, n - k)):
            result = result * (n - i) // (i + 1)
        return result


class MLMouseGenerator:
    """ML-based mouse movement generator.

    Generates human-like mouse trajectories using:
    1. Sigma-Lognormal kinematic model for velocity profiles
    2. Bezier curves for smooth path generation
    3. Micro-tremor injection for realism
    4. Optional ONNX model for GAN-style generation

    Usage:
        generator = MLMouseGenerator(MLMouseConfig())
        trajectory = generator.generate(start=(0, 0), end=(500, 300))

        for point in trajectory:
            await page.mouse.move(point.x, point.y)
            await asyncio.sleep(point.t / 1000)  # Convert ms to seconds
    """

    def __init__(self, config: MLMouseConfig | None = None) -> None:
        """Initialize generator.

        Args:
            config: Generator configuration
        """
        self.config = config or MLMouseConfig()
        self._model: Any = None
        self._model_loaded = False

        # Try to load ONNX model if specified
        if self.config.model_path and self.config.model_path.exists():
            self._load_model()

    def _load_model(self) -> None:
        """Load ONNX model for trajectory generation."""
        try:
            import onnxruntime as ort

            self._model = ort.InferenceSession(str(self.config.model_path))
            self._model_loaded = True
            logger.info("ML mouse model loaded", path=str(self.config.model_path))
        except ImportError:
            logger.warning("onnxruntime not installed, using mathematical model")
        except Exception as e:
            logger.warning("Failed to load mouse model", error=str(e))

    def generate(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        duration: float | None = None,
    ) -> Trajectory:
        """Generate a human-like mouse trajectory.

        Args:
            start: Starting position (x, y)
            end: Target position (x, y)
            duration: Optional duration in ms (auto-calculated if None)

        Returns:
            Trajectory with timestamped points
        """
        start_point = Point(x=start[0], y=start[1], t=0.0)
        end_point = Point(x=end[0], y=end[1])

        distance = start_point.distance_to(end_point)

        # Calculate duration using Fitts' Law if not specified
        if duration is None:
            duration = self._calculate_duration(distance)

        duration *= self.config.speed_factor

        # Use ONNX model if available
        if self._model_loaded:
            return self._generate_with_model(start_point, end_point, duration)

        # Use mathematical model
        return self._generate_mathematical(start_point, end_point, duration, distance)

    def _calculate_duration(self, distance: float) -> float:
        """Calculate movement duration using Fitts' Law.

        T = a + b * log2(D/W + 1)

        Args:
            distance: Movement distance in pixels

        Returns:
            Duration in milliseconds
        """
        # Fitts' Law constants (calibrated for typical mouse movement)
        a = 50  # Base time (ms)
        b = 150  # Movement time coefficient
        w = 10  # Target width (approximate)

        if distance < 1:
            return a

        # Add style-based variation
        style_multipliers = {
            MovementStyle.NATURAL: 1.0,
            MovementStyle.FAST: 0.6,
            MovementStyle.SLOW: 1.5,
            MovementStyle.NERVOUS: 1.2,
            MovementStyle.CONFIDENT: 0.85,
        }
        multiplier = style_multipliers.get(self.config.style, 1.0)

        duration = a + b * math.log2(distance / w + 1)

        if self.config.randomize:
            duration *= random.uniform(0.8, 1.2)

        return duration * multiplier

    def _generate_mathematical(
        self,
        start: Point,
        end: Point,
        duration: float,
        distance: float,
    ) -> Trajectory:
        """Generate trajectory using mathematical models."""
        trajectory = Trajectory()

        # Generate control points for Bezier curve
        control_points = self._generate_control_points(start, end, distance)
        curve = BezierCurve(control_points)

        # Create Sigma-Lognormal velocity model
        slm = SigmaLognormalModel(
            t0=0.0,
            d=distance,
            mu=random.uniform(0.3, 0.6) if self.config.randomize else 0.5,
            sigma=random.uniform(0.3, 0.5) if self.config.randomize else 0.4,
        )

        # Generate points along curve with kinematic timing
        num_points = max(self.config.min_points, int(distance / 5))
        current_time = 0.0

        for i in range(num_points):
            # Parameter along curve (0 to 1)
            if self.config.kinematic_enabled:
                # Use kinematic model for non-linear progression
                t_param = self._kinematic_progress(i / (num_points - 1))
            else:
                t_param = i / (num_points - 1)

            # Get position on Bezier curve
            point = curve.evaluate(t_param)

            # Calculate timestamp
            point.t = current_time

            # Add micro-tremor
            if self.config.tremor_enabled:
                point = self._add_tremor(point)

            trajectory.points.append(point)

            # Calculate time to next point
            if i < num_points - 1:
                (i + 1) / (num_points - 1)
                velocity = slm.velocity(t_param * duration / 1000)
                if velocity > 0:
                    dt = (duration / num_points) * (1 + 0.5 / velocity)
                else:
                    dt = duration / num_points
                current_time += dt

        # Maybe add overshoot and correction
        if random.random() < self.config.overshoot_probability:
            trajectory = self._add_overshoot(trajectory, end)

        return trajectory

    def _generate_control_points(
        self,
        start: Point,
        end: Point,
        distance: float,
    ) -> list[Point]:
        """Generate Bezier control points for curved path."""
        # Direct vector
        dx = end.x - start.x
        dy = end.y - start.y

        # Perpendicular vector
        perp_x = -dy
        perp_y = dx

        # Normalize perpendicular
        perp_len = math.sqrt(perp_x**2 + perp_y**2)
        if perp_len > 0:
            perp_x /= perp_len
            perp_y /= perp_len

        # Random curvature based on style
        curvature_ranges = {
            MovementStyle.NATURAL: (0.1, 0.3),
            MovementStyle.FAST: (0.0, 0.1),
            MovementStyle.SLOW: (0.2, 0.4),
            MovementStyle.NERVOUS: (0.2, 0.5),
            MovementStyle.CONFIDENT: (0.05, 0.15),
        }
        min_c, max_c = curvature_ranges.get(self.config.style, (0.1, 0.3))
        curvature = random.uniform(min_c, max_c) if self.config.randomize else (min_c + max_c) / 2

        # Random direction of curve
        curve_direction = random.choice([-1, 1]) if self.config.randomize else 1

        # Control point offset
        offset = distance * curvature * curve_direction

        # Generate control points (cubic Bezier)
        cp1 = Point(
            x=start.x + dx * 0.25 + perp_x * offset * 0.5,
            y=start.y + dy * 0.25 + perp_y * offset * 0.5,
        )
        cp2 = Point(
            x=start.x + dx * 0.75 + perp_x * offset,
            y=start.y + dy * 0.75 + perp_y * offset,
        )

        return [start, cp1, cp2, end]

    def _kinematic_progress(self, t: float) -> float:
        """Apply kinematic easing (slow start, slow end).

        Uses smooth S-curve for natural acceleration/deceleration.
        """
        # Smoothstep with slight asymmetry (faster acceleration, slower deceleration)
        t2 = t * t
        t3 = t2 * t

        # Modified smootherstep: starts slightly faster, ends slower
        return t3 * (t * (t * 6.5 - 15) + 10.5) - 0.5 * t3 + 0.5 * t2

    def _add_tremor(self, point: Point) -> Point:
        """Add micro-tremor (hand shake) to point."""
        # Use Perlin-like noise for natural tremor
        freq = 0.1  # Frequency of tremor
        amp = self.config.tremor_amplitude

        # Simple noise approximation
        noise_x = math.sin(point.t * freq) * random.uniform(-amp, amp)
        noise_y = math.cos(point.t * freq * 1.3) * random.uniform(-amp, amp)

        return Point(
            x=point.x + noise_x,
            y=point.y + noise_y,
            t=point.t,
        )

    def _add_overshoot(self, trajectory: Trajectory, target: Point) -> Trajectory:
        """Add overshoot and correction movement."""
        if len(trajectory.points) < 2:
            return trajectory

        last_point = trajectory.points[-1]

        # Calculate overshoot direction and distance
        dx = last_point.x - trajectory.points[-2].x
        dy = last_point.y - trajectory.points[-2].y

        overshoot_dist = random.uniform(5, 20)
        magnitude = math.sqrt(dx**2 + dy**2)
        if magnitude > 0:
            overshoot_x = last_point.x + (dx / magnitude) * overshoot_dist
            overshoot_y = last_point.y + (dy / magnitude) * overshoot_dist
        else:
            overshoot_x = last_point.x + random.uniform(-10, 10)
            overshoot_y = last_point.y + random.uniform(-10, 10)

        # Add overshoot point
        overshoot_point = Point(
            x=overshoot_x,
            y=overshoot_y,
            t=last_point.t + random.uniform(30, 80),
        )
        trajectory.points.append(overshoot_point)

        # Add correction back to target
        correction_duration = random.uniform(50, 150)
        num_correction_points = random.randint(3, 6)

        for i in range(1, num_correction_points + 1):
            t_param = i / num_correction_points
            corrected_point = Point(
                x=overshoot_x + (target.x - overshoot_x) * t_param,
                y=overshoot_y + (target.y - overshoot_y) * t_param,
                t=overshoot_point.t + correction_duration * t_param,
            )
            trajectory.points.append(corrected_point)

        return trajectory

    def _generate_with_model(
        self,
        start: Point,
        end: Point,
        duration: float,
    ) -> Trajectory:
        """Generate trajectory using ONNX model."""
        # Prepare input for model
        # Model expects: [start_x, start_y, end_x, end_y, duration]
        import numpy as np

        input_data = np.array(
            [[start.x, start.y, end.x, end.y, duration]],
            dtype=np.float32,
        )

        # Run inference
        outputs = self._model.run(None, {"input": input_data})

        # Parse output (expected: Nx3 array of [x, y, t])
        points_data = outputs[0][0]

        trajectory = Trajectory()
        for point_data in points_data:
            point = Point(
                x=float(point_data[0]),
                y=float(point_data[1]),
                t=float(point_data[2]),
            )
            trajectory.points.append(point)

        return trajectory


class MLMousePlugin:
    """Plugin wrapper for ML mouse generator."""

    name = "ml_mouse"

    def __init__(self, config: MLMouseConfig | None = None) -> None:
        self.generator = MLMouseGenerator(config)

    async def move_to(
        self,
        page: Any,
        x: float,
        y: float,
        from_pos: tuple[float, float] | None = None,
    ) -> None:
        """Move mouse to position with human-like trajectory.

        Args:
            page: Browser page object
            x: Target X coordinate
            y: Target Y coordinate
            from_pos: Starting position (uses current if None)
        """
        import asyncio

        # Get current position if not specified
        if from_pos is None:
            # Try to get current mouse position from page
            try:
                pos = await page.evaluate(
                    "() => ({ x: window.mouseX || 0, y: window.mouseY || 0 })"
                )
                from_pos = (pos["x"], pos["y"])
            except Exception:
                from_pos = (0, 0)

        # Generate trajectory
        trajectory = self.generator.generate(
            start=from_pos,
            end=(x, y),
        )

        # Execute movement
        prev_time = 0.0
        for point in trajectory:
            # Wait for appropriate time
            delay = (point.t - prev_time) / 1000.0  # Convert to seconds
            if delay > 0:
                await asyncio.sleep(delay)

            # Move mouse
            await page.mouse.move(point.x, point.y)
            prev_time = point.t

    async def click_at(
        self,
        page: Any,
        x: float,
        y: float,
        from_pos: tuple[float, float] | None = None,
        button: str = "left",
        click_count: int = 1,
    ) -> None:
        """Move to position and click with human-like behavior.

        Args:
            page: Browser page object
            x: Target X coordinate
            y: Target Y coordinate
            from_pos: Starting position
            button: Mouse button (left, right, middle)
            click_count: Number of clicks
        """
        import asyncio

        # Move to target
        await self.move_to(page, x, y, from_pos)

        # Small delay before click (reaction time)
        await asyncio.sleep(random.uniform(0.05, 0.15))

        # Click
        await page.mouse.click(x, y, button=button, click_count=click_count)


def get_ml_mouse_generator(
    style: MovementStyle | str = MovementStyle.NATURAL,
    **kwargs: Any,
) -> MLMouseGenerator:
    """Factory function to create ML mouse generator.

    Args:
        style: Movement style preset
        **kwargs: Additional config options

    Returns:
        Configured MLMouseGenerator instance
    """
    if isinstance(style, str):
        style = MovementStyle(style.lower())

    config = MLMouseConfig(style=style, **kwargs)
    return MLMouseGenerator(config)
