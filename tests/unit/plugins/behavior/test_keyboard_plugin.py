"""Tests for keyboard behavior plugin."""

from __future__ import annotations

import string
from unittest.mock import AsyncMock, patch

import pytest

from ghoststorm.plugins.behavior.keyboard_plugin import KeyboardBehavior

# ============================================================================
# KEYBOARD BEHAVIOR INIT TESTS
# ============================================================================


class TestKeyboardBehaviorInit:
    """Tests for KeyboardBehavior initialization."""

    def test_default_wpm_range(self):
        """Test default WPM range is (40, 80)."""
        kb = KeyboardBehavior()
        assert kb.wpm_range == (40, 80)

    def test_default_typo_probability(self):
        """Test default typo probability is 0.02."""
        kb = KeyboardBehavior()
        assert kb.typo_probability == 0.02

    def test_default_word_pause_range(self):
        """Test default word pause range is (0.1, 0.4)."""
        kb = KeyboardBehavior()
        assert kb.word_pause_range == (0.1, 0.4)

    def test_default_sentence_pause_range(self):
        """Test default sentence pause range is (0.3, 0.8)."""
        kb = KeyboardBehavior()
        assert kb.sentence_pause_range == (0.3, 0.8)

    def test_default_burst_probability(self):
        """Test default burst probability is 0.1."""
        kb = KeyboardBehavior()
        assert kb.burst_probability == 0.1

    def test_custom_wpm_range(self):
        """Test custom WPM range is stored."""
        kb = KeyboardBehavior(wpm_range=(60, 120))
        assert kb.wpm_range == (60, 120)

    def test_custom_wpm_range_slow_typist(self):
        """Test slow typist WPM range."""
        kb = KeyboardBehavior(wpm_range=(20, 30))
        assert kb.wpm_range == (20, 30)

    def test_custom_wpm_range_fast_typist(self):
        """Test fast typist WPM range."""
        kb = KeyboardBehavior(wpm_range=(100, 150))
        assert kb.wpm_range == (100, 150)

    def test_custom_typo_probability_zero(self):
        """Test zero typo probability (no typos)."""
        kb = KeyboardBehavior(typo_probability=0.0)
        assert kb.typo_probability == 0.0

    def test_custom_typo_probability_high(self):
        """Test high typo probability."""
        kb = KeyboardBehavior(typo_probability=0.15)
        assert kb.typo_probability == 0.15

    def test_custom_word_pause_range(self):
        """Test custom word pause range."""
        kb = KeyboardBehavior(word_pause_range=(0.2, 0.5))
        assert kb.word_pause_range == (0.2, 0.5)

    def test_custom_sentence_pause_range(self):
        """Test custom sentence pause range."""
        kb = KeyboardBehavior(sentence_pause_range=(0.5, 1.0))
        assert kb.sentence_pause_range == (0.5, 1.0)

    def test_custom_burst_probability(self):
        """Test custom burst probability."""
        kb = KeyboardBehavior(burst_probability=0.25)
        assert kb.burst_probability == 0.25

    def test_name_attribute(self):
        """Test class name attribute."""
        assert KeyboardBehavior.name == "keyboard"


# ============================================================================
# ADJACENT KEYS MAPPING TESTS
# ============================================================================


