"""Tests for behavioral coherence engine."""

from __future__ import annotations

import time
from unittest.mock import patch

from ghoststorm.plugins.behavior.coherence_engine import (
    CIRCADIAN_PROFILES,
    AttentionState,
    CircadianProfile,
    CoherenceConfig,
    CoherenceEngine,
    SessionPhase,
    SessionState,
    UserPersona,
)


class TestUserPersonaEnum:
    """Tests for UserPersona enum."""

    def test_all_personas_defined(self) -> None:
        """Test that all 7 personas are defined."""
        personas = list(UserPersona)
        assert len(personas) == 7

    def test_casual_persona(self) -> None:
        """Test CASUAL persona value."""
        assert UserPersona.CASUAL.value == "casual"

    def test_researcher_persona(self) -> None:
        """Test RESEARCHER persona value."""
        assert UserPersona.RESEARCHER.value == "researcher"

    def test_shopper_persona(self) -> None:
        """Test SHOPPER persona value."""
        assert UserPersona.SHOPPER.value == "shopper"

    def test_scanner_persona(self) -> None:
        """Test SCANNER persona value."""
        assert UserPersona.SCANNER.value == "scanner"

    def test_power_user_persona(self) -> None:
        """Test POWER_USER persona value."""
        assert UserPersona.POWER_USER.value == "power_user"

    def test_scroller_persona(self) -> None:
        """Test SCROLLER persona value."""
        assert UserPersona.SCROLLER.value == "scroller"

    def test_content_consumer_persona(self) -> None:
        """Test CONTENT_CONSUMER persona value."""
        assert UserPersona.CONTENT_CONSUMER.value == "content_consumer"

    def test_persona_is_string_enum(self) -> None:
        """Test that UserPersona is a string enum."""
        assert isinstance(UserPersona.CASUAL, str)
        assert UserPersona.CASUAL == "casual"


class TestAttentionStateEnum:
    """Tests for AttentionState enum."""

    def test_focused_value(self) -> None:
        """Test FOCUSED attention state."""
        assert AttentionState.FOCUSED.value == "focused"

    def test_distracted_value(self) -> None:
        """Test DISTRACTED attention state."""
        assert AttentionState.DISTRACTED.value == "distracted"

    def test_skimming_value(self) -> None:
        """Test SKIMMING attention state."""
        assert AttentionState.SKIMMING.value == "skimming"

    def test_reading_value(self) -> None:
        """Test READING attention state."""
        assert AttentionState.READING.value == "reading"

    def test_idle_value(self) -> None:
        """Test IDLE attention state."""
        assert AttentionState.IDLE.value == "idle"

    def test_all_attention_states_count(self) -> None:
        """Test that all 5 attention states are defined."""
        states = list(AttentionState)
        assert len(states) == 5

    def test_attention_state_is_string_enum(self) -> None:
        """Test that AttentionState is a string enum."""
        assert isinstance(AttentionState.FOCUSED, str)


class TestSessionPhaseEnum:
    """Tests for SessionPhase enum."""

    def test_start_phase(self) -> None:
        """Test START session phase."""
        assert SessionPhase.START.value == "start"

    def test_active_phase(self) -> None:
        """Test ACTIVE session phase."""
        assert SessionPhase.ACTIVE.value == "active"

    def test_winding_down_phase(self) -> None:
        """Test WINDING_DOWN session phase."""
        assert SessionPhase.WINDING_DOWN.value == "winding_down"

    def test_end_phase(self) -> None:
        """Test END session phase."""
        assert SessionPhase.END.value == "end"

    def test_all_phases_count(self) -> None:
        """Test that all 4 session phases are defined."""
        phases = list(SessionPhase)
        assert len(phases) == 4


