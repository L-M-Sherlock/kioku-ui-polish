"""Exercise toolbar hooks without requiring a running Anki collection."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


class TopToolbar:
    def __init__(self, toolbar):
        self.toolbar = toolbar


class DeckBrowser:
    pass


class ReviewerBottomBar:
    pass


class Web:
    def __init__(self):
        self.scripts = []
        self.resizes = 0

    def eval(self, script):
        self.scripts.append(script)

    def adjustHeightToFit(self):
        self.resizes += 1


class Toolbar:
    def __init__(self, mw):
        self.mw = mw
        self.web = Web()
        self.links = {}

    def create_link(self, cmd, label, callback, id=None):
        self.links[cmd] = callback
        return f'<a id="{id}">{label}</a>'


class ToolbarHooksTest(unittest.TestCase):
    def setUp(self):
        hooks = types.SimpleNamespace(webview_will_set_content=[], top_toolbar_did_init_links=[], state_did_change=[])
        self.aqt = types.ModuleType("aqt")
        self.aqt.gui_hooks = hooks
        self.aqt.mw = types.SimpleNamespace(state="deckBrowser", reviewer=types.SimpleNamespace(card=None))
        self.aqt.mw.toolbar = Toolbar(self.aqt.mw)
        self.aqt.mw.edits = 0

        def edit():
            self.aqt.mw.edits += 1

        self.aqt.mw.onEditCurrent = edit
        deck = types.ModuleType("aqt.deckbrowser")
        deck.DeckBrowser = DeckBrowser
        reviewer = types.ModuleType("aqt.reviewer")
        reviewer.ReviewerBottomBar = ReviewerBottomBar
        toolbar = types.ModuleType("aqt.toolbar")
        toolbar.TopToolbar = TopToolbar
        utils = types.ModuleType("aqt.utils")
        utils.tr = types.SimpleNamespace(studying_edit=lambda: "Edit")
        modules = {"aqt": self.aqt, "aqt.deckbrowser": deck, "aqt.reviewer": reviewer,
                   "aqt.toolbar": toolbar, "aqt.utils": utils}
        self.modules = patch.dict(sys.modules, modules)
        self.modules.start()
        spec = importlib.util.spec_from_file_location("kioku_ui_polish_test", Path(__file__).resolve().parent.parent / "__init__.py")
        self.plugin = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.plugin)
        self.hooks = hooks

    def tearDown(self):
        self.modules.stop()

    def test_review_link_edits_only_a_live_review_card(self):
        links = []
        toolbar = self.aqt.mw.toolbar
        self.hooks.top_toolbar_did_init_links[0](links, toolbar)
        self.assertIn('id="kioku-edit-current"', links[0])
        action = toolbar.links["kioku-edit-current"]
        action()
        self.aqt.mw.state = "review"
        action()  # no current card yet
        self.assertEqual(self.aqt.mw.edits, 0)
        self.aqt.mw.reviewer.card = object()
        action()
        self.assertEqual(self.aqt.mw.edits, 1)
        self.aqt.mw.state = "overview"
        action()
        self.assertEqual(self.aqt.mw.edits, 1)

    def test_state_changes_and_initial_toolbar_load(self):
        web = self.aqt.mw.toolbar.web
        hook = self.hooks.state_did_change[0]
        self.aqt.mw.state = "review"
        hook("review", "overview")
        self.assertIn('"kioku-review-toolbar", true', web.scripts[-1])
        self.aqt.mw.state = "deckBrowser"
        hook("overview", "review")  # an inner transition already changed state
        self.assertIn('"kioku-review-toolbar", false', web.scripts[-1])
        self.assertEqual(web.resizes, 2)
        html = types.SimpleNamespace(head="")
        self.hooks.webview_will_set_content[0](html, TopToolbar(self.aqt.mw.toolbar))
        self.assertIn('"kioku-review-toolbar", false', html.head)
        self.assertIn('#stats', html.head)
        self.assertIn('#sync', html.head)
        other = types.SimpleNamespace(head="")
        self.hooks.webview_will_set_content[0](other, object())
        self.assertEqual(other.head, "")


if __name__ == "__main__":
    unittest.main()