class TestAdjacentKeysMapping:
    """Tests for ADJACENT_KEYS mapping."""

    def test_all_lowercase_letters_have_adjacent_keys(self):
        """Test all lowercase letters a-z have adjacent keys defined."""
        kb = KeyboardBehavior()
        for letter in string.ascii_lowercase:
            assert letter in kb.ADJACENT_KEYS, f"Letter '{letter}' missing from ADJACENT_KEYS"

    def test_adjacent_keys_are_lowercase(self):
        """Test all adjacent keys are lowercase letters."""
        kb = KeyboardBehavior()
        for letter, adjacents in kb.ADJACENT_KEYS.items():
            for adj in adjacents:
                assert adj.islower(), f"Adjacent key '{adj}' for '{letter}' is not lowercase"
                assert adj.isalpha(), f"Adjacent key '{adj}' for '{letter}' is not a letter"

    def test_qwerty_layout_q_adjacent(self):
        """Test 'q' has correct adjacent keys (w, a)."""
        kb = KeyboardBehavior()
        assert set(kb.ADJACENT_KEYS["q"]) == {"w", "a"}

    def test_qwerty_layout_a_adjacent(self):
        """Test 'a' has correct adjacent keys (q, w, s, z)."""
        kb = KeyboardBehavior()
        assert set(kb.ADJACENT_KEYS["a"]) == {"q", "w", "s", "z"}

    def test_qwerty_layout_s_adjacent(self):
        """Test 's' has correct adjacent keys."""
        kb = KeyboardBehavior()
        assert set(kb.ADJACENT_KEYS["s"]) == {"a", "w", "e", "d", "x", "z"}

    def test_qwerty_layout_f_adjacent(self):
        """Test 'f' has correct adjacent keys (home row, many neighbors)."""
        kb = KeyboardBehavior()
        assert set(kb.ADJACENT_KEYS["f"]) == {"d", "r", "t", "g", "v", "c"}

    def test_qwerty_layout_j_adjacent(self):
        """Test 'j' has correct adjacent keys (home row, many neighbors)."""
        kb = KeyboardBehavior()
        assert set(kb.ADJACENT_KEYS["j"]) == {"h", "u", "i", "k", "m", "n"}

    def test_qwerty_layout_p_adjacent(self):
        """Test 'p' has correct adjacent keys (edge key)."""
        kb = KeyboardBehavior()
        assert set(kb.ADJACENT_KEYS["p"]) == {"o", "l"}

    def test_qwerty_layout_z_adjacent(self):
        """Test 'z' has correct adjacent keys (corner key)."""
        kb = KeyboardBehavior()
        assert set(kb.ADJACENT_KEYS["z"]) == {"a", "s", "x"}

    def test_qwerty_layout_m_adjacent(self):
        """Test 'm' has correct adjacent keys (bottom row edge)."""
        kb = KeyboardBehavior()
        assert set(kb.ADJACENT_KEYS["m"]) == {"n", "j", "k"}

    def test_adjacent_keys_are_nearby_on_qwerty(self):
        """Test that adjacent keys are actually nearby on QWERTY layout."""
        kb = KeyboardBehavior()
        # Verify some key adjacencies make physical sense
        assert "w" in kb.ADJACENT_KEYS["e"]  # w is left of e
        assert "r" in kb.ADJACENT_KEYS["e"]  # r is right of e
        assert "d" in kb.ADJACENT_KEYS["e"]  # d is below e
        assert "s" in kb.ADJACENT_KEYS["e"]  # s is diagonally below-left

    def test_each_letter_has_at_least_two_adjacent(self):
        """Test each letter has at least 2 adjacent keys."""
        kb = KeyboardBehavior()
        for letter, adjacents in kb.ADJACENT_KEYS.items():
            assert len(adjacents) >= 2, f"Letter '{letter}' has fewer than 2 adjacent keys"


# ============================================================================
# GENERATE TYPO METHOD TESTS
# ============================================================================