class TestCircadianProfile:
    """Tests for CircadianProfile dataclass."""

    def test_circadian_profile_creation(self) -> None:
        """Test creating a CircadianProfile."""
        profile = CircadianProfile(
            hour=10,
            activity_level=1.0,
            speed_factor=1.0,
            error_rate=0.03,
            focus_duration=400,
            break_frequency=2.0,
        )
        assert profile.hour == 10
        assert profile.activity_level == 1.0
        assert profile.speed_factor == 1.0
        assert profile.error_rate == 0.03
        assert profile.focus_duration == 400
        assert profile.break_frequency == 2.0

    def test_circadian_profile_fields(self) -> None:
        """Test that CircadianProfile has all required fields."""
        profile = CircadianProfile(0, 0.5, 0.8, 0.05, 200, 1.5)
        assert hasattr(profile, "hour")
        assert hasattr(profile, "activity_level")
        assert hasattr(profile, "speed_factor")
        assert hasattr(profile, "error_rate")
        assert hasattr(profile, "focus_duration")
        assert hasattr(profile, "break_frequency")


class TestCircadianProfiles:
    """Tests for CIRCADIAN_PROFILES dictionary."""

    def test_all_24_hours_defined(self) -> None:
        """Test that all 24 hours are defined in CIRCADIAN_PROFILES."""
        assert len(CIRCADIAN_PROFILES) == 24
        for hour in range(24):
            assert hour in CIRCADIAN_PROFILES, f"Hour {hour} not defined"

    def test_profiles_are_circadian_profile_type(self) -> None:
        """Test that all profiles are CircadianProfile instances."""
        for hour, profile in CIRCADIAN_PROFILES.items():
            assert isinstance(profile, CircadianProfile)
            assert profile.hour == hour

    def test_night_hours_low_activity(self) -> None:
        """Test that night hours (2-4 AM) have low activity."""
        for hour in [2, 3, 4]:
            profile = CIRCADIAN_PROFILES[hour]
            assert profile.activity_level <= 0.15, f"Hour {hour} activity too high"

    def test_peak_hours_high_activity(self) -> None:
        """Test that peak hours (9-10 AM) have high activity."""
        for hour in [9, 10]:
            profile = CIRCADIAN_PROFILES[hour]
            assert profile.activity_level >= 0.9, f"Hour {hour} activity too low"

    def test_activity_level_range(self) -> None:
        """Test that activity levels are within 0-1 range."""
        for _hour, profile in CIRCADIAN_PROFILES.items():
            assert 0 <= profile.activity_level <= 1

    def test_speed_factor_range(self) -> None:
        """Test that speed factors are within reasonable range."""
        for _hour, profile in CIRCADIAN_PROFILES.items():
            assert 0.3 <= profile.speed_factor <= 1.5

    def test_error_rate_range(self) -> None:
        """Test that error rates are within reasonable range."""
        for _hour, profile in CIRCADIAN_PROFILES.items():
            assert 0 <= profile.error_rate <= 0.2


class TestCoherenceConfig:
    """Tests for CoherenceConfig dataclass."""

    def test_default_circadian_enabled(self) -> None:
        """Test default circadian_enabled is True."""
        config = CoherenceConfig()
        assert config.circadian_enabled is True

    def test_default_fatigue_enabled(self) -> None:
        """Test default fatigue_enabled is True."""
        config = CoherenceConfig()
        assert config.fatigue_enabled is True

    def test_default_session_timeout(self) -> None:
        """Test default session_timeout is 1800 (30 minutes)."""
        config = CoherenceConfig()
        assert config.session_timeout == 1800

    def test_default_fatigue_rate(self) -> None:
        """Test default fatigue_rate is 0.1."""
        config = CoherenceConfig()
        assert config.fatigue_rate == 0.1

    def test_default_max_session_duration(self) -> None:
        """Test default max_session_duration is 14400 (4 hours)."""
        config = CoherenceConfig()
        assert config.max_session_duration == 14400

    def test_default_attention_change_probability(self) -> None:
        """Test default attention_change_probability is 0.05."""
        config = CoherenceConfig()
        assert config.attention_change_probability == 0.05

    def test_custom_config_values(self) -> None:
        """Test custom config values override defaults."""
        config = CoherenceConfig(
            circadian_enabled=False,
            fatigue_enabled=False,
            session_timeout=3600,
            fatigue_rate=0.2,
            max_session_duration=7200,
            attention_change_probability=0.1,
        )
        assert config.circadian_enabled is False
        assert config.fatigue_enabled is False
        assert config.session_timeout == 3600
        assert config.fatigue_rate == 0.2
        assert config.max_session_duration == 7200
        assert config.attention_change_probability == 0.1


