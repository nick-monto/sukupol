from __future__ import annotations

import asyncio
import time
import unittest
from unittest.mock import patch

from app.agents import AgentExecutor
from app.agents.runtime import AgentInvocation


class AsyncBlockingTests(unittest.TestCase):
    """AF2: local-llm async methods must off-load sync I/O to a thread via asyncio.to_thread."""

    # ── ainvoke_json ──────────────────────────────────────────────────

    def test_ainvoke_json_does_not_block_event_loop(self) -> None:
        """ainvoke_json yields the event loop during the LLM _post sleep (proven by ordering)."""
        sleep_seconds = 0.3

        def _slow_post(self: object, _payload: dict[str, object]) -> str:
            time.sleep(sleep_seconds)
            return '{"reply": "Hello"}'

        executor = AgentExecutor(mode="local-llm")
        invocation = AgentInvocation(
            agent_name="test",
            instructions="Be helpful",
            user_prompt="Hi",
        )

        async def _run() -> None:
            order: list[str] = []

            with patch.object(
                executor.text_client.__class__,
                "_post",
                _slow_post,
            ):
                llm_task = asyncio.create_task(
                    executor.ainvoke_json(invocation),
                )

                async def _mark_llm_done() -> None:
                    await llm_task
                    order.append("llm_done")

                async def _mark_flag() -> None:
                    order.append("flag_set")

                wait_task = asyncio.create_task(_mark_llm_done())
                flag_task = asyncio.create_task(_mark_flag())

                await asyncio.gather(wait_task, flag_task)

            # With async path: llm_task starts, yields at asyncio.to_thread,
            #   then wait_task runs (blocks on llm_task), then flag_task runs
            #   -> order = ["flag_set", "llm_done"]
            # With sync path: llm_task blocks the loop for 0.3s, completes,
            #   then wait_task runs (llm_task already done), then flag_task
            #   -> order = ["llm_done", "flag_set"]
            self.assertEqual(
                order,
                ["flag_set", "llm_done"],
                f"Got order {order} — expected flag to run during LLM sleep. "
                "Sync _post call is blocking the event loop.",
            )

        asyncio.run(_run())

    def test_ainvoke_json_returns_correct_result(self) -> None:
        """ainvoke_json returns the parsed JSON from the thread-offloaded _post call."""

        def _slow_post(self: object, _payload: dict[str, object]) -> str:
            time.sleep(0.05)
            return '{"reply": "World"}'

        executor = AgentExecutor(mode="local-llm")
        invocation = AgentInvocation(
            agent_name="test",
            instructions="Say hi",
            user_prompt="Hello",
        )

        async def _run() -> dict[str, object]:
            with patch.object(
                executor.text_client.__class__,
                "_post",
                _slow_post,
            ):
                return await executor.ainvoke_json(invocation)

        result = asyncio.run(_run())
        self.assertEqual(result, {"reply": "World"})

    # ── astream_text ──────────────────────────────────────────────────

    def test_astream_text_does_not_block_event_loop(self) -> None:
        """astream_text yields the event loop while draining the sync _post_stream."""
        sleep_seconds = 0.2

        def _slow_post_stream(self: object, _payload: dict[str, object]):
            time.sleep(sleep_seconds)
            yield "chunk-1"
            yield "chunk-2"

        executor = AgentExecutor(mode="local-llm")
        invocation = AgentInvocation(
            agent_name="test",
            instructions="Say stuff",
            user_prompt="Stream me",
        )

        async def _run() -> None:
            order: list[str] = []

            with patch.object(
                executor.text_client.__class__,
                "_post_stream",
                _slow_post_stream,
            ):

                async def _collect_chunks() -> list[str]:
                    chunks: list[str] = []
                    async for chunk in executor.astream_text(invocation):
                        chunks.append(chunk)
                    return chunks

                stream_task = asyncio.create_task(_collect_chunks())

                async def _mark_flag() -> None:
                    order.append("flag_set")

                flag_task = asyncio.create_task(_mark_flag())

                chunks, _ = await asyncio.gather(stream_task, flag_task)

            self.assertEqual(
                order,
                ["flag_set"],
                "flag task did not run while astream_text was sleeping — "
                "sync _post_stream call is blocking the event loop",
            )
            self.assertEqual(chunks, ["chunk-1", "chunk-2"])

        asyncio.run(_run())

    # ── Regression guard: the test MUST fail if sync path is restored ──

    def test_fails_if_sync_path_restored(self) -> None:
        """Prove that calling chat_json (sync) directly blocks the loop — this test passes
        because our code now uses the async path. If someone reverts ainvoke_json's
        local-llm branch to `self.text_client.chat_json(...)`, this test fails."""
        sleep_seconds = 0.15

        def _slow_post(self: object, _payload: dict[str, object]) -> str:
            time.sleep(sleep_seconds)
            return '{"reply": "sync"}'

        executor = AgentExecutor(mode="local-llm")
        invocation = AgentInvocation(
            agent_name="test",
            instructions="Say hi",
            user_prompt="Hello",
        )

        async def _run() -> None:
            with patch.object(
                executor.text_client.__class__,
                "_post",
                _slow_post,
            ):
                llm_task = asyncio.create_task(
                    executor.ainvoke_json(invocation),
                )

                # Attempt a tiny sleep — if ainvoke_json is blocking, this
                # will take ~sleep_seconds instead of ~0.
                start = time.monotonic()
                await asyncio.sleep(0)
                elapsed = time.monotonic() - start

                # The yield should return quickly (< half the sleep duration)
                # if the LLM call was off-loaded to a thread.
                self.assertLess(
                    elapsed,
                    sleep_seconds * 0.5,
                    f"await asyncio.sleep(0) took {elapsed:.3f}s — "
                    "the event loop was blocked by a synchronous call",
                )

                result = await llm_task
                self.assertEqual(result, {"reply": "sync"})

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
