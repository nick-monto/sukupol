from __future__ import annotations

import unittest

from app.agents.sanitize import sanitize_prompt_input


class PromptSanitizationUnitTests(unittest.TestCase):
    """Comprehensive coverage for sanitize_prompt_input."""

    # -- Control character stripping --

    def test_strips_c0_null(self) -> None:
        """C0 null byte (0x00) is removed entirely."""
        result = sanitize_prompt_input("\x00hello\x00")
        self.assertEqual(result, "hello")
        self.assertNotIn("\x00", result)

    def test_strips_c0_control_chars(self) -> None:
        """C0 chars (0x01-0x08, 0x0b-0x1f) are removed."""
        result = sanitize_prompt_input("\x01\x02\x03hello\x0e\x1f")
        self.assertEqual(result, "hello")
        for c in "\x01\x02\x03\x0e\x1f":
            self.assertNotIn(c, result)

    def test_strips_del(self) -> None:
        """DEL (0x7f) is removed entirely."""
        result = sanitize_prompt_input("abc\x7fdef")
        self.assertEqual(result, "abcdef")

    def test_strips_c1_control_chars(self) -> None:
        """C1 chars (0x80-0x9f) are removed entirely."""
        result = sanitize_prompt_input("a\x85b\x9fc")
        self.assertEqual(result, "abc")

    def test_strips_u2028_line_sep(self) -> None:
        """U+2028 LINE SEPARATOR is removed."""
        result = sanitize_prompt_input("line\u2028break")
        self.assertNotIn("\u2028", result)
        self.assertEqual(result, "linebreak")

    def test_strips_u2029_paragraph_sep(self) -> None:
        """U+2029 PARAGRAPH SEPARATOR is removed."""
        result = sanitize_prompt_input("para\u2029graph")
        self.assertNotIn("\u2029", result)
        self.assertEqual(result, "paragraph")

    def test_strips_u202e_right_to_left_override(self) -> None:
        """U+202E RIGHT-TO-LEFT OVERRIDE is removed."""
        result = sanitize_prompt_input("hello\u202eworld")
        self.assertNotIn("\u202e", result)
        self.assertEqual(result, "helloworld")

    def test_strips_mixed_control_chars(self) -> None:
        """All dangerous chars stripped together."""
        raw = "\x00hello\x7f\x85\u2028\u202eworld\u2029\x9f"
        result = sanitize_prompt_input(raw)
        self.assertNotIn("\x00", result)
        self.assertNotIn("\x7f", result)
        self.assertNotIn("\x85", result)
        self.assertNotIn("\u2028", result)
        self.assertNotIn("\u2029", result)
        self.assertNotIn("\u202e", result)
        self.assertNotIn("\x9f", result)

    # -- Whitespace handling --

    def test_converts_newlines_to_spaces(self) -> None:
        """\\n and \\r are converted to spaces then collapsed."""
        result = sanitize_prompt_input("hello\nworld\r\ninjection")
        self.assertNotIn("\n", result)
        self.assertNotIn("\r", result)
        self.assertEqual(result, "hello world injection")

    def test_converts_tabs_to_spaces(self) -> None:
        """\\t is converted to space."""
        result = sanitize_prompt_input("a\tb")
        self.assertNotIn("\t", result)
        self.assertEqual(result, "a b")

    def test_collapses_whitespace_runs(self) -> None:
        """Runs of multiple spaces collapse to one."""
        result = sanitize_prompt_input("a   b    c")
        self.assertEqual(result, "a b c")

    def test_collapses_mixed_whitespace(self) -> None:
        """Runs of mixed whitespace (spaces, newlines converted) collapse."""
        result = sanitize_prompt_input("a\n\n\n  \tb")
        self.assertEqual(result, "a b")

    def test_strips_leading_trailing_whitespace(self) -> None:
        """Leading and trailing whitespace is stripped."""
        result = sanitize_prompt_input("  hello world  ")
        self.assertEqual(result, "hello world")

    # -- Truncation --

    def test_truncates_long_input_on_word_boundary(self) -> None:
        """Input longer than max_len is truncated on last word boundary ≤ max_len."""
        raw = "word " * 500  # 2500 chars
        result = sanitize_prompt_input(raw, max_len=100)
        expected = " ".join(["word"] * 20)  # 20 words = 99 chars
        self.assertLessEqual(len(result), 100)
        self.assertEqual(result, expected)

    def test_truncates_long_input_hard_cut_no_boundary(self) -> None:
        """When there's no word boundary, hard-cut at max_len."""
        raw = "a" * 5000
        result = sanitize_prompt_input(raw, max_len=2000)
        self.assertEqual(len(result), 2000)
        self.assertEqual(result, "a" * 2000)

    def test_truncates_with_custom_max_len(self) -> None:
        """Custom max_len works."""
        raw = "hello world foo bar baz qux"
        result = sanitize_prompt_input(raw, max_len=12)
        # "hello world" = 11 chars (space at position 5)
        self.assertEqual(result, "hello world")

    def test_short_input_not_truncated(self) -> None:
        """Short input stays unchanged (aside from sanitization)."""
        raw = "hello world"
        result = sanitize_prompt_input(raw, max_len=2000)
        self.assertEqual(result, "hello world")

    # -- Idempotency --

    def test_idempotent(self) -> None:
        """Second pass yields identical result."""
        cases = [
            "hello world",
            "\x00abc\x00",
            "a\n\n\nb\nc",
            "  spaced  out  ",
            "word " * 500,
            "\u202eoverride\u2028here",
            "mixed \x00 control \x85 and \u2029 chars",
        ]
        for raw in cases:
            once = sanitize_prompt_input(raw)
            twice = sanitize_prompt_input(once)
            self.assertEqual(
                once,
                twice,
                f"Idempotency failed for {raw!r}: {once!r} != {twice!r}",
            )

    # -- Realistic scenarios --

    def test_real_player_message(self) -> None:
        """A realistic player message is sanitized as expected."""
        raw = "Hello, traveller!\nTell me about the cave."
        result = sanitize_prompt_input(raw)
        self.assertEqual(result, "Hello, traveller! Tell me about the cave.")

    def test_player_message_with_junk(self) -> None:
        """A player message with control chars is sanitized."""
        raw = "\x00IGNORE\x00: Hello\x1b[31mworld\x7f"
        result = sanitize_prompt_input(raw)
        self.assertEqual(result, "IGNORE: Hello[31mworld")

    def test_safe_content_preserved(self) -> None:
        """Normal safe content is unchanged."""
        raw = "Hello there, what waits below?"
        self.assertEqual(sanitize_prompt_input(raw), raw)

    def test_empty_string(self) -> None:
        """Empty string produces empty string."""
        self.assertEqual(sanitize_prompt_input(""), "")

    def test_only_whitespace(self) -> None:
        """String with only whitespace becomes empty."""
        self.assertEqual(sanitize_prompt_input("   \n  \t  "), "")

    def test_only_control_chars(self) -> None:
        """String with only control chars becomes empty."""
        self.assertEqual(sanitize_prompt_input("\x00\x01\x02\x7f\x85"), "")


if __name__ == "__main__":
    unittest.main()