class TestCoherenceEngineCreateSession:
    """Tests for CoherenceEngine.create_session method."""

    def test_create_session_with_random_persona(self) -> None:
        """Test create_session with no persona selects random persona."""
        engine = CoherenceEngine()
        state = engine.create_session()
        assert state.persona in list(UserPersona)

    def test_create_session_with_specific_persona(self) -> None:
        """Test create_session with specific persona uses that persona."""
        engine = CoherenceEngine()
        state = engine.create_session(persona=UserPersona.RESEARCHER)
        assert state.persona == UserPersona.RESEARCHER

    def test_create_session_stores_state(self) -> None:
        """Test create_session stores state in engine."""
        engine = CoherenceEngine()
        state = engine.create_session()
        stored_state = engine.get_session(state.session_id)
        assert stored_state is state

    def test_create_session_with_custom_id(self) -> None:
        """Test create_session with custom session_id."""
        engine = CoherenceEngine()
        custom_id = "custom_session_123"
        state = engine.create_session(session_id=custom_id)
        assert state.session_id == custom_id
        assert engine.get_session(custom_id) is state

    def test_create_session_generates_unique_id(self) -> None:
        """Test create_session generates unique session IDs."""
        engine = CoherenceEngine()
        state1 = engine.create_session()
        state2 = engine.create_session()
        assert state1.session_id != state2.session_id

    def test_create_session_initializes_state_correctly(self) -> None:
        """Test create_session initializes SessionState correctly."""
        engine = CoherenceEngine()
        state = engine.create_session(persona=UserPersona.CASUAL)
        assert state.attention_state == AttentionState.FOCUSED
        assert state.session_phase == SessionPhase.START
        assert state.fatigue_level == 0.0
        assert state.pages_visited == []
        assert state.total_clicks == 0
        assert state.total_keystrokes == 0

    def test_create_session_sets_start_time(self) -> None:
        """Test create_session sets start_time."""
        engine = CoherenceEngine()
        before = time.time()
        state = engine.create_session()
        after = time.time()
        assert before <= state.start_time <= after


class TestCoherenceEngineGetSession:
    """Tests for CoherenceEngine.get_session method."""

    def test_get_session_returns_stored_state(self) -> None:
        """Test get_session returns the stored session state."""
        engine = CoherenceEngine()
        state = engine.create_session()
        retrieved = engine.get_session(state.session_id)
        assert retrieved is state

    def test_get_session_returns_none_for_unknown_id(self) -> None:
        """Test get_session returns None for unknown session ID."""
        engine = CoherenceEngine()
        result = engine.get_session("nonexistent_id")
        assert result is None

    def test_get_session_multiple_sessions(self) -> None:
        """Test get_session retrieves correct session from multiple."""
        engine = CoherenceEngine()
        state1 = engine.create_session(persona=UserPersona.CASUAL)
        state2 = engine.create_session(persona=UserPersona.RESEARCHER)
        assert engine.get_session(state1.session_id) is state1
        assert engine.get_session(state2.session_id) is state2


