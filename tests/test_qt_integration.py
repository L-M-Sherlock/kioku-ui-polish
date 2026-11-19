"""Optional real-Qt smoke checks; skipped when Anki/PyQt is unavailable."""
import importlib.util
import os
import types
import unittest
from concurrent.futures import Future
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    import aqt
    from aqt.qt import QApplication, QFont, QGridLayout, QMenu, QMenuBar, QPoint, QTableView, QToolButton, Qt, QVBoxLayout, QWidget
    from PyQt6.QtTest import QTest
except ImportError:
    aqt = None


@unittest.skipIf(aqt is None, "Anki and Qt are not installed")
class QtIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import anki.lang

        cls.app = QApplication.instance() or QApplication([])
        anki.lang.set_lang("en_US")
        spec = importlib.util.spec_from_file_location("kioku_ui_polish_qt_test", Path(__file__).resolve().parent.parent / "__init__.py")
        cls.plugin = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.plugin)

    @classmethod
    def tearDownClass(cls):
        for hook, fn in (
            (aqt.gui_hooks.webview_will_set_content, cls.plugin._style_web_content),
            (aqt.gui_hooks.top_toolbar_did_init_links, cls.plugin._add_toolbar_link),
            (aqt.gui_hooks.state_did_change, cls.plugin._update_toolbar_state),
            (aqt.gui_hooks.undo_state_did_change, cls.plugin._undo_state_changed),
            (aqt.gui_hooks.browser_will_show, cls.plugin._add_browser_columns),
            (aqt.gui_hooks.operation_did_execute, cls.plugin._after_operation),
        ):
            hook.remove(fn)

    def _columns_browser(self):
        from aqt.browser.table.table import Table

        browser = QWidget()
        grid = QGridLayout(browser)
        grid.addWidget(QWidget(browser), 0, 0)
        grid.addWidget(QWidget(browser), 0, 1)
        menubar = QMenuBar(browser)
        for title in ("Edit", "View", "Notes", "Cards", "Go", "Help"):
            menubar.addMenu(title)
        view = QTableView(browser)
        browser.form = types.SimpleNamespace(gridLayout=grid, tableView=view, menubar=menubar)
        mode = {"current": "cards"}
        columns = {"cards": ["front", "due", "deck"], "notes": ["front", "due", "deck"]}
        state = types.SimpleNamespace(column_label=lambda column: column, column_tooltip=lambda column: "")

        def toggle(key):
            active = columns[mode["current"]]
            if key in active:
                active.remove(key)
            else:
                active.append(key)

        model = types.SimpleNamespace(columns={"front": "Front", "due": "Due", "deck": "Deck"},
                                      active_column_index=lambda key: columns[mode["current"]].index(key)
                                      if key in columns[mode["current"]] else None,
                                      len_columns=lambda: len(columns[mode["current"]]),
                                      toggle_column=toggle)
        table = types.SimpleNamespace(_view=view, _state=state, _model=model, browser=browser,
                                      _set_column_sizes=lambda: None, _set_sort_indicator=lambda: None,
                                      _scroll_to_column=lambda column: None)
        table._on_column_toggled = lambda checked, key: Table._on_column_toggled(table, checked, key)
        browser.table = table
        return browser, menubar, grid, mode, columns

    def test_columns_menu_follows_help_without_extra_button(self):
        browser, menubar, grid, mode, columns = self._columns_browser()
        self.plugin._add_browser_columns(browser)
        menu = browser._kioku_ui_polish_columns
        self.assertEqual([action.text() for action in menubar.actions()],
                         ["Edit", "View", "Notes", "Cards", "Go", "Help", "Columns"])
        self.assertIs(menubar.actions()[-1].menu(), menu)
        self.assertEqual(grid.count(), 2)
        self.assertEqual(menubar.actions()[1].menu().actions(), [])
        browser.close()

    def test_compact_menubar_fits_then_restores_font_when_widened(self):
        window = QWidget()
        layout = QVBoxLayout(window)
        layout.setContentsMargins(0, 0, 0, 0)
        menubar = QMenuBar(window)
        layout.addWidget(menubar)
        font = QFont(menubar.font())
        font.setPointSizeF(15)
        menubar.setFont(font)
        for title in ("Edit", "View", "Notes", "Cards", "Go", "Help", "Columns"):
            menubar.addMenu(title)
        self.plugin._install_compact_menubar(menubar)
        window.resize(320, 100)
        window.show()
        self.app.processEvents()
        self.app.processEvents()
        extension = menubar.findChild(QToolButton, "qt_menubar_ext_button")
        self.assertLessEqual(menubar.sizeHint().width(), menubar.width())
        self.assertFalse(extension.isVisible())
        self.assertGreaterEqual(menubar.font().pointSizeF(), 11)
        window.resize(393, 100)
        self.app.processEvents()
        self.app.processEvents()
        self.assertLessEqual(menubar.sizeHint().width(), menubar.width())
        self.assertFalse(extension.isVisible())
        window.resize(700, 100)
        self.app.processEvents()
        self.app.processEvents()
        self.assertEqual(menubar.font().pointSizeF(), 15)
        window.close()

    def test_compact_menubar_supports_pixel_sized_fonts(self):
        window = QWidget()
        layout = QVBoxLayout(window)
        layout.setContentsMargins(0, 0, 0, 0)
        menubar = QMenuBar(window)
        layout.addWidget(menubar)
        font = QFont(menubar.font())
        font.setPixelSize(20)
        menubar.setFont(font)
        for title in ("Edit", "View", "Notes", "Cards", "Go", "Help", "Columns"):
            menubar.addMenu(title)
        self.plugin._install_compact_menubar(menubar)
        window.resize(320, 100)
        window.show()
        self.app.processEvents()
        self.app.processEvents()
        self.assertLessEqual(menubar.sizeHint().width(), menubar.width())
        self.assertGreaterEqual(menubar.font().pixelSize(), 15)
        window.resize(700, 100)
        self.app.processEvents()
        self.app.processEvents()
        self.assertEqual(menubar.font().pixelSize(), 20)
        window.close()

    def test_columns_menu_allows_multiple_toggles_in_both_modes(self):
        browser, menubar, grid, mode, columns = self._columns_browser()
        self.plugin._add_browser_columns(browser)
        menu = browser._kioku_ui_polish_columns
        seen = []
        hook = lambda _browser, column_menu: seen.append(column_menu)
        aqt.gui_hooks.browser_header_will_show_context_menu.append(hook)
        try:
            for current in ("cards", "notes"):
                mode["current"] = current
                menu.popup(QPoint(0, 0))
                self.app.processEvents()
                self.assertEqual([action.text() for action in menu.actions()], ["Front", "Due", "Deck"])
                for index in (1, 2):
                    action = menu.actions()[index]
                    self.assertTrue(action.isChecked())
                    QTest.mouseClick(menu, Qt.MouseButton.LeftButton,
                                     pos=menu.actionGeometry(action).center())
                    self.app.processEvents()
                    self.assertFalse(action.isChecked())
                    self.assertTrue(menu.isVisible())
                self.assertEqual(columns[current], ["front"])
                # Anki's last-column guard must retain the checkmark.
                with patch("aqt.browser.table.table.showInfo") as warning:
                    action = menu.actions()[0]
                    QTest.mouseClick(menu, Qt.MouseButton.LeftButton,
                                     pos=menu.actionGeometry(action).center())
                    self.app.processEvents()
                    self.assertTrue(action.isChecked())
                    self.assertEqual(columns[current], ["front"])
                    warning.assert_called_once()
                menu.close()
            self.assertEqual(seen, [menu, menu])
        finally:
            aqt.gui_hooks.browser_header_will_show_context_menu.remove(hook)
            browser.close()

    def test_more_menu_uses_reviewer_and_keeps_it_alive(self):
        parent = QWidget()
        web = QWidget(parent)
        web.resize(320, 44)
        parent.state = "review"
        parent.reviewer = types.SimpleNamespace(card=object())
        parent.reviewer._contextMenu = lambda: ["flag", "bury", "replay"]
        parent.reviewer._addMenuItems = lambda menu, rows: [menu.addAction(row) for row in rows]
        toolbar = types.SimpleNamespace(mw=parent, web=web)
        observed = []
        hook = lambda reviewer, menu: observed.append((reviewer, menu))
        aqt.gui_hooks.reviewer_will_show_context_menu.append(hook)
        try:
            self.plugin._review_more(toolbar)
            menu = parent._kioku_ui_polish_review_menu
            self.assertEqual([action.text() for action in menu.actions()], ["flag", "bury", "replay"])
            self.assertEqual(observed, [(parent.reviewer, menu)])
            menu.close()
            self.plugin._review_more(toolbar)
            self.assertIs(parent._kioku_ui_polish_review_menu, menu)
            self.assertEqual([action.text() for action in menu.actions()], ["flag", "bury", "replay"])
            menu.close()
        finally:
            aqt.gui_hooks.reviewer_will_show_context_menu.remove(hook)
            parent.close()

    def test_undo_refreshes_after_anki_defers_due_to_tooltip_focus(self):
        from aqt.main import AnkiQt
        from aqt.qt import Qt
        from aqt.reviewer import Reviewer

        parent = QWidget()
        parent.state = "review"
        events = []
        changes = types.SimpleNamespace(study_queues=True, note_text=False, card=False,
                                        mtime=False, notetype=False)
        result = types.SimpleNamespace(operation="Answer Card", changes=changes)
        parent.col = types.SimpleNamespace(undo=lambda: result, op_made_changes=lambda _changes: False)
        parent.undo_actions_info = lambda: types.SimpleNamespace(can_undo=True)
        parent._increase_background_ops = lambda: None
        parent._decrease_background_ops = lambda: None
        parent.update_undo_actions = lambda: None
        parent.fade_out_webview = lambda: events.append("fade")
        reviewer = types.SimpleNamespace(_refresh_needed=None)
        reviewer.op_executed = types.MethodType(Reviewer.op_executed, reviewer)

        def refresh():
            events.append("refresh")
            reviewer._refresh_needed = None

        reviewer.refresh_if_needed = refresh
        parent.reviewer = reviewer

        def run_operation(op, on_done, *, parent):
            future = Future()
            future.set_result(op())
            on_done(future)

        parent.taskman = types.SimpleNamespace(with_progress=run_operation)

        class TooltipWindow:
            def window(self): return self
            def isVisible(self): return True
            def windowType(self): return Qt.WindowType.ToolTip

        tooltip_window = TooltipWindow()

        class Focus:
            activeModalWidget = staticmethod(lambda: None)
            activePopupWidget = staticmethod(lambda: None)
            focusWidget = staticmethod(lambda: tooltip_window)
            activeWindow = staticmethod(lambda: None)

        main_handler = lambda changes, initiator: AnkiQt.on_operation_did_execute(parent, changes, initiator)
        hook = aqt.gui_hooks.operation_did_execute
        hook.remove(self.plugin._after_operation)
        hook.append(main_handler)
        hook.append(self.plugin._after_operation)
        try:
            with patch.object(aqt, "mw", parent), \
                 patch("aqt.main.current_window", return_value=tooltip_window), \
                 patch("aqt.qt.QApplication", Focus), \
                 patch("aqt.utils.tooltip", side_effect=lambda *args, **kwargs: events.append("tooltip")):
                self.plugin._undo(types.SimpleNamespace(mw=parent))
            self.assertEqual(events, ["tooltip", "fade", "refresh"])
            self.assertIsNone(reviewer._refresh_needed)
        finally:
            hook.remove(main_handler)
            parent.close()


if __name__ == "__main__":
    unittest.main()
