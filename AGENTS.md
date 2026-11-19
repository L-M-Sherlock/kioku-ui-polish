# Repository Guidelines

## Project Structure & Module Organization

Kioku UI Polish is a mobile-focused Anki add-on. `__init__.py` registers Anki hooks and loads the UI assets. `decks.css` and `decks.js` control the deck list; `review.css` styles reviewer controls. `manifest.json` contains the add-on identity and version. `tests/` holds Python unit tests, `scripts/build.py` packages the add-on, and `.github/workflows/release.yml` runs checks and publishes releases. Generated packages live in the ignored `dist/` directory.

## Build, Test, and Development Commands

- `python3 -m unittest discover -s tests -v` runs the toolbar hook tests without a running Anki collection.
- `python3 scripts/build.py` checks the manifest and Python syntax, then builds and verifies `dist/kioku_ui_polish.ankiaddon`.
- `RELEASE_TAG=v1.1.3 python3 scripts/build.py` also verifies that the tag matches `human_version` in `manifest.json`.

Python 3.9 or newer is required; these commands need no third-party packages. Install the generated package through Kioku’s **Tools → Add-ons → Install from file**, then restart Kioku.

## Coding Style & Naming Conventions

Use four-space indentation in Python, JavaScript, and CSS. Follow existing conventions: `snake_case` for Python functions and test files, descriptive JavaScript names, and `kioku-` prefixes for add-on-specific DOM identifiers. Keep hooks scoped to the relevant Anki context and preserve existing deck and review commands. No formatter or linter is configured.

## Testing Guidelines

Add focused `unittest` cases to `tests/test_*.py` for behavior that can be verified without Anki. Run the full unit suite and package build before submitting changes. For visual or touch changes, inspect narrow and wide layouts, light and dark themes where relevant, and test in Kioku on a device or simulator when available; report any untested scenarios. No coverage threshold is configured.

## Commit & Pull Request Guidelines

Use short, imperative commit subjects, following history such as `Add edit current card to review toolbar`. Describe the user-visible change and validation in pull requests; link relevant issues and include screenshots for layout changes.

## Releases

Update `human_version` in `manifest.json`, commit the change, and push a matching `v` tag such as `v1.1.3`. GitHub Actions validates the version, builds the archive, and attaches it to a release. Keep the existing `package` value so upgrades replace earlier installations.
