from __future__ import annotations

import pytest

from app.agents.config import resolve_base_url


class TestResolveBaseUrl:
    """Coverage for resolve_base_url (AF6)."""

    # -- Framework mode (for_framework=True) --

    def test_framework_plain_gets_v1_slash(self) -> None:
        """Plain URL gets /v1/ appended for framework mode."""
        result = resolve_base_url("http://localhost:8033", for_framework=True)
        assert result == "http://localhost:8033/v1/"

    def test_framework_v1_gets_trailing_slash(self) -> None:
        """URL ending /v1 gets trailing slash for framework mode."""
        result = resolve_base_url("http://localhost:8033/v1", for_framework=True)
        assert result == "http://localhost:8033/v1/"

    def test_framework_v1_slash_stays(self) -> None:
        """URL ending /v1/ stays unchanged for framework mode."""
        result = resolve_base_url("http://localhost:8033/v1/", for_framework=True)
        assert result == "http://localhost:8033/v1/"

    def test_framework_full_endpoint_stays(self) -> None:
        """URL with full /v1/chat/completions stays unchanged for framework mode."""
        result = resolve_base_url(
            "http://localhost:8033/v1/chat/completions", for_framework=True
        )
        assert result == "http://localhost:8033/v1/chat/completions"

    def test_framework_https(self) -> None:
        """https scheme works with framework mode."""
        result = resolve_base_url("https://api.openai.com", for_framework=True)
        assert result == "https://api.openai.com/v1/"

    # -- Provider mode (for_framework=False / chat-completions) --

    def test_provider_plain_gets_v1_chat_completions(self) -> None:
        """Plain URL gets /v1/chat/completions appended."""
        result = resolve_base_url("http://localhost:8033", for_framework=False)
        assert result == "http://localhost:8033/v1/chat/completions"

    def test_provider_v1_gets_chat_completions(self) -> None:
        """URL ending /v1 gets /chat/completions appended."""
        result = resolve_base_url(
            "http://localhost:8033/v1", for_framework=False
        )
        assert result == "http://localhost:8033/v1/chat/completions"

    def test_provider_full_endpoint_stays(self) -> None:
        """URL with full /v1/chat/completions stays unchanged."""
        result = resolve_base_url(
            "http://localhost:8033/v1/chat/completions", for_framework=False
        )
        assert result == "http://localhost:8033/v1/chat/completions"

    def test_provider_v1_slash_gets_chat_completions(self) -> None:
        """URL ending /v1/ gets /chat/completions appended."""
        result = resolve_base_url("http://localhost:8033/v1/", for_framework=False)
        assert result == "http://localhost:8033/v1/chat/completions"

    # -- Error cases --

    def test_invalid_no_scheme_raises(self) -> None:
        """URL without a scheme raises RuntimeError."""
        with pytest.raises(RuntimeError, match="invalid agent base_url"):
            resolve_base_url("not-a-url")

    def test_empty_raises(self) -> None:
        """Empty string raises RuntimeError."""
        with pytest.raises(RuntimeError, match="invalid agent base_url"):
            resolve_base_url("")
