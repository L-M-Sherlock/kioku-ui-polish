"""Build an Anki add-on archive; optionally verify its release tag."""
import json
import os
import py_compile
import tempfile
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parent.parent
FILES = ("__init__.py", "manifest.json", "review.css", "decks.css", "decks.js")
manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
if not manifest.get("package") or not manifest.get("name") or not manifest.get("human_version"):
    raise SystemExit("manifest.json must include package, name and human_version")
tag = os.environ.get("RELEASE_TAG")
if tag and tag != "v" + manifest["human_version"]:
    raise SystemExit(f"release tag {tag!r} does not match manifest version {manifest['human_version']!r}")
with tempfile.TemporaryDirectory() as tmp:
    py_compile.compile(str(ROOT / "__init__.py"), cfile=str(Path(tmp) / "addon.pyc"), doraise=True)
out = ROOT / "dist" / "kioku_ui_polish.ankiaddon"
out.parent.mkdir(exist_ok=True)
with ZipFile(out, "w", ZIP_DEFLATED) as archive:
    for name in FILES:
        archive.write(ROOT / name, name)
with ZipFile(out) as archive:
    if set(archive.namelist()) != set(FILES) or archive.testzip():
        raise SystemExit("invalid add-on archive")
    for name in FILES:
        if archive.read(name) != (ROOT / name).read_bytes():
            raise SystemExit(f"archive content mismatch: {name}")
print(out)