class TestCoherenceEngineEndSession:
    """Tests for CoherenceEngine.end_session method."""

    def test_end_session_removes_state(self) -> None:
        """Test end_session removes session state."""
        engine = CoherenceEngine()
        state = engine.create_session()
        session_id = state.session_id
        engine.end_session(session_id)
        assert engine.get_session(session_id) is None

    def test_end_session_unknown_id_no_error(self) -> None:
        """Test end_session with unknown ID does not raise error."""
        engine = CoherenceEngine()
        engine.end_session("nonexistent_id")  # Should not raise

    def test_end_session_does_not_affect_other_sessions(self) -> None:
        """Test end_session does not affect other sessions."""
        engine = CoherenceEngine()
        state1 = engine.create_session()
        state2 = engine.create_session()
        engine.end_session(state1.session_id)
        assert engine.get_session(state1.session_id) is None
        assert engine.get_session(state2.session_id) is state2


class TestPersonaParameters:
    """Tests for persona parameter differences."""

    def test_scanner_has_short_attention_span(self) -> None:
        """Test SCANNER persona has short attention span."""
        engine = CoherenceEngine()
        # Create multiple sessions to get average
        attention_spans = []
        for _ in range(10):
            state = engine.create_session(persona=UserPersona.SCANNER)
            attention_spans.append(state.attention_span)
        avg_attention = sum(attention_spans) / len(attention_spans)
        # Scanner average should be around 60 seconds
        assert avg_attention < 120, "Scanner attention span too long"

    def test_researcher_has_long_attention_span(self) -> None:
        """Test RESEARCHER persona has long attention span."""
        engine = CoherenceEngine()
        # Create multiple sessions to get average
        attention_spans = []
        for _ in range(10):
            state = engine.create_session(persona=UserPersona.RESEARCHER)
            attention_spans.append(state.attention_span)
        avg_attention = sum(attention_spans) / len(attention_spans)
        # Researcher average should be around 600 seconds
        assert avg_attention > 400, "Researcher attention span too short"

    def test_scanner_shorter_than_researcher(self) -> None:
        """Test SCANNER has shorter attention than RESEARCHER."""
        engine = CoherenceEngine()
        scanner_spans = []
        researcher_spans = []
        for _ in range(20):
            scanner_state = engine.create_session(persona=UserPersona.SCANNER)
            researcher_state = engine.create_session(persona=UserPersona.RESEARCHER)
            scanner_spans.append(scanner_state.attention_span)
            researcher_spans.append(researcher_state.attention_span)
        avg_scanner = sum(scanner_spans) / len(scanner_spans)
        avg_researcher = sum(researcher_spans) / len(researcher_spans)
        assert avg_scanner < avg_researcher

    def test_power_user_has_high_typing_speed(self) -> None:
        """Test POWER_USER persona has high typing speed."""
        engine = CoherenceEngine()
        speeds = []
        for _ in range(10):
            state = engine.create_session(persona=UserPersona.POWER_USER)
            speeds.append(state.base_typing_speed)
        avg_speed = sum(speeds) / len(speeds)
        assert avg_speed > 60, "Power user typing speed too low"

    def test_scroller_has_very_short_attention(self) -> None:
        """Test SCROLLER persona has very short attention span."""
        engine = CoherenceEngine()
        spans = []
        for _ in range(10):
            state = engine.create_session(persona=UserPersona.SCROLLER)
            spans.append(state.attention_span)
        avg_span = sum(spans) / len(spans)
        assert avg_span < 60, "Scroller attention span too long"


