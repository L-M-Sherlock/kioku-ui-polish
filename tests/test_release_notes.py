"""Check that release notes are selected and validated before publishing."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "release_notes", Path(__file__).resolve().parent.parent / "scripts" / "release_notes.py"
)
release_notes = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release_notes)


class ReleaseNotesTest(unittest.TestCase):
    def test_selects_notes_for_exact_tag(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "release-notes"
            folder.mkdir()
            (folder / "v1.2.3.md").write_text("## What's new\n\n- A real change.\n", encoding="utf-8")
            self.assertEqual(release_notes.load_notes(root, "v1.2.3"), "## What's new\n\n- A real change.\n")
            with self.assertRaisesRegex(ValueError, "missing release notes"):
                release_notes.load_notes(root, "v1.2.4")

    def test_rejects_empty_or_invalid_notes_and_unsafe_tag(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "release-notes"
            folder.mkdir()
            path = folder / "v1.2.3.md"
            for text in ("", "## What's new\n\n", "## What's new\n\n## Details", "## Changes\n\n- Fixed something"):
                path.write_text(text, encoding="utf-8")
                with self.subTest(text=text), self.assertRaisesRegex(ValueError, "must start"):
                    release_notes.load_notes(root, "v1.2.3")
            with self.assertRaisesRegex(ValueError, "invalid release tag"):
                release_notes.load_notes(root, "v1.2.3/../../outside")


if __name__ == "__main__":
    unittest.main()
