"""Application safety tests with explicit test doubles, not inference evidence."""

import json
from pathlib import Path
import tempfile
import unittest

from memory_companion.model import suggest
from memory_companion.store import Store, Conflict


class ProposalConcurrencyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name) / "memory.sqlite")
        self.store.project("desk", "Desk")

    def save(self, content="Use concise answers.", revision=0):
        return self.store.put(scope="project:desk", kind="preference", key="answer-style",
                              content=content, source="Explicit test input", expected_revision=revision)

    def model(self, action=lambda: None, **overrides):
        class TestDouble:
            def complete(inner, messages, schema=None):
                action()
                return json.dumps({"save": True, "key": "answer-style",
                                   "content": "Use detailed answers.", "reason": "Explicit request.", **overrides})
        return TestDouble()

    def test_edit_during_generation_rejects_stale_suggestion(self):
        self.save()
        with self.assertRaises(Conflict):
            suggest(self.model(lambda: self.save("Use bullet points.", 1)), self.store,
                    "desk", "I prefer detailed answers.")
        self.assertEqual(self.store.list("desk")[0]["content"], "Use bullet points.")
        self.assertEqual(self.store.proposals(), [])

    def test_creation_during_generation_rejects_stale_suggestion(self):
        with self.assertRaises(Conflict):
            suggest(self.model(lambda: self.save("Use bullet points.")), self.store,
                    "desk", "I prefer detailed answers.")
        self.assertEqual(self.store.proposals(), [])

    def test_forget_and_recreate_same_revision_is_not_same_record(self):
        old = self.save()
        def replace():
            self.store.forget(old["id"], 1)
            self.save("Use bullet points.")
        with self.assertRaises(Conflict):
            suggest(self.model(replace), self.store, "desk", "I prefer detailed answers.")
        self.assertNotEqual(self.store.list("desk")[0]["id"], old["id"])
        self.assertEqual(self.store.proposals(), [])

    def test_unchanged_record_still_requires_review(self):
        original = self.save()
        proposal = suggest(self.model(), self.store, "desk", "I prefer detailed answers.")
        self.assertEqual(self.store.get(original["id"])["content"], original["content"])
        approved = self.store.review(proposal["id"], True)
        self.assertEqual(approved["content"], "Use detailed answers.")
        self.assertEqual(approved["revision"], 2)

    def test_no_save_response_still_validates_all_schema_fields(self):
        for invalid in ({"key": []}, {"content": {}}):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                suggest(self.model(save=False, **invalid), self.store, "desk", "Hello.")
        self.assertEqual(self.store.proposals(), [])
        self.assertEqual(self.store.list("desk"), [])


if __name__ == "__main__":
    unittest.main()
