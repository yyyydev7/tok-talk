import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from . import build_if_changed as builder


class BuildIfChangedTest(unittest.TestCase):
    def test_reuse_refresh_and_atomic_replacement(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            pdf = root / "NIOSH.pdf"
            pdf.write_bytes(b"test")
            content = {"value": "first"}
            calls = {"collect": 0, "index": 0}

            async def collect(args):
                calls["collect"] += 1
                records = [
                    {"cas_no": cas, "source": source, "content": content["value"],
                     "retrieved_at": str(calls["collect"])}
                    for cas in builder.CHEMICALS for source in ("KOSHA", "NIOSH PDF")
                ]
                status = {cas: {
                    "kosha": {str(n): {"status": "ok"} for n in builder.SECTIONS},
                    "niosh_pdf": {"status": "ok"},
                } for cas in builder.CHEMICALS}
                Path(args.output).write_text(json.dumps({"records": records, "status": status}))

            def index(args):
                calls["index"] += 1
                path = Path(args.output)
                path.mkdir()
                (path / "index.faiss").write_bytes(b"faiss")
                (path / "index.pkl").write_bytes(b"pickle")
                (path / "config.json").write_text(json.dumps(builder.INDEX_CONFIG))

            with patch.object(builder, "input_fingerprint", return_value="inputs-v1"), \
                 patch.object(builder, "collect", collect), patch.object(builder, "index", index):
                self.assertEqual(builder.build_if_changed(root, pdf, 24), "rebuilt")
                current = root / "indexes/current"
                first = current.resolve()
                self.assertTrue(current.is_symlink())
                self.assertEqual(builder.build_if_changed(root, pdf, 24), "reused")
                self.assertEqual(calls, {"collect": 1, "index": 1})

                self.assertEqual(builder.build_if_changed(root, pdf, 24, True), "unchanged")
                self.assertEqual(current.resolve(), first)
                self.assertEqual(calls, {"collect": 2, "index": 1})

                content["value"] = "changed"
                self.assertEqual(builder.build_if_changed(root, pdf, 24, True), "rebuilt")
                self.assertNotEqual(current.resolve(), first)
                self.assertEqual(calls, {"collect": 3, "index": 2})

                second = current.resolve()
                content["value"] = "cannot embed"
                with patch.object(builder, "index", side_effect=RuntimeError("embedding failed")):
                    self.assertEqual(builder.build_if_changed(root, pdf, 24, True), "stale")
                self.assertEqual(current.resolve(), second)

    def test_failed_refresh_preserves_existing_index(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            pdf = root / "NIOSH.pdf"
            pdf.write_bytes(b"test")
            current = root / "indexes/current"
            current.mkdir(parents=True)
            (current / "index.faiss").write_bytes(b"faiss")
            (current / "index.pkl").write_bytes(b"pickle")
            (current / "config.json").write_text(json.dumps(builder.INDEX_CONFIG))
            (current / "manifest.json").write_text(json.dumps({"input_fingerprint": "inputs-v1"}))

            async def fail(_args):
                raise RuntimeError("API unavailable")

            with patch.object(builder, "input_fingerprint", return_value="inputs-v1"), \
                 patch.object(builder, "collect", fail):
                self.assertEqual(builder.build_if_changed(root, pdf, 24, True), "stale")
            self.assertEqual((current / "index.faiss").read_bytes(), b"faiss")

    def test_incomplete_collection_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "KOSHA 수집 항목이 불완전"):
            builder.validate_collection({"records": [], "status": {}})


if __name__ == "__main__":
    unittest.main()
