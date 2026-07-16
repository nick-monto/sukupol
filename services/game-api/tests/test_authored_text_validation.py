from __future__ import annotations

import unittest

from app.agents.sanitize import sanitize_prompt_input
from app.agents.validate import validate_authored_text


class ValidateAuthoredTextTests(unittest.TestCase):
    """Unit tests for ``validate_authored_text``."""

    def test_rejects_newline_embedded(self) -> None:
        self.assertIsNone(validate_authored_text("Evil\nQuest", max_len=80))

    def test_rejects_u202e(self) -> None:
        self.assertIsNone(validate_authored_text("Evil\u202eQuest", max_len=80))

    def test_rejects_over_length(self) -> None:
        self.assertIsNone(validate_authored_text("a" * 81, max_len=80))

    def test_accepts_exactly_max_len(self) -> None:
        self.assertIsNotNone(validate_authored_text("a" * 80, max_len=80))

    def test_rejects_one_over_max_len(self) -> None:
        self.assertIsNone(validate_authored_text("a" * 81, max_len=80))

    def test_returns_stripped_sanitized_text(self) -> None:
        result = validate_authored_text("  Hello World  ", max_len=100)
        self.assertEqual("Hello World", result)

    def test_rejects_empty_after_sanitize(self) -> None:
        self.assertIsNone(validate_authored_text("   ", max_len=100))

    def test_rejects_control_chars(self) -> None:
        self.assertIsNone(validate_authored_text("bad\x00text", max_len=100))
        self.assertIsNone(validate_authored_text("bad\x7ftext", max_len=100))
        self.assertIsNone(validate_authored_text("bad\x85text", max_len=100))

    def test_sanitize_newline_becomes_space(self) -> None:
        """Combat parley contract: ``\\n`` is cleaned to space, not rejected."""
        self.assertEqual("a b", sanitize_prompt_input("a\nb"))


class QuestOfferNormalizeTests(unittest.TestCase):
    """Integration tests for ``_normalize_offer_payload`` behaviour."""

    def setUp(self) -> None:
        from app.agents import QuestGenerationService
        from app.agents.runtime import AgentExecutor

        self.service = QuestGenerationService(executor=AgentExecutor(mode="local-llm"))

    def _normalize(self, **fields: str) -> dict[str, str] | None:
        return self.service._normalize_offer_payload(fields)  # type: ignore[arg-type]

    def test_newline_title_rejected(self) -> None:
        result = self._normalize(
            title="Evil\nQuest",
            summary="Marta wants her satchel back.",
            objective_text="Recover the satchel.",
            offer_text="Bring it to me.",
        )
        self.assertIsNone(result)

    def test_u202e_summary_rejected(self) -> None:
        result = self._normalize(
            title="Recover Marta's Satchel",
            summary="Evil\u202eoverride",
            objective_text="Recover the satchel.",
            offer_text="Bring it to me.",
        )
        self.assertIsNone(result)

    def test_overlong_title_rejected(self) -> None:
        result = self._normalize(
            title="A" * 81,
            summary="Marta wants her satchel back.",
            objective_text="Recover the satchel.",
            offer_text="Bring it to me.",
        )
        self.assertIsNone(result)

    def test_title_80_passes_81_fails(self) -> None:
        ok = self._normalize(
            title="A" * 80,
            summary="Marta wants her satchel back.",
            objective_text="Recover the satchel.",
            offer_text="Bring it to me.",
        )
        self.assertIsNotNone(ok)
        self.assertIsNotNone(ok and ok["title"])

        bad = self._normalize(
            title="A" * 81,
            summary="Marta wants her satchel back.",
            objective_text="Recover the satchel.",
            offer_text="Bring it to me.",
        )
        self.assertIsNone(bad)

    def test_all_valid_fields_returned_cleaned(self) -> None:
        result = self._normalize(
            title="  Recover Marta's Satchel  ",
            summary="  She wants it back from the archives.  ",
            objective_text="  Find the satchel.  ",
            offer_text="  Bring it to me.  ",
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual("Recover Marta's Satchel", result["title"])
        self.assertEqual("She wants it back from the archives.", result["summary"])
        self.assertEqual("Find the satchel.", result["objective_text"])
        self.assertEqual("Bring it to me.", result["offer_text"])


class LoreUpdateNormalizeTests(unittest.TestCase):
    """Integration tests for ``_normalize_lore_updates`` behaviour."""

    def _normalize(self, *entries: dict[str, str]) -> list[dict[str, str]]:
        from app.dialogue.summary import _normalize_lore_updates

        return _normalize_lore_updates(list(entries))

    def test_skips_entry_with_control_char_content(self) -> None:
        result = self._normalize(
            {"category": "lore", "content": "clean lore"},
            {"category": "history", "content": "dirty\x00content"},
            {"category": "rumor", "content": "another clean one"},
        )
        self.assertEqual(2, len(result))
        self.assertEqual("clean lore", result[0]["content"])
        self.assertEqual("another clean one", result[1]["content"])

    def test_keeps_valid_entries_within_cap(self) -> None:
        entries = [{"category": f"cat{i}", "content": f"content{i}"} for i in range(6)]
        result = self._normalize(*entries)
        # cap at 4
        self.assertEqual(4, len(result))
        for i, entry in enumerate(result):
            self.assertEqual(f"cat{i}", entry["category"])
            self.assertEqual(f"content{i}", entry["content"])

    def test_skips_entry_with_empty_content(self) -> None:
        result = self._normalize(
            {"category": "lore", "content": ""},
            {"category": "history", "content": "real content"},
        )
        self.assertEqual(1, len(result))
        self.assertEqual("real content", result[0]["content"])

    def test_skips_entry_with_newline_in_category(self) -> None:
        result = self._normalize(
            {"category": "bad\ncategory", "content": "some content"},
            {"category": "good", "content": "real content"},
        )
        self.assertEqual(1, len(result))
        self.assertEqual("good", result[0]["category"])
        self.assertEqual("real content", result[0]["content"])


class CombatParleySanitizationTests(unittest.TestCase):
    """Combat parley uses sanitize-only (not reject) for LLM text."""

    def test_reply_with_embedded_newline_cleaned(self) -> None:
        """\\n in LLM reply becomes space in transcript."""
        from app.agents.sanitize import sanitize_prompt_input

        self.assertEqual(
            "The dragon pauses and listens to your terms.",
            sanitize_prompt_input("The dragon pauses\nand listens to your terms."),
        )


if __name__ == "__main__":
    unittest.main()