class TestGenerateTypo:
    """Tests for _generate_typo method."""

    def test_returns_adjacent_key_for_lowercase(self):
        """Test typo returns an adjacent key for lowercase letter."""
        kb = KeyboardBehavior()
        typo = kb._generate_typo("a")
        assert typo in kb.ADJACENT_KEYS["a"]

    def test_returns_adjacent_key_for_another_lowercase(self):
        """Test typo returns an adjacent key for different letter."""
        kb = KeyboardBehavior()
        typo = kb._generate_typo("t")
        assert typo in kb.ADJACENT_KEYS["t"]

    def test_preserves_case_uppercase_input(self):
        """Test uppercase input returns uppercase typo."""
        kb = KeyboardBehavior()
        typo = kb._generate_typo("A")
        assert typo is not None
        assert typo.isupper()
        assert typo.lower() in kb.ADJACENT_KEYS["a"]

    def test_preserves_case_uppercase_middle(self):
        """Test uppercase in middle of alphabet."""
        kb = KeyboardBehavior()
        typo = kb._generate_typo("M")
        assert typo is not None
        assert typo.isupper()
        assert typo.lower() in kb.ADJACENT_KEYS["m"]

    def test_non_letter_returns_none_digit(self):
        """Test digit returns None."""
        kb = KeyboardBehavior()
        assert kb._generate_typo("5") is None

    def test_non_letter_returns_none_space(self):
        """Test space returns None."""
        kb = KeyboardBehavior()
        assert kb._generate_typo(" ") is None

    def test_non_letter_returns_none_punctuation(self):
        """Test punctuation returns None."""
        kb = KeyboardBehavior()
        assert kb._generate_typo(".") is None
        assert kb._generate_typo(",") is None
        assert kb._generate_typo("!") is None

    def test_non_letter_returns_none_special_char(self):
        """Test special characters return None."""
        kb = KeyboardBehavior()
        assert kb._generate_typo("@") is None
        assert kb._generate_typo("#") is None
        assert kb._generate_typo("$") is None

    def test_typo_is_random_choice(self):
        """Test that typo is randomly selected from adjacent keys."""
        kb = KeyboardBehavior()
        # Generate many typos and check distribution
        typos = set()
        for _ in range(100):
            typo = kb._generate_typo("f")
            typos.add(typo)
        # Should get multiple different adjacent keys
        assert len(typos) > 1


# ============================================================================
# GET CHAR DELAY METHOD TESTS
# ============================================================================


class TestGetCharDelay:
    """Tests for _get_char_delay method."""

    def test_uppercase_slower_than_base(self):
        """Test uppercase letters are slower (1.2-1.5x base delay)."""
        kb = KeyboardBehavior()
        base_delay = 0.1
        with patch("random.uniform", return_value=1.35):
            delay = kb._get_char_delay("A", base_delay)
        assert delay == 0.135  # 0.1 * 1.35

    def test_uppercase_minimum_multiplier(self):
        """Test uppercase uses at least 1.2x multiplier."""
        kb = KeyboardBehavior()
        base_delay = 0.1
        with patch("random.uniform", return_value=1.2):
            delay = kb._get_char_delay("Z", base_delay)
        assert delay == 0.12

    def test_uppercase_maximum_multiplier(self):
        """Test uppercase uses at most 1.5x multiplier."""
        kb = KeyboardBehavior()
        base_delay = 0.1
        with patch("random.uniform", return_value=1.5):
            delay = kb._get_char_delay("M", base_delay)
        assert delay == pytest.approx(0.15)

    def test_shift_characters_slower(self):
        """Test shift characters (!@#etc) are slower like uppercase."""
        kb = KeyboardBehavior()
        base_delay = 0.1
        shift_chars = '!@#$%^&*()_+{}|:"<>?'
        for char in shift_chars:
            with patch("random.uniform", return_value=1.3):
                delay = kb._get_char_delay(char, base_delay)
            assert delay == 0.13, f"Shift char '{char}' should use 1.3x multiplier"

    def test_numbers_slower_than_letters(self):
        """Test digits are slower than regular letters (1.1-1.3x)."""
        kb = KeyboardBehavior()
        base_delay = 0.1
        with patch("random.uniform", return_value=1.2):
            delay = kb._get_char_delay("5", base_delay)
        assert delay == 0.12

    def test_numbers_minimum_multiplier(self):
        """Test numbers use at least 1.1x multiplier."""
        kb = KeyboardBehavior()
        base_delay = 0.1
        with patch("random.uniform", return_value=1.1):
            delay = kb._get_char_delay("0", base_delay)
        assert delay == pytest.approx(0.11)

    def test_numbers_maximum_multiplier(self):
        """Test numbers use at most 1.3x multiplier."""
        kb = KeyboardBehavior()
        base_delay = 0.1
        with patch("random.uniform", return_value=1.3):
            delay = kb._get_char_delay("9", base_delay)
        assert delay == 0.13

    def test_punctuation_near_base_delay(self):
        """Test common punctuation is near base delay (0.9-1.1x)."""
        kb = KeyboardBehavior()
        base_delay = 0.1
        for char in ".,;'":
            with patch("random.uniform", return_value=1.0):
                delay = kb._get_char_delay(char, base_delay)
            assert delay == 0.1

    def test_regular_letters_base_range(self):
        """Test regular lowercase letters use 0.8-1.2x range."""
        kb = KeyboardBehavior()
        base_delay = 0.1
        with patch("random.uniform", return_value=1.0):
            delay = kb._get_char_delay("a", base_delay)
        assert delay == 0.1

    def test_regular_letters_can_be_faster(self):
        """Test regular letters can be faster than base (0.8x)."""
        kb = KeyboardBehavior()
        base_delay = 0.1
        with patch("random.uniform", return_value=0.8):
            delay = kb._get_char_delay("e", base_delay)
        assert delay == pytest.approx(0.08)

    def test_regular_letters_can_be_slower(self):
        """Test regular letters can be slower than base (1.2x)."""
        kb = KeyboardBehavior()
        base_delay = 0.1
        with patch("random.uniform", return_value=1.2):
            delay = kb._get_char_delay("x", base_delay)
        assert delay == 0.12


