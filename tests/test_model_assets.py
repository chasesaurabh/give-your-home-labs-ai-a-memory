"""Artifact verification must reject tampering and unsafe destinations."""
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
from model_assets import artifact_path, verify_file, verify_directory


class ModelArtifactTests(unittest.TestCase):
    def test_same_size_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "weights.bin"
            path.write_bytes(b"original")
            item = dict(path=path.name, bytes=8, hash_algorithm="sha256",
                        hash=hashlib.sha256(b"original").hexdigest())
            verify_file(path, item)
            path.write_bytes(b"modified")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                verify_file(path, item)

    def test_git_blob_hash_is_not_plain_file_sha1(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            payload = b'{"local":true}\n'
            path.write_bytes(payload)
            item = dict(path=path.name, bytes=len(payload), hash_algorithm="git_blob_sha1",
                        hash=hashlib.sha1(f"blob {len(payload)}\0".encode() + payload).hexdigest())
            verify_file(path, item)
            item["hash"] = hashlib.sha1(payload).hexdigest()
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                verify_file(path, item)

    def test_paths_cannot_escape_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            for name in ("../outside", "nested/../../outside", "/absolute", "C:/outside", "nested\\outside", "weights:stream"):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    artifact_path(directory, name)
            self.assertEqual(artifact_path(directory, "nested/config.json"),
                             Path(directory).resolve() / "nested" / "config.json")

    def test_directory_verification_requires_every_locked_file(self):
        with tempfile.TemporaryDirectory() as directory:
            config = dict(repository="fictional/test", revision="f" * 40,
                          files=[dict(path="missing", bytes=1, hash_algorithm="sha256", hash="0" * 64)])
            with self.assertRaisesRegex(ValueError, "Missing artifact"):
                verify_directory(directory, config)


if __name__ == "__main__":
    unittest.main()