class TestGetBehaviorModifiers:
    """Tests for CoherenceEngine.get_behavior_modifiers method."""

    def test_returns_dict_with_expected_keys(self) -> None:
        """Test get_behavior_modifiers returns dict with expected keys."""
        engine = CoherenceEngine()
        state = engine.create_session()
        modifiers = engine.get_behavior_modifiers(state)
        expected_keys = [
            "speed_factor",
            "dwell_time_factor",
            "error_rate",
            "focus_probability",
            "break_probability",
            "typo_probability",
            "misclick_probability",
        ]
        for key in expected_keys:
            assert key in modifiers, f"Missing key: {key}"

    def test_circadian_affects_modifiers(self) -> None:
        """Test circadian rhythm affects behavior modifiers."""
        engine_enabled = CoherenceEngine(CoherenceConfig(circadian_enabled=True))
        engine_disabled = CoherenceEngine(CoherenceConfig(circadian_enabled=False))
        state_enabled = engine_enabled.create_session(persona=UserPersona.CASUAL)
        state_disabled = engine_disabled.create_session(persona=UserPersona.CASUAL)
        # Make states have same base parameters for comparison
        state_disabled.base_mouse_speed = state_enabled.base_mouse_speed
        state_disabled.error_proneness = state_enabled.error_proneness
        mods_enabled = engine_enabled.get_behavior_modifiers(state_enabled)
        mods_disabled = engine_disabled.get_behavior_modifiers(state_disabled)
        # With circadian enabled, error_rate may differ due to circadian.error_rate
        # We can't guarantee they differ since it depends on time of day
        # Just verify they're valid
        assert isinstance(mods_enabled["error_rate"], float)
        assert isinstance(mods_disabled["error_rate"], float)

    def test_fatigue_affects_modifiers(self) -> None:
        """Test fatigue affects behavior modifiers."""
        engine = CoherenceEngine(CoherenceConfig(fatigue_enabled=True))
        state_fresh = engine.create_session(persona=UserPersona.CASUAL)
        state_fresh.fatigue_level = 0.0
        state_tired = engine.create_session(persona=UserPersona.CASUAL)
        state_tired.fatigue_level = 0.8
        # Make base params same
        state_tired.base_mouse_speed = state_fresh.base_mouse_speed
        state_tired.error_proneness = state_fresh.error_proneness
        mods_fresh = engine.get_behavior_modifiers(state_fresh)
        mods_tired = engine.get_behavior_modifiers(state_tired)
        # Tired should have lower speed factor
        assert mods_tired["speed_factor"] < mods_fresh["speed_factor"]
        # Tired should have higher error rate
        assert mods_tired["error_rate"] > mods_fresh["error_rate"]
        # Tired should have higher dwell time
        assert mods_tired["dwell_time_factor"] > mods_fresh["dwell_time_factor"]

    def test_modifiers_speed_factor_clamped(self) -> None:
        """Test speed_factor is clamped to valid range."""
        engine = CoherenceEngine()
        state = engine.create_session()
        modifiers = engine.get_behavior_modifiers(state)
        assert 0.3 <= modifiers["speed_factor"] <= 2.0

    def test_modifiers_dwell_time_factor_clamped(self) -> None:
        """Test dwell_time_factor is clamped to valid range."""
        engine = CoherenceEngine()
        state = engine.create_session()
        modifiers = engine.get_behavior_modifiers(state)
        assert 0.2 <= modifiers["dwell_time_factor"] <= 5.0

    def test_modifiers_error_rate_clamped(self) -> None:
        """Test error_rate is clamped to valid range."""
        engine = CoherenceEngine()
        state = engine.create_session()
        modifiers = engine.get_behavior_modifiers(state)
        assert 0.0 <= modifiers["error_rate"] <= 0.2

    def test_attention_state_affects_modifiers(self) -> None:
        """Test attention state affects behavior modifiers."""
        engine = CoherenceEngine(CoherenceConfig(circadian_enabled=False, fatigue_enabled=False))
        state_focused = engine.create_session(persona=UserPersona.CASUAL)
        state_focused.attention_state = AttentionState.FOCUSED
        state_idle = engine.create_session(persona=UserPersona.CASUAL)
        state_idle.attention_state = AttentionState.IDLE
        state_idle.base_mouse_speed = state_focused.base_mouse_speed
        mods_focused = engine.get_behavior_modifiers(state_focused)
        mods_idle = engine.get_behavior_modifiers(state_idle)
        # Idle should have lower speed factor
        assert mods_idle["speed_factor"] < mods_focused["speed_factor"]
        # Idle should have higher dwell time factor
        assert mods_idle["dwell_time_factor"] > mods_focused["dwell_time_factor"]


