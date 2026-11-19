"""Mobile-friendly review buttons and deck list for Kioku."""

import json
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
        'var undoButton=document.getElementById("kioku-undo-current");'
        f'if(undoButton){{undoButton.setAttribute("aria-disabled", {json.dumps(disabled)});'
        f'undoButton.setAttribute("title", {json.dumps(description)});}}'
    )


def _undo_state_changed(info):
    _set_undo_state(aqt.mw.toolbar.web, info.can_undo, info.undo_text)


def _update_toolbar_state(_new_state, _old_state):
    # Read the actual state: a state transition can itself trigger another one.
    mw = aqt.mw
    on = "true" if mw.state == "review" else "false"
    web = mw.toolbar.web
    web.eval(f'document.documentElement.classList.toggle("kioku-review-toolbar", {on});')
    info = mw.undo_actions_info()
    _set_undo_state(web, info.can_undo, info.undo_text)
    web.adjustHeightToFit()


def _style_web_content(web_content, context):
    if isinstance(context, ReviewerBottomBar):
        web_content.head += f"\n<style>{_REVIEW_CSS}</style>\n"
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
            'String(!document.documentElement.classList.contains("kioku-can-undo")));});</script>\n'
        )


def _add_browser_columns(browser):
    from anki.lang import current_lang
    from aqt.qt import QAction, QPoint, QPushButton

    label = "列" if current_lang.lower().startswith("zh") else "Columns"

    def show_columns():
        table = browser.table
        view = browser.form.tableView
        # The existing menu builds the correct columns for the current
        # Cards/Notes mode, preserves add-on hooks, and saves the selection.
        table._on_header_context(QPoint(0, view.horizontalHeader().height()))

    action = QAction(label + "…", browser)
    action.triggered.connect(lambda _checked=False: show_columns())
    browser.form.menuqt_accel_view.addAction(action)
    button = QPushButton(label + "…", browser)
    button.setObjectName("kiokuColumnsButton")
    button.setMinimumHeight(44)
    button.clicked.connect(lambda _checked=False: show_columns())
    grid = browser.form.gridLayout
    grid.addWidget(button, 0, grid.columnCount())
    # Qt parents own these objects; retain Python references as well.
    browser._kioku_ui_polish_columns = (action, button)


gui_hooks.webview_will_set_content.append(_style_web_content)
gui_hooks.top_toolbar_did_init_links.append(_add_toolbar_link)
gui_hooks.state_did_change.append(_update_toolbar_state)
gui_hooks.undo_state_did_change.append(_undo_state_changed)
gui_hooks.browser_will_show.append(_add_browser_columns)
gui_hooks.operation_did_execute.append(_after_operation)
