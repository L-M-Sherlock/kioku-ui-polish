"""Mobile-friendly review buttons and deck list for Kioku."""

from pathlib import Path

from aqt import gui_hooks
from aqt.deckbrowser import DeckBrowser
from aqt.reviewer import ReviewerBottomBar

_ROOT = Path(__file__).parent
_REVIEW_CSS = (_ROOT / "review.css").read_text(encoding="utf-8")
_DECK_CSS = (_ROOT / "decks.css").read_text(encoding="utf-8")
_DECK_JS = (_ROOT / "decks.js").read_text(encoding="utf-8")


def _style_web_content(web_content, context):
    if isinstance(context, ReviewerBottomBar):
        web_content.head += f"\n<style>{_REVIEW_CSS}</style>\n"
    elif isinstance(context, DeckBrowser):
        web_content.head += f"\n<style>{_DECK_CSS}</style>\n<script>{_DECK_JS}</script>\n"


gui_hooks.webview_will_set_content.append(_style_web_content)