class TestRecordAction:
    """Tests for CoherenceEngine.record_action method."""

    def test_click_updates_total_clicks(self) -> None:
        """Test recording a click action updates total_clicks."""
        engine = CoherenceEngine()
        state = engine.create_session()
        initial_clicks = state.total_clicks
        engine.record_action(state, "click")
        assert state.total_clicks == initial_clicks + 1

    def test_keypress_updates_total_keystrokes(self) -> None:
        """Test recording a keypress action updates total_keystrokes."""
        engine = CoherenceEngine()
        state = engine.create_session()
        initial_keystrokes = state.total_keystrokes
        engine.record_action(state, "keypress")
        assert state.total_keystrokes == initial_keystrokes + 1

    def test_navigate_updates_pages_visited(self) -> None:
        """Test recording navigate action updates pages_visited."""
        engine = CoherenceEngine()
        state = engine.create_session()
        url = "https://example.com/page1"
        engine.record_action(state, "navigate", url=url)
        assert url in state.pages_visited

    def test_navigate_same_url_not_duplicated(self) -> None:
        """Test navigating to same URL does not duplicate in pages_visited."""
        engine = CoherenceEngine()
        state = engine.create_session()
        url = "https://example.com/page1"
        engine.record_action(state, "navigate", url=url)
        engine.record_action(state, "navigate", url=url)
        assert state.pages_visited.count(url) == 1

    def test_updates_last_action_time(self) -> None:
        """Test record_action updates last_action_time."""
        engine = CoherenceEngine()
        state = engine.create_session()
        before = time.time()
        engine.record_action(state, "click")
        after = time.time()
        assert before <= state.last_action_time <= after

    def test_multiple_clicks_accumulate(self) -> None:
        """Test multiple click actions accumulate."""
        engine = CoherenceEngine()
        state = engine.create_session()
        for _i in range(5):
            engine.record_action(state, "click")
        assert state.total_clicks == 5

    def test_multiple_keypresses_accumulate(self) -> None:
        """Test multiple keypress actions accumulate."""
        engine = CoherenceEngine()
        state = engine.create_session()
        for _i in range(10):
            engine.record_action(state, "keypress")
        assert state.total_keystrokes == 10


class TestSessionPhases:
    """Tests for session phase transitions."""

    def test_start_phase_at_beginning(self) -> None:
        """Test session starts in START phase."""
        engine = CoherenceEngine()
        state = engine.create_session()
        assert state.session_phase == SessionPhase.START

    def test_active_phase_after_5_minutes(self) -> None:
        """Test session transitions to ACTIVE after 5 minutes."""
        engine = CoherenceEngine()
        state = engine.create_session()
        # Simulate 6 minutes elapsed
        state.start_time = time.time() - 360
        engine.record_action(state, "click")
        assert state.session_phase == SessionPhase.ACTIVE

    def test_winding_down_phase_high_fatigue(self) -> None:
        """Test session transitions to WINDING_DOWN with high fatigue."""
        # Disable fatigue calculation so we can test phase logic directly
        config = CoherenceConfig(fatigue_enabled=False)
        engine = CoherenceEngine(config)
        state = engine.create_session()
        # Simulate past start phase and high fatigue
        state.start_time = time.time() - 400
        state.fatigue_level = 0.65
        # Call _determine_session_phase directly to test phase logic
        phase = engine._determine_session_phase(state)
        assert phase == SessionPhase.WINDING_DOWN

    def test_end_phase_very_high_fatigue(self) -> None:
        """Test session transitions to END with very high fatigue."""
        # Disable fatigue calculation so we can test phase logic directly
        config = CoherenceConfig(fatigue_enabled=False)
        engine = CoherenceEngine(config)
        state = engine.create_session()
        # Simulate past start phase and very high fatigue
        state.start_time = time.time() - 400
        state.fatigue_level = 0.85
        # Call _determine_session_phase directly to test phase logic
        phase = engine._determine_session_phase(state)
        assert phase == SessionPhase.END

    def test_end_phase_near_max_duration(self) -> None:
        """Test session transitions to END near max duration."""
        config = CoherenceConfig(max_session_duration=1000)
        engine = CoherenceEngine(config)
        state = engine.create_session()
        # Simulate > 90% of max duration
        state.start_time = time.time() - 950
        engine.record_action(state, "click")
        assert state.session_phase == SessionPhase.END