# ============================================================================
# WPM TO DELAY CONVERSION TESTS
# ============================================================================


class TestWpmToDelay:
    """Tests for _wpm_to_delay method."""

    def test_formula_is_12_divided_by_wpm(self):
        """Test formula: delay = 12 / wpm."""
        kb = KeyboardBehavior()
        # 60 WPM -> 0.2s delay
        assert kb._wpm_to_delay(60) == 0.2

    def test_40_wpm_delay(self):
        """Test 40 WPM gives 0.3s delay."""
        kb = KeyboardBehavior()
        assert kb._wpm_to_delay(40) == 0.3

    def test_80_wpm_delay(self):
        """Test 80 WPM gives 0.15s delay."""
        kb = KeyboardBehavior()
        assert kb._wpm_to_delay(80) == 0.15

    def test_120_wpm_delay(self):
        """Test 120 WPM gives 0.1s delay."""
        kb = KeyboardBehavior()
        assert kb._wpm_to_delay(120) == 0.1

    def test_higher_wpm_shorter_delay(self):
        """Test higher WPM results in shorter delay."""
        kb = KeyboardBehavior()
        delay_slow = kb._wpm_to_delay(40)
        delay_fast = kb._wpm_to_delay(100)
        assert delay_fast < delay_slow

    def test_12_wpm_gives_1_second_delay(self):
        """Test 12 WPM gives exactly 1 second delay."""
        kb = KeyboardBehavior()
        assert kb._wpm_to_delay(12) == 1.0

    def test_24_wpm_gives_half_second_delay(self):
        """Test 24 WPM gives 0.5 second delay."""
        kb = KeyboardBehavior()
        assert kb._wpm_to_delay(24) == 0.5

    def test_returns_float(self):
        """Test method returns float type."""
        kb = KeyboardBehavior()
        result = kb._wpm_to_delay(50)
        assert isinstance(result, float)


# ============================================================================
# ASYNC TYPE_TEXT METHOD TESTS
# ============================================================================


