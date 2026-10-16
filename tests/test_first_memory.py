"""Acceptance checks use a fresh process for every operation."""

import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest


EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "01_first_memory.py"


class FirstMemoryTests(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory()
        self.addCleanup(self.workspace.cleanup)
        self.database = Path(self.workspace.name) / "memory.sqlite"

    def operation(self, action, scope="project:reading-desk", key="shell", value=None):
        command = [sys.executable, str(EXAMPLE), "--db", str(self.database), action,
                   "--scope", scope, "--key", key]
        if value is not None:
            command.extend(["--value", value])
        return subprocess.run(command, capture_output=True, text=True, check=False)

    def result(self, *args, **kwargs):
        process = self.operation(*args, **kwargs)
        self.assertEqual(process.returncode, 0, process.stderr)
        return json.loads(process.stdout)

    def test_preference_survives_process_restart(self):
        self.result("save", value="PowerShell")
        self.assertEqual(self.result("get")["value"], "PowerShell")

    def test_same_key_in_another_project_does_not_leak(self):
        self.result("save", value="PowerShell")
        self.assertIsNone(self.result("get", scope="project:other")["value"])
        self.result("save", scope="project:other", value="Bash")
        self.assertEqual(self.result("get")["value"], "PowerShell")
        self.assertEqual(self.result("get", scope="project:other")["value"], "Bash")

    def test_replacement_keeps_one_active_record(self):
        self.result("save", value="PowerShell")
        self.result("save", value="Bash")
        self.assertEqual(self.result("get")["value"], "Bash")
        connection = sqlite3.connect(self.database)
        try:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM memories").fetchone()[0], 1)
        finally:
            connection.close()

    def test_forget_removes_from_future_lookup(self):
        self.result("save", value="PowerShell")
        self.result("forget")
        self.assertIsNone(self.result("get")["value"])

    def test_sql_like_text_is_stored_as_data(self):
        value = "'); DROP TABLE memories; --"
        self.result("save", value=value)
        self.assertEqual(self.result("get")["value"], value)

    def test_invalid_save_does_not_replace_existing_value(self):
        self.result("save", value="PowerShell")
        self.assertNotEqual(self.operation("save", value=" ").returncode, 0)
        self.assertEqual(self.result("get")["value"], "PowerShell")


if __name__ == "__main__":
    unittest.main()