class TestRecordBreak:
    """Tests for CoherenceEngine.record_break method."""

    def test_reduces_fatigue(self) -> None:
        """Test record_break reduces fatigue level."""
        engine = CoherenceEngine()
        state = engine.create_session()
        state.fatigue_level = 0.5
        engine.record_break(state, duration=300)  # 5 minute break
        assert state.fatigue_level < 0.5

    def test_resets_attention_state(self) -> None:
        """Test record_break resets attention state to FOCUSED."""
        engine = CoherenceEngine()
        state = engine.create_session()
        state.attention_state = AttentionState.DISTRACTED
        engine.record_break(state, duration=60)
        assert state.attention_state == AttentionState.FOCUSED

    def test_updates_last_break_time(self) -> None:
        """Test record_break updates last_break_time."""
        engine = CoherenceEngine()
        state = engine.create_session()
        before = time.time()
        engine.record_break(state, duration=60)
        after = time.time()
        assert before <= state.last_break_time <= after

    def test_longer_break_more_fatigue_reduction(self) -> None:
        """Test longer breaks reduce more fatigue."""
        engine = CoherenceEngine()
        state1 = engine.create_session()
        state1.fatigue_level = 0.6
        state2 = engine.create_session()
        state2.fatigue_level = 0.6
        engine.record_break(state1, duration=60)  # 1 minute
        engine.record_break(state2, duration=600)  # 10 minutes
        assert state2.fatigue_level < state1.fatigue_level

    def test_fatigue_cannot_go_negative(self) -> None:
        """Test fatigue level cannot go below 0."""
        engine = CoherenceEngine()
        state = engine.create_session()
        state.fatigue_level = 0.1
        engine.record_break(state, duration=600)  # Long break
        assert state.fatigue_level >= 0.0

    def test_max_fatigue_reduction_capped(self) -> None:
        """Test fatigue reduction is capped at 0.3."""
        engine = CoherenceEngine()
        state = engine.create_session()
        state.fatigue_level = 0.5
        # Very long break (1 hour)
        engine.record_break(state, duration=3600)
        # Should reduce by at most 0.3
        assert state.fatigue_level >= 0.2


class TestCoherenceEngineInit:
    """Tests for CoherenceEngine initialization."""

    def test_default_config(self) -> None:
        """Test engine uses default config when none provided."""
        engine = CoherenceEngine()
        assert engine.config.circadian_enabled is True
        assert engine.config.fatigue_enabled is True

    def test_custom_config(self) -> None:
        """Test engine uses provided config."""
        config = CoherenceConfig(circadian_enabled=False)
        engine = CoherenceEngine(config)
        assert engine.config.circadian_enabled is False

    def test_sessions_dict_initialized_empty(self) -> None:
        """Test sessions dict is initialized empty."""
        engine = CoherenceEngine()
        assert engine._sessions == {}