class TestTypeText:
    """Tests for async type_text method."""

    @pytest.mark.asyncio
    async def test_types_each_character(self, mock_page, mock_sleep):
        """Test that each character is typed."""
        kb = KeyboardBehavior(typo_probability=0.0, burst_probability=0.0)
        text = "hello"
        await kb.type_text(mock_page, text, simulate_typos=False)
        # Each character should be typed
        assert mock_page.keyboard.type.call_count == len(text)

    @pytest.mark.asyncio
    async def test_types_characters_in_order(self, mock_page, mock_sleep):
        """Test characters are typed in correct order."""
        kb = KeyboardBehavior(typo_probability=0.0, burst_probability=0.0)
        text = "abc"
        await kb.type_text(mock_page, text, simulate_typos=False)
        calls = mock_page.keyboard.type.call_args_list
        assert calls[0][0][0] == "a"
        assert calls[1][0][0] == "b"
        assert calls[2][0][0] == "c"

    @pytest.mark.asyncio
    async def test_sleep_called_for_each_character(self, mock_page, mock_sleep):
        """Test asyncio.sleep is called for character delays."""
        kb = KeyboardBehavior(typo_probability=0.0, burst_probability=0.0)
        text = "hi"
        await kb.type_text(mock_page, text, simulate_typos=False)
        # At least one sleep per character
        assert mock_sleep.call_count >= len(text)

    @pytest.mark.asyncio
    async def test_word_pause_after_space(self, mock_page, mock_sleep):
        """Test extra pause is added after space."""
        kb = KeyboardBehavior(
            typo_probability=0.0,
            burst_probability=0.0,
            word_pause_range=(0.2, 0.3),
        )
        text = "a b"
        await kb.type_text(mock_page, text, simulate_typos=False)
        # Should have character delays + word pause after space
        # 3 chars = 3 delays, plus 1 word pause
        assert mock_sleep.call_count >= 4

    @pytest.mark.asyncio
    async def test_sentence_pause_after_period(self, mock_page, mock_sleep):
        """Test extra pause is added after sentence-ending punctuation."""
        kb = KeyboardBehavior(
            typo_probability=0.0,
            burst_probability=0.0,
            sentence_pause_range=(0.4, 0.5),
        )
        text = "a."
        await kb.type_text(mock_page, text, simulate_typos=False)
        # 2 chars = 2 delays, plus 1 sentence pause
        assert mock_sleep.call_count >= 3

    @pytest.mark.asyncio
    async def test_sentence_pause_after_exclamation(self, mock_page, mock_sleep):
        """Test extra pause after exclamation mark."""
        kb = KeyboardBehavior(typo_probability=0.0, burst_probability=0.0)
        text = "hi!"
        await kb.type_text(mock_page, text, simulate_typos=False)
        assert mock_page.keyboard.type.call_count == 3

    @pytest.mark.asyncio
    async def test_sentence_pause_after_question(self, mock_page, mock_sleep):
        """Test extra pause after question mark."""
        kb = KeyboardBehavior(typo_probability=0.0, burst_probability=0.0)
        text = "hi?"
        await kb.type_text(mock_page, text, simulate_typos=False)
        assert mock_page.keyboard.type.call_count == 3

    @pytest.mark.asyncio
    async def test_clicks_selector_before_typing(self, mock_page, mock_sleep):
        """Test selector is clicked before typing starts."""
        kb = KeyboardBehavior(typo_probability=0.0, burst_probability=0.0)
        mock_page.click = AsyncMock()
        await kb.type_text(mock_page, "test", selector="#input")
        mock_page.click.assert_called_once_with("#input")

    @pytest.mark.asyncio
    async def test_clear_first_sends_ctrl_a_backspace(self, mock_page, mock_sleep):
        """Test clear_first clears existing content."""
        kb = KeyboardBehavior(typo_probability=0.0, burst_probability=0.0)
        await kb.type_text(mock_page, "test", clear_first=True)
        # Should press Control+a then Backspace
        press_calls = [call[0][0] for call in mock_page.keyboard.press.call_args_list]
        assert "Control+a" in press_calls
        assert "Backspace" in press_calls

    @pytest.mark.asyncio
    async def test_empty_text_no_typing(self, mock_page, mock_sleep):
        """Test empty text results in no typing."""
        kb = KeyboardBehavior()
        await kb.type_text(mock_page, "")
        mock_page.keyboard.type.assert_not_called()


# ============================================================================
# ASYNC PRESS_KEY METHOD TESTS
# ============================================================================


