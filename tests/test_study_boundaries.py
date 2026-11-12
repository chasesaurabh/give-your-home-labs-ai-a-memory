"""Verify study controls do not leak answer keys or disallowed memory into prompts."""
from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

path = Path(__file__).resolve().parents[1]/"examples/memory_study.py"
spec = importlib.util.spec_from_file_location("memory_study", path)
study = importlib.util.module_from_spec(spec)
spec.loader.exec_module(study)


class StudyBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        target = Path(cls.temp.name)/"pack"
        with redirect_stdout(io.StringIO()):
            study.prepare(target)
        cls.requests = json.loads((target/"prepared.json").read_text(encoding="utf-8"))["requests"]

    def request(self, case, condition):
        return next(r for r in self.requests if r["case_id"] == case and r["condition"] == condition)

    def test_no_memory_control_contains_no_answer_records(self):
        for r in self.requests:
            if r["condition"] == "none":
                self.assertEqual(r["selection"]["records"], [])
                self.assertTrue(r["messages"][1]["content"].endswith("[]"))
                self.assertNotIn("rubric", json.dumps(r["messages"]))

    def test_scope_and_deleted_values_never_reach_any_request(self):
        for r in self.requests:
            messages = json.dumps(r["messages"])
            self.assertNotIn("ORCHID-PRIVATE", messages)
            self.assertNotIn("drawer-violet", messages)
            self.assertNotIn("endpoint-copper", messages)
        records = self.request("scope-01", "selected")["selection"]["records"]
        self.assertEqual([r["scope"] for r in records], ["project:desk"])
        self.assertIn("PowerShell", records[0]["content"])

    def test_oracle_control_can_expose_a_real_selection_miss(self):
        selected = self.request("paraphrase-04", "selected")
        oracle = self.request("paraphrase-04", "oracle")
        self.assertEqual(selected["selected_ids"], [])
        self.assertEqual(oracle["selected_ids"], oracle["required_ids"])
        self.assertIn("seventeen minutes", oracle["messages"][1]["content"])
        self.assertNotIn("seventeen minutes", selected["messages"][1]["content"])


if __name__ == "__main__":
    unittest.main()