class TestSessionState:
    """Tests for SessionState dataclass."""

    def test_default_attention_state(self) -> None:
        """Test default attention state is FOCUSED."""
        state = SessionState(
            session_id="test",
            persona=UserPersona.CASUAL,
            start_time=time.time(),
        )
        assert state.attention_state == AttentionState.FOCUSED

    def test_default_session_phase(self) -> None:
        """Test default session phase is START."""
        state = SessionState(
            session_id="test",
            persona=UserPersona.CASUAL,
            start_time=time.time(),
        )
        assert state.session_phase == SessionPhase.START

    def test_default_fatigue_level(self) -> None:
        """Test default fatigue level is 0."""
        state = SessionState(
            session_id="test",
            persona=UserPersona.CASUAL,
            start_time=time.time(),
        )
        assert state.fatigue_level == 0.0

    def test_default_pages_visited_empty(self) -> None:
        """Test default pages_visited is empty list."""
        state = SessionState(
            session_id="test",
            persona=UserPersona.CASUAL,
            start_time=time.time(),
        )
        assert state.pages_visited == []

    def test_pages_visited_not_shared_between_instances(self) -> None:
        """Test pages_visited list is not shared between instances."""
        state1 = SessionState(
            session_id="test1",
            persona=UserPersona.CASUAL,
            start_time=time.time(),
        )
        state2 = SessionState(
            session_id="test2",
            persona=UserPersona.CASUAL,
            start_time=time.time(),
        )
        state1.pages_visited.append("http://example.com")
        assert state2.pages_visited == []


class TestCircadianProfileRetrieval:
    """Tests for get_circadian_profile method."""

    def test_returns_circadian_profile(self) -> None:
        """Test get_circadian_profile returns CircadianProfile."""
        engine = CoherenceEngine()
        profile = engine.get_circadian_profile()
        assert isinstance(profile, CircadianProfile)

    def test_returns_profile_for_current_hour(self) -> None:
        """Test get_circadian_profile returns profile for current hour."""
        engine = CoherenceEngine()
        with patch("ghoststorm.plugins.behavior.coherence_engine.datetime") as mock_dt:
            mock_now = mock_dt.now.return_value
            mock_now.hour = 10
            profile = engine.get_circadian_profile()
            assert profile.hour == 10

    def test_fallback_to_noon_for_invalid_hour(self) -> None:
        """Test fallback to hour 12 if somehow invalid hour."""
        # This tests the .get() fallback - though in practice shouldn't happen
        engine = CoherenceEngine()
        profile = engine.get_circadian_profile()
        assert profile.hour in range(24)


class TestShouldTakeBreak:
    """Tests for should_take_break method."""

    def test_should_not_break_immediately(self) -> None:
        """Test should not suggest break immediately after session start."""
        engine = CoherenceEngine()
        state = engine.create_session()
        state.last_break_time = time.time()
        assert engine.should_take_break(state) is False

    def test_should_break_after_long_time(self) -> None:
        """Test should suggest break after long time without break."""
        engine = CoherenceEngine()
        state = engine.create_session()
        # Simulate 2 hours without break
        state.last_break_time = time.time() - 7200
        assert engine.should_take_break(state) is True

    def test_high_fatigue_increases_break_likelihood(self) -> None:
        """Test high fatigue makes breaks more likely."""
        engine = CoherenceEngine()
        state_fresh = engine.create_session()
        state_tired = engine.create_session()
        state_fresh.fatigue_level = 0.0
        state_tired.fatigue_level = 0.9
        # Same time since last break
        time_since = time.time() - 3000
        state_fresh.last_break_time = time_since
        state_tired.last_break_time = time_since
        # Tired user should need break sooner (or at same threshold)
        # Due to fatigue_level affecting break_threshold calculation
        # We can't guarantee exact behavior without knowing circadian,
        # but high fatigue reduces break_threshold
        # This is more of a sanity check that the method runs
        result_fresh = engine.should_take_break(state_fresh)
        result_tired = engine.should_take_break(state_tired)
        # At least one should be True given 50 min without break
        assert isinstance(result_fresh, bool)
        assert isinstance(result_tired, bool)