class TestPressKey:
    """Tests for async press_key method."""

    @pytest.mark.asyncio
    async def test_simple_key_press(self, mock_page, mock_sleep):
        """Test simple key press without modifiers."""
        kb = KeyboardBehavior()
        await kb.press_key(mock_page, "Enter")
        mock_page.keyboard.down.assert_called()
        mock_page.keyboard.up.assert_called()

    @pytest.mark.asyncio
    async def test_simple_key_presses_and_releases(self, mock_page, mock_sleep):
        """Test key is pressed down and then released."""
        kb = KeyboardBehavior()
        await kb.press_key(mock_page, "Tab")
        # Should call down then up for the key
        down_calls = [call[0][0] for call in mock_page.keyboard.down.call_args_list]
        up_calls = [call[0][0] for call in mock_page.keyboard.up.call_args_list]
        assert "Tab" in down_calls
        assert "Tab" in up_calls

    @pytest.mark.asyncio
    async def test_with_single_modifier(self, mock_page, mock_sleep):
        """Test key press with single modifier."""
        kb = KeyboardBehavior()
        await kb.press_key(mock_page, "c", modifiers=["Control"])
        down_calls = [call[0][0] for call in mock_page.keyboard.down.call_args_list]
        up_calls = [call[0][0] for call in mock_page.keyboard.up.call_args_list]
        # Modifier pressed before key
        assert "Control" in down_calls
        assert "c" in down_calls
        # Both released
        assert "Control" in up_calls
        assert "c" in up_calls

    @pytest.mark.asyncio
    async def test_with_multiple_modifiers(self, mock_page, mock_sleep):
        """Test key press with multiple modifiers."""
        kb = KeyboardBehavior()
        await kb.press_key(mock_page, "s", modifiers=["Control", "Shift"])
        down_calls = [call[0][0] for call in mock_page.keyboard.down.call_args_list]
        assert "Control" in down_calls
        assert "Shift" in down_calls
        assert "s" in down_calls

    @pytest.mark.asyncio
    async def test_modifiers_released_in_reverse_order(self, mock_page, mock_sleep):
        """Test modifiers are released in reverse order."""
        kb = KeyboardBehavior()
        await kb.press_key(mock_page, "z", modifiers=["Control", "Shift"])
        up_calls = [call[0][0] for call in mock_page.keyboard.up.call_args_list]
        # Key released first, then modifiers in reverse
        # z, Shift, Control
        z_idx = up_calls.index("z")
        shift_idx = up_calls.index("Shift")
        control_idx = up_calls.index("Control")
        assert z_idx < shift_idx < control_idx

    @pytest.mark.asyncio
    async def test_with_custom_hold_time(self, mock_page, mock_sleep):
        """Test key press with custom hold time."""
        kb = KeyboardBehavior()
        await kb.press_key(mock_page, "a", hold_time=0.5)
        # Should sleep for the hold time
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert 0.5 in sleep_calls

    @pytest.mark.asyncio
    async def test_hold_time_between_down_and_up(self, mock_page, mock_sleep):
        """Test hold time sleep occurs between down and up."""
        kb = KeyboardBehavior()
        await kb.press_key(mock_page, "Space", hold_time=0.3)
        mock_page.keyboard.down.assert_called_with("Space")
        mock_page.keyboard.up.assert_called_with("Space")

    @pytest.mark.asyncio
    async def test_without_hold_time_uses_random_delay(self, mock_page, mock_sleep):
        """Test without hold_time, random delay (0.05-0.12) is used."""
        kb = KeyboardBehavior()
        with patch("random.uniform", return_value=0.08) as mock_uniform:
            await kb.press_key(mock_page, "Enter")
            # Check random.uniform was called for hold delay
            mock_uniform.assert_any_call(0.05, 0.12)

    @pytest.mark.asyncio
    async def test_small_delay_after_key_press(self, mock_page, mock_sleep):
        """Test small delay added after key press (0.05-0.1s)."""
        kb = KeyboardBehavior()
        await kb.press_key(mock_page, "Escape")
        # Last sleep should be the post-press delay
        assert mock_sleep.call_count > 0
