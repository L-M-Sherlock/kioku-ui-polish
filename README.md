# Kioku UI Polish

A mobile-focused Anki add-on for [Kioku](https://github.com/krmanik/kioku). It makes the deck list and reviewer controls easier to use on narrow screens while keeping Anki's existing deck and review actions.

## Features

- An AnkiDroid-inspired deck list with larger rows, separate expand and options targets, and colored card counts.
- Compact indentation for deeply nested decks in narrow phone and iPad Split View windows.
- In narrow review windows, the top toolbar shows Edit, Undo, and More. In wider windows, Stats and Sync remain at the top, while Edit, More, and Undo appear beside the bottom review controls. Undo follows Anki's undo state; More opens Anki's existing review actions.
- Choose Browser columns from a dedicated Columns menu, without a mouse or repeated trips through the View menu.
- Larger, color-coded review buttons, including support for two-, three-, and four-button layouts and optional intervals.
- A neutral Show Answer button with readable card counts in light and dark modes.
- The review controls adapt to the available viewport width: the bottom side controls appear at 584 CSS pixels and above, and the top review shortcuts appear below that width. The deck list styling applies at all widths.

## Install

1. Download `kioku_ui_polish.ankiaddon` from the [latest release](https://github.com/L-M-Sherlock/kioku-ui-polish/releases/latest).
2. In Kioku, open **Tools → Add-ons → Install from file…** and select the file.
3. Restart Kioku.

This package keeps the installation ID of the earlier **Kioku Touch Review Buttons** add-on, so installing it replaces that version. Disable or remove it in **Tools → Add-ons**.

The add-on uses Anki's desktop add-on interface and was developed against Kioku's Anki 26.09.4. WebKit layout and simulated clicks have been checked; full device testing across versions is still needed. Other add-ons that change the deck list or review buttons may affect the layout.

## Build

Requires Python 3.9 or newer; no third-party packages are needed.

```sh
python3 scripts/build.py
```

The package is written to `dist/kioku_ui_polish.ankiaddon`. To publish a release, update `human_version` in `manifest.json` and add `release-notes/v1.2.3.md` for that version. Start the file with `## What's new` and describe the user-visible changes. Commit both files and push the matching tag (for example, `v1.2.3`). GitHub Actions validates the tag and notes, builds the add-on, and publishes the curated notes before GitHub's generated changelog. Missing or empty notes stop the release.

On macOS, `python3 tests/verify_webkit_decks.py /path/to/kioku` and `python3 tests/verify_webkit_review.py /path/to/kioku` check synthetic pages in WebKit using that Kioku checkout's phone CSS. They require Swift and do not replace testing in Kioku on a device.

## License

[AGPL-3.0-or-later](LICENSE).
