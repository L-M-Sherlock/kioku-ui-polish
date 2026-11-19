"""Mobile-friendly review buttons and deck list for Kioku."""

from pathlib import Path

import aqt
from aqt import gui_hooks
from aqt.deckbrowser import DeckBrowser
from aqt.reviewer import ReviewerBottomBar
from aqt.toolbar import TopToolbar
from aqt.utils import tr

_ROOT = Path(__file__).parent
_REVIEW_CSS = (_ROOT / "review.css").read_text(encoding="utf-8")
_DECK_CSS = (_ROOT / "decks.css").read_text(encoding="utf-8")
_DECK_JS = (_ROOT / "decks.js").read_text(encoding="utf-8")
_TOOLBAR_CSS = """
#kioku-edit-current { display: none; }
html.kioku-review-toolbar #stats, html.kioku-review-toolbar #sync { display: none; }
html.kioku-review-toolbar #kioku-edit-current { display: inline-block; }
"""


def _edit_current(toolbar):
    mw = toolbar.mw
    if mw.state == "review" and mw.reviewer.card is not None:
        mw.onEditCurrent()


def _add_toolbar_link(links, toolbar):
    links.append(toolbar.create_link(
        "kioku-edit-current", tr.studying_edit(), lambda: _edit_current(toolbar),
        id="kioku-edit-current",
    ))


def _update_toolbar_state(_new_state, _old_state):
    # Read the actual state: a state transition can itself trigger another one.
    mw = aqt.mw
    on = "true" if mw.state == "review" else "false"
    web = mw.toolbar.web
    web.eval(f'document.documentElement.classList.toggle("kioku-review-toolbar", {on});')
    web.adjustHeightToFit()


def _style_web_content(web_content, context):
    if isinstance(context, ReviewerBottomBar):
        web_content.head += f"\n<style>{_REVIEW_CSS}</style>\n"
    elif isinstance(context, DeckBrowser):
        web_content.head += f"\n<style>{_DECK_CSS}</style>\n<script>{_DECK_JS}</script>\n"
    elif isinstance(context, TopToolbar):
        on = "true" if getattr(context.toolbar.mw, "state", None) == "review" else "false"
        web_content.head += (
            f"\n<style>{_TOOLBAR_CSS}</style>\n"
            f'<script>document.documentElement.classList.toggle("kioku-review-toolbar", {on});</script>\n'
        )


gui_hooks.webview_will_set_content.append(_style_web_content)
gui_hooks.top_toolbar_did_init_links.append(_add_toolbar_link)
gui_hooks.state_did_change.append(_update_toolbar_state)
