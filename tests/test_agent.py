import io
import json
from pathlib import Path
import tempfile
import unittest

from memory_companion.agent import run_agent
from memory_companion.model import Model
from memory_companion.store import Store


def call(name="recall_project_memory", arguments=None):
    return {"id": "synthetic-call", "type": "function", "function": {"name": name,
            "arguments": json.dumps({"question": "shell"} if arguments is None else arguments)}}


class Responses:
    def __init__(self, messages):
        self.messages = iter(messages)
        self.requests = []

    def open(self, request, timeout):
        self.requests.append(json.loads(request.data))
        return io.BytesIO(json.dumps({"choices": [{"message": next(self.messages)}]}).encode())


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.store = Store(Path(self.temporary.name) / "memory.sqlite")
        self.store.project("one", "One")
        self.store.project("two", "Two")
        self.store.put(scope="project:one", kind="preference", key="shell", content="PowerShell", source="synthetic")
        self.store.put(scope="project:two", kind="preference", key="shell", content="Bash", source="synthetic")
        self.model = Model(backend="compatible", url="http://127.0.0.1:1/v1", name="synthetic-test-double")

    def test_bounded_recall_preserves_store_and_scope(self):
        before = self.store.export()["memories"]
        self.model.opener = Responses([{"tool_calls": [call()], "content": None}, {"content": "Controlled test response."}])
        result = run_agent(self.model, self.store, "one", "Which shell?")
        self.assertEqual(result["turns"], 2)
        self.assertEqual(result["trace"][0]["project"], "one")
        supplied = self.model.opener.requests[1]["messages"][-1]["content"]
        self.assertIn("PowerShell", supplied)
        self.assertNotIn("Bash", supplied)
        self.assertEqual(self.store.export()["memories"], before)

    def test_unavailable_tool_is_rejected(self):
        self.model.opener = Responses([{"tool_calls": [call("execute_shell")]}])
        with self.assertRaisesRegex(ValueError, "unavailable tool"):
            run_agent(self.model, self.store, "one", "Do something")

    def test_tool_cannot_choose_another_project(self):
        self.model.opener = Responses([{"tool_calls": [call(arguments={"question": "shell", "project": "two"})]}])
        with self.assertRaisesRegex(ValueError, "allowed contract"):
            run_agent(self.model, self.store, "one", "Which shell?")

    def test_turn_limit_stops_repeated_recall(self):
        self.model.opener = Responses([{"tool_calls": [call()]}] * 3)
        with self.assertRaisesRegex(ValueError, "turn limit"):
            run_agent(self.model, self.store, "one", "Which shell?")
        self.assertEqual(len(self.model.opener.requests), 3)

    def test_malformed_call_and_oversized_batch_are_rejected(self):
        for calls in (["invalid"], [call(), call(), call()]):
            self.model.opener = Responses([{"tool_calls": calls}])
            with self.assertRaises(ValueError):
                run_agent(self.model, self.store, "one", "Which shell?")


if __name__ == "__main__":
    unittest.main()
