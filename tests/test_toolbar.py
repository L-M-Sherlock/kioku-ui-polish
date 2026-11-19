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
    def __init__(self, reviewer):
        self.reviewer = reviewer


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
        hooks = types.SimpleNamespace(webview_will_set_content=[], webview_did_receive_js_message=[], top_toolbar_did_init_links=[], state_did_change=[],
                                      undo_state_did_change=[], browser_will_show=[], operation_did_execute=[],
                                      state_did_undo=lambda out: self.undo_events.append(out),
                                      reviewer_will_show_context_menu=lambda *args: None)
        self.aqt = types.ModuleType("aqt")
        self.aqt.gui_hooks = hooks
        self.aqt.mw = types.SimpleNamespace(state="deckBrowser", reviewer=types.SimpleNamespace(card=None))
        self.aqt.mw.toolbar = Toolbar(self.aqt.mw)
        self.aqt.mw.bottomWeb = Web()
        self.aqt.mw.edits = 0
        self.aqt.mw.undo_enabled = False
        self.undo_events = []
        self.tooltips = []
        self.warnings = []
        self.operations = []
        self.aqt.mw.undo_actions_info = lambda: types.SimpleNamespace(can_undo=self.aqt.mw.undo_enabled, undo_text="Undo review")

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
        utils.tr = types.SimpleNamespace(studying_edit=lambda: "Edit", studying_more=lambda: "More", undo_undo=lambda: "Undo",
                                         undo_action_undone=lambda action: action + " undone")
        utils.tooltip = lambda message, parent: self.tooltips.append((message, parent))
        utils.showWarning = lambda message, parent: self.warnings.append((message, parent))
        anki = types.ModuleType("anki")
        anki.__path__ = []
        errors = types.ModuleType("anki.errors")
        errors.UndoEmpty = type("UndoEmpty", (Exception,), {})
        ops = types.ModuleType("aqt.operations")
        test = self

        class CollectionOp:
            def __init__(self, parent, operation):
                self.parent, self.operation = parent, operation

            def success(self, callback):
                self.on_success = callback
                return self

            def failure(self, callback):
                self.on_failure = callback
                return self

            def run_in_background(self, *, initiator):
                self.initiator = initiator
                test.operations.append(self)

        ops.CollectionOp = CollectionOp
        modules = {"aqt": self.aqt, "aqt.deckbrowser": deck, "aqt.reviewer": reviewer,
                   "aqt.toolbar": toolbar, "aqt.utils": utils, "aqt.operations": ops,
                   "anki": anki, "anki.errors": errors}
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
        self.assertIn('"kioku-review-toolbar", true', web.scripts[-2])
        self.aqt.mw.state = "deckBrowser"
        hook("overview", "review")  # an inner transition already changed state
        self.assertIn('"kioku-review-toolbar", false', web.scripts[-2])
        self.assertEqual(web.resizes, 2)
        html = types.SimpleNamespace(head="")
        self.hooks.webview_will_set_content[0](html, TopToolbar(self.aqt.mw.toolbar))
        self.assertIn('"kioku-review-toolbar", false', html.head)
        self.assertIn('#stats', html.head)
        self.assertIn('#sync', html.head)
        other = types.SimpleNamespace(head="")
        self.hooks.webview_will_set_content[0](other, object())
        self.assertEqual(other.head, "")

    def test_undo_is_only_enabled_when_available_in_review(self):
        toolbar = self.aqt.mw.toolbar
        links = []
        self.hooks.top_toolbar_did_init_links[0](links, toolbar)
        action = toolbar.links["kioku-undo-current"]
        self.aqt.mw.state = "review"
        action()
        self.assertEqual(len(self.operations), 0)
        self.aqt.mw.undo_enabled = True
        self.hooks.undo_state_did_change[0](self.aqt.mw.undo_actions_info())
        self.assertIn('"kioku-can-undo", true', toolbar.web.scripts[-1])
        self.assertIn('"kioku-can-undo", true', self.aqt.mw.bottomWeb.scripts[-1])
        self.assertIn('aria-disabled', toolbar.web.scripts[-1])
        self.assertIn('Undo review', toolbar.web.scripts[-1])
        action()
        self.assertEqual(len(self.operations), 1)
        operation = self.operations[0]
        self.assertIs(operation.initiator, self.plugin._TOOLBAR_UNDO)
        result = object()
        col = types.SimpleNamespace(undo=lambda: result)
        self.assertIs(operation.operation(col), result)
        out = types.SimpleNamespace(operation="Answer Card")
        operation.on_success(out)
        self.assertEqual(self.undo_events, [out])
        self.assertEqual(self.tooltips, [("Answer Card undone", self.aqt.mw)])
        operation.on_failure(sys.modules["anki.errors"].UndoEmpty())
        self.assertEqual(self.warnings, [])
        operation.on_failure(ValueError("failure"))
        self.assertEqual(self.warnings, [("failure", self.aqt.mw)])
        self.aqt.mw.state = "overview"
        action()
        self.assertEqual(len(self.operations), 1)

    def test_bottom_undo_uses_existing_undo_and_respects_other_messages(self):
        context = ReviewerBottomBar(types.SimpleNamespace(mw=self.aqt.mw))
        hook = self.hooks.webview_did_receive_js_message[0]
        self.aqt.mw.state = "review"
        self.aqt.mw.undo_enabled = True
        self.assertEqual(hook((False, None), "other", context), (False, None))
        self.assertEqual(hook((True, "handled"), "kioku:bottom-undo", context), (True, "handled"))
        self.assertEqual(hook((False, None), "kioku:bottom-undo", object()), (False, None))
        self.assertEqual(hook((False, None), "kioku:bottom-undo", context), (True, None))
        self.assertEqual(len(self.operations), 1)
        self.assertIs(self.operations[0].initiator, self.plugin._TOOLBAR_UNDO)

    def test_bottom_content_initializes_undo_state(self):
        context = ReviewerBottomBar(types.SimpleNamespace(mw=self.aqt.mw))
        html = types.SimpleNamespace(head="")
        self.hooks.webview_will_set_content[0](html, context)
        self.assertIn('kioku-bottom-undo', html.head)
        self.assertIn('kioku:bottom-undo', html.head)
        self.assertIn('"kioku-can-undo", false', html.head)

    def test_toolbar_resize_requests_height_update_only_in_review(self):
        toolbar = self.aqt.mw.toolbar
        context = TopToolbar(toolbar)
        hook = self.hooks.webview_did_receive_js_message[0]
        self.aqt.mw.state = "review"
        self.assertEqual(hook((False, None), "kioku:toolbar-resize", context), (True, None))
        self.assertEqual(toolbar.web.resizes, 1)
        self.aqt.mw.state = "overview"
        self.assertEqual(hook((False, None), "kioku:toolbar-resize", context), (True, None))
        self.assertEqual(toolbar.web.resizes, 1)
        self.assertEqual(hook((False, None), "kioku:toolbar-resize", object()), (False, None))

    def test_only_our_undo_refreshes_a_deferred_reviewer(self):
        class Window:
            def __init__(self, kind):
                self.kind = kind

            def window(self):
                return self

            def isVisible(self):
                return True

            def windowType(self):
                return self.kind

        class App:
            modal = popup = focus = active = None
            activeModalWidget = staticmethod(lambda: App.modal)
            activePopupWidget = staticmethod(lambda: App.popup)
            focusWidget = staticmethod(lambda: App.focus)
            activeWindow = staticmethod(lambda: App.active)

        qt = types.ModuleType("aqt.qt")
        qt.QApplication = App
        qt.Qt = types.SimpleNamespace(WindowType=types.SimpleNamespace(ToolTip="tooltip"))
        reviewer = self.aqt.mw.reviewer
        reviewer._refresh_needed = True
        refreshes = []
        reviewer.refresh_if_needed = lambda: refreshes.append("refresh")
        self.aqt.mw.state = "review"
        hook = self.hooks.operation_did_execute[0]
        with patch.dict(sys.modules, {"aqt.qt": qt}):
            hook(object(), object())
            self.assertEqual(refreshes, [])
            App.focus = Window("tooltip")
            hook(object(), self.plugin._TOOLBAR_UNDO)
            self.assertEqual(refreshes, ["refresh"])
            App.focus = Window("other window")
            hook(object(), self.plugin._TOOLBAR_UNDO)
            App.active = self.aqt.mw
            hook(object(), self.plugin._TOOLBAR_UNDO)
            self.assertEqual(refreshes, ["refresh", "refresh"])
            App.active = None
            App.focus = None
            App.modal = object()
            hook(object(), self.plugin._TOOLBAR_UNDO)
            App.modal = None
            App.popup = object()
            hook(object(), self.plugin._TOOLBAR_UNDO)
            App.popup = None
            self.aqt.mw.state = "overview"
            hook(object(), self.plugin._TOOLBAR_UNDO)
        self.assertEqual(refreshes, ["refresh", "refresh"])

    def test_more_menu_uses_existing_reviewer_actions_and_hook(self):
        class Point:
            def __init__(self, x, y):
                self.x, self.y = x, y

        class Menu:
            def __init__(self, parent):
                self.parent = parent
                self.items = None
                self.position = None

            def popup(self, position):
                self.position = position

        qt = types.ModuleType("aqt.qt")
        qt.QMenu, qt.QPoint = Menu, Point
        utils = sys.modules["aqt.utils"]
        utils.qtMenuShortcutWorkaround = lambda menu: setattr(menu, "shortcuts_checked", True)
        seen = []
        self.hooks.reviewer_will_show_context_menu = lambda reviewer, menu: seen.append((reviewer, menu))
        reviewer = self.aqt.mw.reviewer
        reviewer.card = object()
        reviewer._contextMenu = lambda: ["existing actions"]
        reviewer._addMenuItems = lambda menu, rows: setattr(menu, "items", rows)
        toolbar = self.aqt.mw.toolbar
        toolbar.web.width = lambda: 320
        toolbar.web.height = lambda: 44
        toolbar.web.mapToGlobal = lambda point: (point.x, point.y)
        links = []
        self.hooks.top_toolbar_did_init_links[0](links, toolbar)
        self.aqt.mw.state = "review"
        with patch.dict(sys.modules, {"aqt.qt": qt}):
            toolbar.links["kioku-review-more"]()
        menu = self.aqt.mw._kioku_ui_polish_review_menu
        self.assertEqual(menu.items, ["existing actions"])
        self.assertEqual(menu.position, (160, 44))
        self.assertTrue(menu.shortcuts_checked)
        self.assertEqual(seen, [(reviewer, menu)])
        reviewer.card = None
        with patch.dict(sys.modules, {"aqt.qt": qt}):
            toolbar.links["kioku-review-more"]()
        self.assertIs(self.aqt.mw._kioku_ui_polish_review_menu, menu)


if __name__ == "__main__":
    unittest.main()
