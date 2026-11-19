"""Mobile-friendly review buttons and deck list for Kioku."""

import json
import sys
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
_TOOLBAR_UNDO = object()
_TOOLBAR_CSS = """
#kioku-edit-current, #kioku-undo-current, #kioku-review-more { display: none; }
html.kioku-review-toolbar #stats, html.kioku-review-toolbar #sync { display: none; }
html.kioku-review-toolbar #kioku-edit-current,
html.kioku-review-toolbar #kioku-undo-current,
html.kioku-review-toolbar #kioku-review-more { display: inline-block; }
#kioku-undo-current { opacity: 0.4; pointer-events: none; }
html.kioku-can-undo #kioku-undo-current { opacity: 1; pointer-events: auto; }
@media (min-width: 584px) {
    html.kioku-review-toolbar #stats,
    html.kioku-review-toolbar #sync { display: inline-block; }
    html.kioku-review-toolbar #kioku-edit-current,
    html.kioku-review-toolbar #kioku-undo-current,
    html.kioku-review-toolbar #kioku-review-more { display: none; }
}
"""


def _edit_current(toolbar):
    mw = toolbar.mw
    if mw.state == "review" and mw.reviewer.card is not None:
        mw.onEditCurrent()


def _undo(toolbar):
    mw = toolbar.mw
    if mw.state != "review" or not mw.undo_actions_info().can_undo:
        return

    from anki.errors import UndoEmpty
    from aqt.operations import CollectionOp
    from aqt.utils import showWarning, tooltip

    # Match Anki's undo operation, including its hooks and feedback. The
    # initiator lets us recognize this particular operation after Anki has
    # processed its changes; menu/keyboard undos keep their normal behavior.
    def success(out):
        gui_hooks.state_did_undo(out)
        tooltip(tr.undo_action_undone(action=out.operation), parent=mw)

    def failure(error):
        if not isinstance(error, UndoEmpty):
            showWarning(str(error), parent=mw)

    CollectionOp(mw, lambda col: col.undo()).success(success).failure(failure).run_in_background(
        initiator=_TOOLBAR_UNDO
    )


def _after_operation(changes, initiator):
    if initiator is not _TOOLBAR_UNDO:
        return
    mw = aqt.mw
    if mw.state != "review" or not mw.reviewer._refresh_needed:
        return

    from aqt.qt import QApplication, Qt

    # Anki defers refreshing when another window has focus. On iOS the undo
    # tooltip can be mistaken for that window, leaving the card dimmed. Do
    # not override the deferral for a genuine dialog, popup, or other window.
    if QApplication.activeModalWidget() or QApplication.activePopupWidget():
        return
    # Qt can retain a stale focusWidget from a different window even after
    # the main window becomes active; prefer the active top-level window.
    active = QApplication.activeWindow()
    if active is None:
        focus = QApplication.focusWidget()
        active = focus.window() if focus is not None else None
    if active is not None and active is not mw and active.isVisible():
        if active.windowType() != Qt.WindowType.ToolTip:
            return
    mw.reviewer.refresh_if_needed()


