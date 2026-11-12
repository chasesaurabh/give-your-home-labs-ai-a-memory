"""A concurrent writer must not turn an export into mixed database states."""
from contextlib import contextmanager
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from memory_companion.store import Store


class ExportSnapshotTests(unittest.TestCase):
    def test_export_remains_importable_when_project_added_between_reads(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"source.sqlite"
            store = Store(path)
            store.project("first", "First")
            writer = Store(path)
            with store.db() as db:
                db.execute("PRAGMA journal_mode=WAL")
            original_db = store.db
            fired, errors = [], []

            @contextmanager
            def interleaved_reader():
                with original_db() as db:
                    def before_alias_read(sql):
                        if "SELECT * FROM aliases" in sql and not fired:
                            fired.append(True)
                            try:
                                writer.project("second", "Second", aliases=["new-name"])
                                writer.put(scope="project:second", kind="decision", key="storage",
                                           content="Use a local file.", source="Synthetic concurrent write")
                            except Exception as error:
                                errors.append(str(error))
                    db.set_trace_callback(before_alias_read)
                    yield db
            with patch.object(store, "db", interleaved_reader):
                document = store.export()
            self.assertEqual(errors, [])
            self.assertEqual(fired, [True])
            self.assertEqual(len(writer.projects()), 2, "Writer really committed during export")
            project_ids = {p["id"] for p in document["projects"]}
            self.assertTrue(all(a["project"] in project_ids for a in document["aliases"]),
                            "Export must not contain an alias whose project was omitted")
            self.assertTrue(all(r["scope"] == "global" or r["scope"][8:] in project_ids
                                for r in document["memories"]))
            destination = Store(Path(folder)/"roundtrip.sqlite")
            destination.import_data(document, apply=True)
            self.assertEqual(destination.projects(), document["projects"])


if __name__ == "__main__":
    unittest.main()
