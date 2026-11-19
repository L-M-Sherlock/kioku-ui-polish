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
    from aqt.qt import QApplication, QGridLayout, QMenu, QTableView, QTimer, QWidget
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

    def test_columns_button_and_view_action_open_original_menu(self):
        browser = QWidget()
        grid = QGridLayout(browser)
        grid.addWidget(QWidget(browser), 0, 0)
        grid.addWidget(QWidget(browser), 0, 1)
        view = QTableView(browser)
        menu = QMenu(browser)
        browser.form = types.SimpleNamespace(gridLayout=grid, tableView=view, menuqt_accel_view=menu)
        called = []
        browser.table = types.SimpleNamespace(_on_header_context=lambda point: called.append((point.x(), point.y())))
        self.plugin._add_browser_columns(browser)
        action, button = browser._kioku_ui_polish_columns
        self.assertIs(menu.actions()[-1], action)
        self.assertEqual(button.minimumHeight(), 44)
        self.assertEqual(grid.indexOf(button), 2)
        button.click()
        action.trigger()
        self.assertEqual(called, [(0, view.horizontalHeader().height())] * 2)
        browser.close()

    def test_columns_menu_toggles_current_mode(self):
        from aqt.browser.table.table import Table

        browser = QWidget()
        grid = QGridLayout(browser)
        grid.addWidget(QWidget(browser), 0, 0)
        grid.addWidget(QWidget(browser), 0, 1)
        view = QTableView(browser)
        menu = QMenu(browser)
        browser.form = types.SimpleNamespace(gridLayout=grid, tableView=view, menuqt_accel_view=menu)
        mode = {"current": "cards"}
        columns = {"cards": ["front", "due"], "notes": ["front", "due"]}
        state = types.SimpleNamespace(column_label=lambda column: column, column_tooltip=lambda column: "")
        model = types.SimpleNamespace(columns={"front": "Front", "due": "Due"},
                                      active_column_index=lambda key: columns[mode["current"]].index(key)
                                      if key in columns[mode["current"]] else None,
                                      len_columns=lambda: len(columns[mode["current"]]),
                                      toggle_column=lambda key: columns[mode["current"]].remove(key))
        table = types.SimpleNamespace(_view=view, _state=state, _model=model, browser=browser,
                                      _set_column_sizes=lambda: None, _set_sort_indicator=lambda: None)
        table._on_column_toggled = lambda checked, key: Table._on_column_toggled(table, checked, key)
        table._on_header_context = lambda point: Table._on_header_context(table, point)
        browser.table = table
        self.plugin._add_browser_columns(browser)

        checked_before = []

        def select_due(_browser, column_menu):
            def choose():
                checked_before.append(column_menu.actions()[1].isChecked())
                column_menu.actions()[1].trigger()
                column_menu.close()
            QTimer.singleShot(0, choose)

        aqt.gui_hooks.browser_header_will_show_context_menu.append(select_due)
        try:
            browser._kioku_ui_polish_columns[1].click()
            self.assertEqual(columns, {"cards": ["front"], "notes": ["front", "due"]})
            mode["current"] = "notes"
            browser._kioku_ui_polish_columns[1].click()
            self.assertEqual(columns, {"cards": ["front"], "notes": ["front"]})
            self.assertEqual(checked_before, [True, True])
        finally:
            aqt.gui_hooks.browser_header_will_show_context_menu.remove(select_due)
            browser.close()

    def test_kioku_phone_layout_keeps_columns_button_clickable(self):
        try:
            from kioku.windows import _wrap_search_row
        except ImportError:
            self.skipTest("Kioku source is not on PYTHONPATH")
        browser = QWidget()
        grid = QGridLayout(browser)
        grid.addWidget(QWidget(browser), 0, 0)
        grid.addWidget(QWidget(browser), 0, 1)
        view = QTableView(browser)
        menu = QMenu(browser)
        browser.form = types.SimpleNamespace(gridLayout=grid, tableView=view, menuqt_accel_view=menu)
        calls = []
        browser.table = types.SimpleNamespace(_on_header_context=lambda point: calls.append(point.y()))
        self.plugin._add_browser_columns(browser)
        button = browser._kioku_ui_polish_columns[1]
        _wrap_search_row(browser)
        row = grid.itemAtPosition(1, 0).layout()
        self.assertIs(row.itemAt(0).widget(), button)
        button.click()
        self.assertEqual(calls, [view.horizontalHeader().height()])
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
