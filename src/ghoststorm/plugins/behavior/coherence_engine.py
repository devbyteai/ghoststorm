"""Behavioral Coherence Engine.

Ensures consistent, human-like behavior across browser sessions by:
- Maintaining cross-page state and behavior patterns
- Simulating circadian rhythm patterns (time-of-day behavior)
- Session-level consistency (same user persona throughout)
- Attention modeling (focused vs distracted browsing)
- Fatigue simulation over extended sessions

This engine prevents detection by ensuring behaviors don't suddenly change
mid-session and that patterns match realistic human browsing.
"""

from __future__ import annotations

import random
import secrets
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

import structlog

logger = structlog.get_logger(__name__)


class UserPersona(str, Enum):
    """User persona types affecting browsing behavior."""

    CASUAL = "casual"  # Relaxed browsing, longer dwell times
    RESEARCHER = "researcher"  # Thorough reading, many clicks
    SHOPPER = "shopper"  # Product-focused, comparison behavior
    SCANNER = "scanner"  # Quick scanning, short attention
    POWER_USER = "power_user"  # Efficient, keyboard shortcuts
    # Video content personas (TikTok/Instagram)
    SCROLLER = "scroller"  # Fast swipes, very short attention (video platforms)
    CONTENT_CONSUMER = "content_consumer"  # Engaged viewer, longer watches


class AttentionState(str, Enum):
    """Current attention/focus state."""

    FOCUSED = "focused"  # Engaged with content
    DISTRACTED = "distracted"  # Multitasking, irregular patterns
    SKIMMING = "skimming"  # Quick scanning
    READING = "reading"  # Deep content engagement
    IDLE = "idle"  # Inactive but page open


class SessionPhase(str, Enum):
    """Phase of browsing session."""

    START = "start"  # Beginning, exploratory
    ACTIVE = "active"  # Main engagement
    WINDING_DOWN = "winding_down"  # Slowing activity
    END = "end"  # Session conclusion


@dataclass
class CircadianProfile:
    """Time-of-day behavior profile."""

    hour: int  # 0-23

    # Activity level (0-1)
    activity_level: float

    # Speed factor (affects movement, typing)
    speed_factor: float

    # Error rate (typos, misclicks)
    error_rate: float

    # Focus duration (seconds)
    focus_duration: float

    # Break frequency (per hour)
    break_frequency: float


# Circadian rhythm profiles by hour
CIRCADIAN_PROFILES = {
    # Night (0-5): Very low activity
    0: CircadianProfile(0, 0.2, 0.7, 0.08, 120, 0.5),
    1: CircadianProfile(1, 0.1, 0.6, 0.10, 90, 0.3),
    2: CircadianProfile(2, 0.05, 0.5, 0.12, 60, 0.2),
    3: CircadianProfile(3, 0.05, 0.5, 0.12, 60, 0.2),
    4: CircadianProfile(4, 0.1, 0.6, 0.10, 90, 0.3),
    5: CircadianProfile(5, 0.3, 0.7, 0.08, 120, 0.5),
    # Morning (6-11): Increasing activity
    6: CircadianProfile(6, 0.5, 0.8, 0.06, 180, 1.0),
    7: CircadianProfile(7, 0.7, 0.9, 0.05, 240, 1.5),
    8: CircadianProfile(8, 0.8, 1.0, 0.04, 300, 2.0),
    9: CircadianProfile(9, 0.9, 1.0, 0.03, 360, 2.5),
    10: CircadianProfile(10, 1.0, 1.0, 0.03, 400, 2.0),
    11: CircadianProfile(11, 0.95, 1.0, 0.04, 360, 2.5),
    # Afternoon (12-17): Peak then declining
    12: CircadianProfile(12, 0.7, 0.9, 0.05, 300, 3.0),  # Lunch dip
    13: CircadianProfile(13, 0.75, 0.9, 0.05, 280, 2.5),
    14: CircadianProfile(14, 0.9, 1.0, 0.04, 340, 2.0),
    15: CircadianProfile(15, 0.95, 1.0, 0.03, 380, 2.0),
    16: CircadianProfile(16, 0.9, 0.95, 0.04, 340, 2.0),
    17: CircadianProfile(17, 0.8, 0.9, 0.05, 300, 2.5),
    # Evening (18-23): Winding down
    18: CircadianProfile(18, 0.7, 0.85, 0.05, 280, 2.0),
    19: CircadianProfile(19, 0.65, 0.85, 0.06, 260, 1.5),
    20: CircadianProfile(20, 0.6, 0.8, 0.06, 240, 1.5),
    21: CircadianProfile(21, 0.55, 0.75, 0.07, 200, 1.0),
    22: CircadianProfile(22, 0.4, 0.7, 0.08, 160, 0.8),
    23: CircadianProfile(23, 0.3, 0.7, 0.08, 140, 0.6),
}