def _review_more(toolbar):
    mw = toolbar.mw
    reviewer = mw.reviewer
    if mw.state != "review" or reviewer.card is None:
        return

    from aqt.qt import QMenu, QPoint
    from aqt.utils import qtMenuShortcutWorkaround

    menu = getattr(mw, "_kioku_ui_polish_review_menu", None)
    if menu is None:
        menu = QMenu(mw)
        mw._kioku_ui_polish_review_menu = menu
    else:
        menu.clear()
    reviewer._addMenuItems(menu, reviewer._contextMenu())
    gui_hooks.reviewer_will_show_context_menu(reviewer, menu)
    qtMenuShortcutWorkaround(menu)
    # Anchor to the visible toolbar instead of QCursor.pos(), which may not
    # represent a finger tap on iOS.
    web = toolbar.web
    menu.popup(web.mapToGlobal(QPoint(web.width() // 2, web.height())))


def _add_toolbar_link(links, toolbar):
    links.append(toolbar.create_link(
        "kioku-edit-current", tr.studying_edit(), lambda: _edit_current(toolbar),
        id="kioku-edit-current",
    ))
    links.append(toolbar.create_link(
        "kioku-undo-current", tr.undo_undo(), lambda: _undo(toolbar),
        id="kioku-undo-current",
    ))
    links.append(toolbar.create_link(
        "kioku-review-more", tr.studying_more(), lambda: _review_more(toolbar),
        id="kioku-review-more",
    ))


def _set_undo_state(web, can_undo, description=""):
    on = "true" if can_undo else "false"
    disabled = "false" if can_undo else "true"
    web.eval(
        f'document.documentElement.classList.toggle("kioku-can-undo", {on});'
        'var undoButton=document.getElementById("kioku-undo-current")||document.getElementById("kioku-bottom-undo");'
        f'if(undoButton){{undoButton.setAttribute("aria-disabled", {json.dumps(disabled)});'
        f'undoButton.setAttribute("title", {json.dumps(description)});'
        f'if(undoButton.tagName === "BUTTON") undoButton.disabled = {"false" if can_undo else "true"};}}'
    )


def _undo_state_changed(info):
    mw = aqt.mw
    _set_undo_state(mw.toolbar.web, info.can_undo, info.undo_text)
    if mw.state == "review":
        _set_undo_state(mw.bottomWeb, info.can_undo, info.undo_text)


def _update_toolbar_state(_new_state, _old_state):
    # Read the actual state: a state transition can itself trigger another one.
    mw = aqt.mw
    on = "true" if mw.state == "review" else "false"
    web = mw.toolbar.web
    web.eval(f'document.documentElement.classList.toggle("kioku-review-toolbar", {on});')
    info = mw.undo_actions_info()
    _set_undo_state(web, info.can_undo, info.undo_text)
    if mw.state == "review":
        _set_undo_state(mw.bottomWeb, info.can_undo, info.undo_text)
    web.adjustHeightToFit()


def _style_web_content(web_content, context):
    if isinstance(context, ReviewerBottomBar):
        can_undo = context.reviewer.mw.undo_actions_info().can_undo
        label = json.dumps(tr.undo_undo()).replace("</", "<\\/")
        on = "true" if can_undo else "false"
        web_content.head += f"\n<style>{_REVIEW_CSS}</style>\n" + (
            '<script>document.documentElement.classList.toggle("kioku-can-undo", ' + on + ');'
            'document.addEventListener("DOMContentLoaded",function(){'
            'var cells=document.querySelectorAll("#innertable > tbody > tr > td.stat");'
            'if(cells.length<2)return;var button=document.createElement("button");'
            'button.id="kioku-bottom-undo";button.type="button";button.textContent=' + label + ';'
            'button.disabled=!document.documentElement.classList.contains("kioku-can-undo");'
            'button.setAttribute("aria-disabled",String(button.disabled));'
            'button.onclick=function(){return pycmd("kioku:bottom-undo");};'
            'cells[cells.length-1].appendChild(button);});</script>\n'
        )
    elif isinstance(context, DeckBrowser):
        web_content.head += f"\n<style>{_DECK_CSS}</style>\n<script>{_DECK_JS}</script>\n"
    elif isinstance(context, TopToolbar):
        mw = context.toolbar.mw
        on = "true" if getattr(mw, "state", None) == "review" else "false"
        can_undo = "true" if mw.undo_actions_info().can_undo else "false"
        web_content.head += (
            f"\n<style>{_TOOLBAR_CSS}</style>\n"
            f'<script>document.documentElement.classList.toggle("kioku-review-toolbar", {on});'
            f'document.documentElement.classList.toggle("kioku-can-undo", {can_undo});'
            'document.addEventListener("DOMContentLoaded",function(){'
            'var button=document.getElementById("kioku-undo-current");'
            'if(button)button.setAttribute("aria-disabled",'
            'String(!document.documentElement.classList.contains("kioku-can-undo")));'
            'var width=window.innerWidth;window.addEventListener("resize",function(){'
            'if(window.innerWidth===width)return;width=window.innerWidth;'
            'if(typeof pycmd==="function")pycmd("kioku:toolbar-resize");});});</script>\n'
        )


def _install_compact_menubar(bar):
    """Fit the browser menus on a phone while preserving larger text if possible."""
    from aqt.qt import QEvent, QFont, QObject, QTimer

    class FitMenuBar(QObject):
        def __init__(self):
            super().__init__(bar)
            self.font = QFont(bar.font())
            self.style = bar.styleSheet()
            self.last = None
            self.pending = False

        def eventFilter(self, obj, event):
            if event.type() in (QEvent.Type.Show, QEvent.Type.Resize,
                                QEvent.Type.ActionAdded, QEvent.Type.ActionRemoved):
                if not self.pending:
                    self.pending = True
                    QTimer.singleShot(0, self.fit)
            return False

        def fit(self):
            self.pending = False
            try:
                width = bar.width()
                key = (width, tuple(action.text() for action in bar.actions()))
                if width <= 0 or key == self.last:
                    return
                self.last = key
                bar.setStyleSheet(self.style + ("\nQMenuBar::item { padding: 3px 1px; }" if width < 600 else ""))
                bar.setFont(self.font)
                if width >= 600:
                    return
                font = QFont(self.font)
                size = font.pointSizeF()
                if size > 0:
                    minimum = min(size, 11.0)
                    while size > minimum and bar.sizeHint().width() > width:
                        size = max(minimum, size - 0.5)
                        font.setPointSizeF(size)
                        bar.setFont(font)
                elif font.pixelSize() > 0:
                    pixels = font.pixelSize()
                    minimum = min(pixels, 15)
                    while pixels > minimum and bar.sizeHint().width() > width:
                        pixels -= 1
                        font.setPixelSize(pixels)
                        bar.setFont(font)
            except RuntimeError:
                # The browser may have closed while the queued fit was waiting.
                return

    fitter = FitMenuBar()
    bar.installEventFilter(fitter)
    bar._kioku_ui_polish_menu_fit = fitter


def _add_browser_columns(browser):
    from anki.lang import current_lang
    from aqt.qt import QMenu, QSignalBlocker, Qt

    label = "列" if current_lang.lower().startswith("zh") else "Columns"

    class ColumnsMenu(QMenu):
        def mouseReleaseEvent(self, event):
            action = self.actionAt(event.pos())
            if (event.button() == Qt.MouseButton.LeftButton and action is not None
                    and action.isEnabled() and action.isCheckable() and action.menu() is None):
                # A normal QMenu closes on every selection. Keep it open for
                # consecutive column changes; other menu actions stay normal.
                action.trigger()
                event.accept()
                return
            super().mouseReleaseEvent(event)

    menu = ColumnsMenu(label, browser)
    menu.setObjectName("kiokuColumnsMenu")
    menu.setToolTipsVisible(True)

    def fill_columns():
        menu.clear()
        table = browser.table
        for key, column in table._model.columns.items():
            action = menu.addAction(table._state.column_label(column))
            action.setCheckable(True)
            action.setChecked(table._model.active_column_index(key) is not None)
            action.setToolTip(table._state.column_tooltip(column))

            def toggle(checked, key=key, action=action):
                table._on_column_toggled(checked, key)
                # Anki refuses to hide the last column. Keep the menu's
                # checkmark consistent with the actual model in that case.
                with QSignalBlocker(action):
                    action.setChecked(table._model.active_column_index(key) is not None)

            action.toggled.connect(toggle)
        gui_hooks.browser_header_will_show_context_menu(browser, menu)

    menu.aboutToShow.connect(fill_columns)
    browser.form.menubar.addMenu(menu)
    browser._kioku_ui_polish_columns = menu
    if sys.platform in ("ios", "android"):
        _install_compact_menubar(browser.form.menubar)


def _bottom_message(handled, message, context):
    if handled[0]:
        return handled
    if message == "kioku:bottom-undo" and isinstance(context, ReviewerBottomBar):
        _undo(context.reviewer.mw.toolbar)
        return (True, None)
    if message == "kioku:toolbar-resize" and isinstance(context, TopToolbar):
        if context.toolbar.mw.state == "review":
            context.toolbar.web.adjustHeightToFit()
        return (True, None)
    return handled


gui_hooks.webview_did_receive_js_message.append(_bottom_message)
gui_hooks.webview_will_set_content.append(_style_web_content)
gui_hooks.top_toolbar_did_init_links.append(_add_toolbar_link)
gui_hooks.state_did_change.append(_update_toolbar_state)
gui_hooks.undo_state_did_change.append(_undo_state_changed)
gui_hooks.browser_will_show.append(_add_browser_columns)
gui_hooks.operation_did_execute.append(_after_operation)
