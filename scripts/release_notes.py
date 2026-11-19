"""Validate and print the curated notes for a release tag."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TAG_PATTERN = re.compile(r"v[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?\Z")
HEADING = "## What's new"


def load_notes(root: Path, tag: str) -> str:
    if not TAG_PATTERN.fullmatch(tag):
        raise ValueError(f"invalid release tag: {tag!r}")
    path = root / "release-notes" / f"{tag}.md"
    try:
        notes = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        raise ValueError(f"missing release notes: {path}") from None
    lines = notes.splitlines()
    has_content = any(line.strip() and not line.lstrip().startswith("#") for line in lines[1:])
    if not lines or lines[0].strip() != HEADING or not has_content:
        raise ValueError(f"{path} must start with {HEADING!r} and describe the changes")
    return notes + "\n"


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python3 scripts/release_notes.py v1.2.3", file=sys.stderr)
        return 2
    try:
        print(load_notes(ROOT, sys.argv[1]), end="")
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