@dataclass
class SessionState:
    """Current session state for coherence tracking."""

    # Session identity
    session_id: str
    persona: UserPersona
    start_time: float  # Unix timestamp

    # Current state
    attention_state: AttentionState = AttentionState.FOCUSED
    session_phase: SessionPhase = SessionPhase.START

    # Fatigue modeling
    fatigue_level: float = 0.0  # 0-1
    last_break_time: float = 0.0

    # Navigation history
    pages_visited: list[str] = field(default_factory=list)
    total_clicks: int = 0
    total_keystrokes: int = 0

    # Timing
    last_action_time: float = 0.0
    time_on_current_page: float = 0.0

    # Behavior parameters (consistent within session)
    base_typing_speed: float = 0.0  # WPM
    base_mouse_speed: float = 1.0
    error_proneness: float = 0.0  # 0-1
    attention_span: float = 300.0  # seconds


@dataclass
class CoherenceConfig:
    """Configuration for coherence engine."""

    # Enable circadian rhythm simulation
    circadian_enabled: bool = True

    # Enable fatigue simulation
    fatigue_enabled: bool = True

    # Session timeout (no activity) in seconds
    session_timeout: float = 1800  # 30 minutes

    # Fatigue accumulation rate per hour
    fatigue_rate: float = 0.1

    # Maximum session duration before forced break
    max_session_duration: float = 14400  # 4 hours

    # Attention state change probability per action
    attention_change_probability: float = 0.05


