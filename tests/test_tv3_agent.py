"""TV3 unit tests: no model download, external API or shared artifact writes."""

import sys
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from core.config import load_settings
from retrieval.agent import _answer_text, build_agent, run_agent_question


class AgentTests(unittest.TestCase):
    def test_provider_text_blocks_are_plain_text(self):
        message = SimpleNamespace(
            content=[
                {"type": "text", "text": "Answer"},
                {"type": "reasoning", "text": "do not expose"},
                {"type": "output_text", "text": "[paper-id]"},
            ]
        )
        self.assertEqual(_answer_text(message), "Answer\n[paper-id]")

    def test_plain_text_unchanged(self):
        self.assertEqual(_answer_text(SimpleNamespace(content="hello")), "hello")

    def test_blank_question_never_calls_model(self):
        agent = Mock()
        with self.assertRaises(ValueError):
            run_agent_question(agent, "  ")
        agent.invoke.assert_not_called()

    def test_graph_has_recursion_bound(self):
        agent = Mock()
        agent.invoke.return_value = {"messages": [SimpleNamespace(content="answer")]}
        self.assertEqual(run_agent_question(agent, "question"), "answer")
        self.assertEqual(agent.invoke.call_args.kwargs["config"]["recursion_limit"], 12)

    def test_no_messages_returns_empty(self):
        agent = Mock()
        agent.invoke.return_value = {"messages": []}
        self.assertEqual(run_agent_question(agent, "question"), "")

    def test_mock_llm_is_not_reported_as_real_tool_demo(self):
        settings = replace(load_settings(), llm_provider="mock")
        with self.assertRaisesRegex(ValueError, "cannot call tools"):
            build_agent(settings, Mock())

    def test_tools_use_real_index_contract_and_bound_top_k(self):
        settings = replace(load_settings(), llm_provider="gemini")
        index = Mock()
        index.documents = [{"paper_id": "paper-1"}]
        index.search.return_value = [
            SimpleNamespace(
                paper_id="paper-1", title="Title", score=0.8, content="Summary"
            )
        ]
        index.lookup.return_value = None
        with (
            patch("retrieval.agent.build_llm"),
            patch("retrieval.agent.create_agent") as create,
        ):
            build_agent(settings, index)
            tools = {t.name: t for t in create.call_args.kwargs["tools"]}
            answer = tools["semantic_search_papers"].invoke(
                {"query": "topic", "top_k": 999}
            )
            self.assertIn("paper-1", answer)
            index.search.assert_called_once_with("topic", top_k=1)
            missing = tools["lookup_paper"].invoke({"paper_id_or_title": "absent"})
            self.assertEqual(missing, "No exact paper match found.")
            before = index.search.call_count
            tools["semantic_search_papers"].invoke({"query": "", "top_k": 0})
            self.assertEqual(index.search.call_count, before)


if __name__ == "__main__":
    unittest.main()
