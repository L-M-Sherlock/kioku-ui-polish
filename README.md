# Kioku UI Polish

A mobile-focused Anki add-on for [Kioku](https://github.com/krmanik/kioku). It makes the deck list and reviewer controls easier to use on narrow screens while keeping Anki's existing deck and review actions.

## Features

- An AnkiDroid-inspired deck list with larger rows, separate expand and options targets, and colored card counts.
- Larger, color-coded review buttons, including support for two-, three-, and four-button layouts and optional intervals.
- A neutral Show Answer button with readable card counts in light and dark modes.
- Changes apply at viewport widths up to 600 CSS pixels; wider windows keep their original layout.

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

The package is written to `dist/kioku_ui_polish.ankiaddon`. To publish a release, update `human_version` in `manifest.json`, commit it, and push the matching tag (for example, `v1.1.1`). GitHub Actions checks the tag against the manifest, builds the add-on, and attaches it to a GitHub Release.

## License

[AGPL-3.0-or-later](LICENSE).