class CoherenceEngine:
    """Behavioral coherence engine for session consistency.

    Maintains realistic, consistent behavior patterns across a browsing session
    to avoid detection by behavior analysis systems.

    Usage:
        engine = CoherenceEngine()
        state = engine.create_session(persona=UserPersona.CASUAL)

        # Get behavior modifiers before each action
        modifiers = engine.get_behavior_modifiers(state)

        # Apply modifiers to mouse speed, typing speed, etc.
        actual_speed = base_speed * modifiers.speed_factor

        # Update state after action
        engine.record_action(state, "click")
    """

    def __init__(self, config: CoherenceConfig | None = None) -> None:
        """Initialize coherence engine.

        Args:
            config: Engine configuration
        """
        self.config = config or CoherenceConfig()
        self._sessions: dict[str, SessionState] = {}

    def create_session(
        self,
        persona: UserPersona | None = None,
        session_id: str | None = None,
    ) -> SessionState:
        """Create a new coherent session.

        Args:
            persona: User persona (random if None)
            session_id: Custom session ID (generated if None)

        Returns:
            New SessionState
        """
        if persona is None:
            persona = random.choice(list(UserPersona))

        if session_id is None:
            # Use cryptographically secure random for session IDs
            session_id = secrets.token_hex(6)  # 12 hex chars, 48 bits entropy

        # Generate consistent base parameters for persona
        persona_params = self._get_persona_parameters(persona)

        state = SessionState(
            session_id=session_id,
            persona=persona,
            start_time=time.time(),
            base_typing_speed=persona_params["typing_speed"],
            base_mouse_speed=persona_params["mouse_speed"],
            error_proneness=persona_params["error_proneness"],
            attention_span=persona_params["attention_span"],
        )

        self._sessions[session_id] = state
        logger.info(
            "Created coherent session",
            session_id=session_id,
            persona=persona.value,
        )

        return state

    def _get_persona_parameters(self, persona: UserPersona) -> dict[str, float]:
        """Get base parameters for a persona."""
        params = {
            UserPersona.CASUAL: {
                "typing_speed": random.gauss(40, 10),  # WPM
                "mouse_speed": random.gauss(0.8, 0.1),
                "error_proneness": random.gauss(0.05, 0.02),
                "attention_span": random.gauss(180, 60),
            },
            UserPersona.RESEARCHER: {
                "typing_speed": random.gauss(55, 12),
                "mouse_speed": random.gauss(1.0, 0.15),
                "error_proneness": random.gauss(0.03, 0.01),
                "attention_span": random.gauss(600, 120),
            },
            UserPersona.SHOPPER: {
                "typing_speed": random.gauss(45, 10),
                "mouse_speed": random.gauss(1.1, 0.15),
                "error_proneness": random.gauss(0.04, 0.02),
                "attention_span": random.gauss(120, 40),
            },
            UserPersona.SCANNER: {
                "typing_speed": random.gauss(35, 8),
                "mouse_speed": random.gauss(1.3, 0.2),
                "error_proneness": random.gauss(0.06, 0.02),
                "attention_span": random.gauss(60, 20),
            },
            UserPersona.POWER_USER: {
                "typing_speed": random.gauss(75, 15),
                "mouse_speed": random.gauss(1.2, 0.15),
                "error_proneness": random.gauss(0.02, 0.01),
                "attention_span": random.gauss(300, 90),
            },
            # Video content personas (TikTok/Instagram)
            UserPersona.SCROLLER: {
                "typing_speed": random.gauss(50, 10),  # Rarely types
                "mouse_speed": random.gauss(1.4, 0.2),  # Fast swipes
                "error_proneness": random.gauss(0.07, 0.02),  # Some misclicks
                "attention_span": random.gauss(30, 15),  # Very short
            },
            UserPersona.CONTENT_CONSUMER: {
                "typing_speed": random.gauss(45, 10),
                "mouse_speed": random.gauss(0.9, 0.1),  # Slower, engaged
                "error_proneness": random.gauss(0.04, 0.02),
                "attention_span": random.gauss(180, 60),  # Longer watches
            },
        }

        return params.get(persona, params[UserPersona.CASUAL])

    def get_circadian_profile(self) -> CircadianProfile:
        """Get current circadian profile based on time of day."""
        current_hour = datetime.now(UTC).hour
        return CIRCADIAN_PROFILES.get(current_hour, CIRCADIAN_PROFILES[12])

    def get_behavior_modifiers(self, state: SessionState) -> dict[str, float]:
        """Calculate behavior modifiers for current session state.

        Args:
            state: Current session state

        Returns:
            Dict with modifier values for various behaviors
        """
        modifiers = {
            "speed_factor": 1.0,
            "dwell_time_factor": 1.0,
            "error_rate": state.error_proneness,
            "focus_probability": 0.8,
            "break_probability": 0.0,
            "typo_probability": 0.02,
            "misclick_probability": 0.01,
        }

        # Apply circadian modifiers
        if self.config.circadian_enabled:
            circadian = self.get_circadian_profile()
            modifiers["speed_factor"] *= circadian.speed_factor
            modifiers["error_rate"] += circadian.error_rate
            modifiers["focus_probability"] *= circadian.activity_level

        # Apply fatigue modifiers
        if self.config.fatigue_enabled:
            fatigue_modifier = 1.0 - (state.fatigue_level * 0.3)
            modifiers["speed_factor"] *= fatigue_modifier
            modifiers["dwell_time_factor"] *= 1.0 + (state.fatigue_level * 0.5)
            modifiers["error_rate"] += state.fatigue_level * 0.05
            modifiers["typo_probability"] += state.fatigue_level * 0.03
            modifiers["misclick_probability"] += state.fatigue_level * 0.02

        # Apply attention state modifiers
        attention_modifiers = {
            AttentionState.FOCUSED: {
                "speed_factor": 1.0,
                "error_rate": 0.0,
            },
            AttentionState.DISTRACTED: {
                "speed_factor": 0.7,
                "error_rate": 0.03,
                "dwell_time_factor": 1.5,
            },
            AttentionState.SKIMMING: {
                "speed_factor": 1.3,
                "dwell_time_factor": 0.5,
            },
            AttentionState.READING: {
                "speed_factor": 0.8,
                "dwell_time_factor": 2.0,
            },
            AttentionState.IDLE: {
                "speed_factor": 0.3,
                "dwell_time_factor": 3.0,
            },
        }

        if state.attention_state in attention_modifiers:
            for key, value in attention_modifiers[state.attention_state].items():
                if key in modifiers:
                    if key.endswith("_factor"):
                        modifiers[key] *= value
                    else:
                        modifiers[key] += value

        # Apply session phase modifiers
        if state.session_phase == SessionPhase.START:
            modifiers["speed_factor"] *= 0.9  # Slightly slower at start
        elif state.session_phase == SessionPhase.WINDING_DOWN:
            modifiers["speed_factor"] *= 0.85
            modifiers["dwell_time_factor"] *= 1.3
        elif state.session_phase == SessionPhase.END:
            modifiers["break_probability"] = 0.3

        # Apply persona modifiers
        modifiers["speed_factor"] *= state.base_mouse_speed

        # Clamp values
        modifiers["speed_factor"] = max(0.3, min(2.0, modifiers["speed_factor"]))
        modifiers["dwell_time_factor"] = max(0.2, min(5.0, modifiers["dwell_time_factor"]))
        modifiers["error_rate"] = max(0.0, min(0.2, modifiers["error_rate"]))

        return modifiers

    def record_action(
        self,
        state: SessionState,
        action_type: str,
        url: str | None = None,
    ) -> None:
        """Record an action and update session state.

        Args:
            state: Session state to update
            action_type: Type of action (click, keypress, scroll, navigate)
            url: Current URL (for navigation tracking)
        """
        current_time = time.time()

        # Update action counts
        if action_type == "click":
            state.total_clicks += 1
        elif action_type == "keypress":
            state.total_keystrokes += 1

        # Update navigation
        if url and url not in state.pages_visited:
            state.pages_visited.append(url)
            state.time_on_current_page = 0.0
        else:
            state.time_on_current_page += current_time - state.last_action_time

        state.last_action_time = current_time

        # Update fatigue
        if self.config.fatigue_enabled:
            session_duration = current_time - state.start_time
            state.fatigue_level = min(
                1.0,
                (session_duration / 3600) * self.config.fatigue_rate,
            )

        # Maybe update attention state
        if random.random() < self.config.attention_change_probability:
            state.attention_state = self._transition_attention_state(
                state.attention_state
            )

        # Update session phase
        state.session_phase = self._determine_session_phase(state)

    def _transition_attention_state(
        self,
        current: AttentionState,
    ) -> AttentionState:
        """Determine next attention state with realistic transitions."""
        # Transition probabilities from each state
        transitions = {
            AttentionState.FOCUSED: {
                AttentionState.FOCUSED: 0.7,
                AttentionState.READING: 0.15,
                AttentionState.DISTRACTED: 0.1,
                AttentionState.SKIMMING: 0.05,
            },
            AttentionState.DISTRACTED: {
                AttentionState.DISTRACTED: 0.5,
                AttentionState.FOCUSED: 0.3,
                AttentionState.IDLE: 0.1,
                AttentionState.SKIMMING: 0.1,
            },
            AttentionState.SKIMMING: {
                AttentionState.SKIMMING: 0.4,
                AttentionState.FOCUSED: 0.3,
                AttentionState.READING: 0.2,
                AttentionState.DISTRACTED: 0.1,
            },
            AttentionState.READING: {
                AttentionState.READING: 0.6,
                AttentionState.FOCUSED: 0.2,
                AttentionState.SKIMMING: 0.15,
                AttentionState.DISTRACTED: 0.05,
            },
            AttentionState.IDLE: {
                AttentionState.IDLE: 0.3,
                AttentionState.FOCUSED: 0.4,
                AttentionState.DISTRACTED: 0.2,
                AttentionState.SKIMMING: 0.1,
            },
        }

        probs = transitions.get(
            current,
            {AttentionState.FOCUSED: 1.0},
        )

        # Weighted random selection
        rand = random.random()
        cumulative = 0.0
        for state, prob in probs.items():
            cumulative += prob
            if rand < cumulative:
                return state

        return AttentionState.FOCUSED

    def _determine_session_phase(self, state: SessionState) -> SessionPhase:
        """Determine current session phase."""
        session_duration = time.time() - state.start_time

        # Start phase: first 5 minutes
        if session_duration < 300:
            return SessionPhase.START

        # End phase: approaching timeout or max duration
        if (
            session_duration > self.config.max_session_duration * 0.9
            or state.fatigue_level > 0.8
        ):
            return SessionPhase.END

        # Winding down: high fatigue or long session
        if state.fatigue_level > 0.6 or session_duration > self.config.max_session_duration * 0.7:
            return SessionPhase.WINDING_DOWN

        return SessionPhase.ACTIVE

    def should_take_break(self, state: SessionState) -> bool:
        """Determine if user should take a break.

        Args:
            state: Session state

        Returns:
            True if break is recommended
        """
        current_time = time.time()
        time_since_break = current_time - state.last_break_time

        # Circadian break frequency
        circadian = self.get_circadian_profile()
        avg_break_interval = 3600 / max(0.1, circadian.break_frequency)

        # Fatigue increases break probability
        break_threshold = avg_break_interval * (1 - state.fatigue_level * 0.5)

        return time_since_break > break_threshold

    def record_break(self, state: SessionState, duration: float) -> None:
        """Record that user took a break.

        Args:
            state: Session state
            duration: Break duration in seconds
        """
        state.last_break_time = time.time()

        # Breaks reduce fatigue
        fatigue_reduction = min(0.3, duration / 600)  # Up to 0.3 for 10min break
        state.fatigue_level = max(0.0, state.fatigue_level - fatigue_reduction)

        # Reset attention to focused
        state.attention_state = AttentionState.FOCUSED

    def get_session(self, session_id: str) -> SessionState | None:
        """Get session by ID."""
        return self._sessions.get(session_id)

    def end_session(self, session_id: str) -> None:
        """End and remove a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info("Session ended", session_id=session_id)


# Global engine instance
_engine: CoherenceEngine | None = None


def get_coherence_engine(config: CoherenceConfig | None = None) -> CoherenceEngine:
    """Get or create the global coherence engine.

    Args:
        config: Optional configuration (only used if creating new)

    Returns:
        CoherenceEngine instance
    """
    global _engine
    if _engine is None:
        _engine = CoherenceEngine(config)
    return _engine
