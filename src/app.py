import sys
import os
from datetime import datetime
import markdown
from PyQt6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTextBrowser,
    QFrame,
    QListWidgetItem,
    QLabel,
    QMessageBox,
    QMainWindow,
    QDockWidget,
    QTabWidget,

    QComboBox,
    QFileDialog,
    QApplication,
    QSizePolicy,
)
from PyQt6.QtCore import QTimer, Qt, QObject, QEvent
from PyQt6.QtGui import QShortcut, QKeySequence, QIcon, QAction
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog

from .auth import AuthManager
from .ui.dialogs import (
    CustomTitleBar,
    CustomInputDialog,
    CustomMessageBox,
    FindReplaceDialog,
    TagsDialog,
    VersionHistoryDialog,
    StatisticsDialog,
    SettingsDialog,
    StyledMenu,
)
from .ui.widgets import NoteListWidget, NoteItemWidget
from .ui.editor import NoteEditor

AUTO_LOCK_MINUTES = {
    "0": 0,
    "5": 5,
    "10": 10,
    "30": 30,
    "60": 60,
}


class ActivityFilter(QObject):
    def __init__(self, app_window):
        super().__init__()
        self.app_window = app_window

    def eventFilter(self, obj, event):
        if event.type() in (
            QEvent.Type.MouseMove,
            QEvent.Type.KeyPress,
            QEvent.Type.MouseButtonPress,
            QEvent.Type.Wheel,
        ):
            self.app_window.reset_auto_lock_timer()
        return False


class HiddenoteApp(QMainWindow):
    def __init__(self, test_mode=False):
        super().__init__()
        self.auth_manager = AuthManager()
        self.db_manager = None
        self.current_note = None
        self._find_replace_dialog = None
        self._auto_lock_timer = QTimer()
        self._auto_lock_timer.setSingleShot(True)
        self._auto_lock_timer.timeout.connect(self._lock_app)
        self._activity_filter = ActivityFilter(self)

        self.init_ui()
        self.show()

        if test_mode:
            self._init_test_db()
        else:
            if not self.auth_manager.authenticate_user(self):
                sys.exit()
            self.db_manager = self.auth_manager.get_database_manager()
            self._check_integrity()
            self._apply_auto_lock_setting()
            self._apply_trash_clean_setting()
            QApplication.instance().installEventFilter(self._activity_filter)

        self.notes_list.current_view = "all"
        self.setup_shortcuts()
        self.setup_auto_save()
        self.load_notes()
        QTimer.singleShot(100, self._update_editor_corners)

    def _init_test_db(self):
        from .database import DatabaseManager
        import os

        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "hiddenote_test.db")
        if os.path.exists(db_path):
            os.remove(db_path)

        self.db_manager = DatabaseManager(db_path)
        self.db_manager.setup_encryption("demo")
        self.db_manager.populate_demo_data()

    def _check_integrity(self):
        if not self.db_manager.verify_integrity():
            CustomMessageBox.warning(
                self,
                "integrity warning",
                "the database appears to have been modified externally. "
                "your notes may have been tampered with.",
            )

    def _apply_auto_lock_setting(self):
        minutes = int(self.db_manager.get_setting("auto_lock_minutes", "0"))
        if minutes > 0:
            self._auto_lock_timer.setInterval(minutes * 60 * 1000)
            self._auto_lock_timer.start()
        else:
            self._auto_lock_timer.stop()

    def _apply_trash_clean_setting(self):
        days = int(self.db_manager.get_setting("trash_clean_days", "30"))
        if days > 0:
            self.db_manager.auto_clean_trash(days)

    def reset_auto_lock_timer(self):
        if self._auto_lock_timer.isActive():
            self._auto_lock_timer.start()

    def _lock_app(self):
        self.db_manager.lock()
        self.edit_tab.clear()
        self.preview_tab.clear()
        self.current_note = None
        self.update_window_title()

        if not self.auth_manager.re_authenticate(self):
            sys.exit()

        self.db_manager = self.auth_manager.get_database_manager()
        self._apply_auto_lock_setting()
        self.load_notes()

    def init_ui(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setGeometry(100, 100, 1200, 800)

        icon_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "assets", "icon.ico"
        )
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.main_frame = QFrame()
        self.main_frame.setObjectName("mainFrame")
        frame_layout = QVBoxLayout(self.main_frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(0)

        self.title_bar = CustomTitleBar(self, "hiddenote")
        self._build_title_bar_actions()
        frame_layout.addWidget(self.title_bar)

        dock_container = QMainWindow()
        dock_container.setObjectName("dockContainer")
        dock_container.setDockOptions(
            QMainWindow.DockOption.AllowNestedDocks
            | QMainWindow.DockOption.AllowTabbedDocks
            | QMainWindow.DockOption.AnimatedDocks
        )
        dock_container.setTabPosition(
            Qt.DockWidgetArea.AllDockWidgetAreas, QTabWidget.TabPosition.North
        )
        frame_layout.addWidget(dock_container)

        self.dock_main_window = dock_container
        self.setCentralWidget(self.main_frame)

        self.setup_sidebar()
        self.setup_editor_dock()
        self.setup_preview_dock()
        self.setup_context_menu()

    def _build_title_bar_actions(self):
        layout = self.title_bar.layout()

        btn_style = (
            "QPushButton { background: transparent; color: #6C6F7E; border: none;"
            "font-size: 13px; min-width: 0; max-width: 9999px;"
            "min-height: 22px; max-height: 22px; padding: 0 8px; border-radius: 4px; }"
            "QPushButton:hover { background: #35384A; color: #FFD580; }"
        )

        for symbol, slot, tip in [
            ("stats", self._show_stats, "statistics"),
            ("settings", self._show_settings, "settings"),
            ("import", self._import_file, "import file"),
            ("lock", self._lock_app, "lock (Ctrl+L)"),
        ]:
            btn = QPushButton(symbol)
            btn.setToolTip(tip)
            btn.setStyleSheet(btn_style)
            btn.clicked.connect(slot)
            idx = layout.count() - 1
            layout.insertWidget(idx, btn)

        spacer_label = QLabel("  ")
        layout.insertWidget(layout.count() - 1, spacer_label)

    def setup_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("sidebarFrame")
        sidebar.setFixedWidth(260)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setSpacing(6)
        sidebar_layout.setContentsMargins(8, 8, 8, 8)

        new_note_btn = QPushButton("+ new note")
        new_note_btn.clicked.connect(self.create_new_note)
        sidebar_layout.addWidget(new_note_btn)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("search notes...")
        self.search_input.textChanged.connect(self.filter_notes)
        sidebar_layout.addWidget(self.search_input)

        view_row = QHBoxLayout()
        view_row.setSpacing(4)

        self._view_buttons = {}
        for view, label in [("all", "all"), ("pinned", "★"), ("archived", "arch"), ("trash", "trash")]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setFixedHeight(28)
            btn.setStyleSheet(
                "QPushButton { background: #35384A; color: #6C6F7E; border-radius: 6px;"
                "font-size: 13px; min-width: 0; padding: 2px 8px; }"
                "QPushButton:checked { background: #FFD580; color: #23262F; }"
                "QPushButton:hover:!checked { background: #3D4057; }"
            )
            btn.clicked.connect(lambda _, v=view: self._set_view(v))
            view_row.addWidget(btn)
            self._view_buttons[view] = btn

        self._view_buttons["all"].setChecked(True)
        sidebar_layout.addLayout(view_row)

        sort_tag_row = QHBoxLayout()
        sort_tag_row.setSpacing(4)

        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["updated", "created", "A → Z", "Z → A"])
        self.sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        sort_tag_row.addWidget(self.sort_combo)

        self.tag_filter_combo = QComboBox()
        self.tag_filter_combo.addItem("all tags")
        self.tag_filter_combo.currentIndexChanged.connect(self._on_tag_filter_changed)
        sort_tag_row.addWidget(self.tag_filter_combo)
        sidebar_layout.addLayout(sort_tag_row)

        self.notes_list = NoteListWidget(self)
        self.notes_list.currentRowChanged.connect(self.load_note)
        sidebar_layout.addWidget(self.notes_list)

        self.sidebar_dock = QDockWidget("Notes", self.dock_main_window)
        self.sidebar_dock.setWidget(sidebar)
        self.sidebar_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.sidebar_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.dock_main_window.addDockWidget(
            Qt.DockWidgetArea.LeftDockWidgetArea, self.sidebar_dock
        )

    def _sort_key(self):
        sort_map = {0: "updated_at", 1: "created_at", 2: "title_asc", 3: "title_desc"}
        return sort_map.get(self.sort_combo.currentIndex(), "updated_at")

    def _tag_filter(self):
        if self.tag_filter_combo.currentIndex() <= 0:
            return None
        return self.tag_filter_combo.currentText()

    def _on_sort_changed(self):
        self.load_notes(keep_selection=True)

    def _on_tag_filter_changed(self):
        self.load_notes(keep_selection=True)

    def _set_view(self, view):
        for v, btn in self._view_buttons.items():
            btn.setChecked(v == view)
        self.notes_list.current_view = view
        self.load_notes()

    def setup_editor_dock(self):
        self.editor_container = QFrame()
        self.editor_container.setObjectName("editorFrame")
        editor_layout = QVBoxLayout(self.editor_container)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(0)

        self.edit_tab = NoteEditor()
        self.edit_tab.textChanged.connect(self.on_text_changed)
        self.edit_tab.cursor_position_changed.connect(self._update_status_bar)
        editor_layout.addWidget(self.edit_tab)

        self.status_bar = QLabel("words: 0  chars: 0  line 1, col 1")
        self.status_bar.setObjectName("statusBar")
        self._apply_status_bar_style(0, 0)
        self.status_bar.setAlignment(Qt.AlignmentFlag.AlignRight)
        editor_layout.addWidget(self.status_bar)

        self.editor_dock = QDockWidget("Editor", self.dock_main_window)
        self.editor_dock.setWidget(self.editor_container)
        self.editor_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.editor_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea
            | Qt.DockWidgetArea.RightDockWidgetArea
            | Qt.DockWidgetArea.TopDockWidgetArea
            | Qt.DockWidgetArea.BottomDockWidgetArea
        )
        self.dock_main_window.addDockWidget(
            Qt.DockWidgetArea.RightDockWidgetArea, self.editor_dock
        )

        self.editor_dock.dockLocationChanged.connect(
            lambda _: QTimer.singleShot(50, self._update_editor_corners)
        )
        self.editor_dock.topLevelChanged.connect(
            lambda _: QTimer.singleShot(50, self._update_editor_corners)
        )

    def setup_preview_dock(self):
        self.preview_tab = QTextBrowser()

        self.preview_dock = QDockWidget("Preview", self.dock_main_window)
        self.preview_dock.setWidget(self.preview_tab)
        self.preview_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.preview_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea
            | Qt.DockWidgetArea.RightDockWidgetArea
            | Qt.DockWidgetArea.TopDockWidgetArea
            | Qt.DockWidgetArea.BottomDockWidgetArea
        )
        self.dock_main_window.addDockWidget(
            Qt.DockWidgetArea.RightDockWidgetArea, self.preview_dock
        )

        self.dock_main_window.tabifyDockWidget(self.editor_dock, self.preview_dock)
        self.editor_dock.raise_()

    def get_dock_widgets(self):
        return {
            "sidebar": self.sidebar_dock,
            "editor": self.editor_dock,
            "preview": self.preview_dock,
        }

    def reset_layout(self):
        self.dock_main_window.addDockWidget(
            Qt.DockWidgetArea.LeftDockWidgetArea, self.sidebar_dock
        )
        self.dock_main_window.addDockWidget(
            Qt.DockWidgetArea.RightDockWidgetArea, self.editor_dock
        )
        self.dock_main_window.addDockWidget(
            Qt.DockWidgetArea.RightDockWidgetArea, self.preview_dock
        )
        self.dock_main_window.tabifyDockWidget(self.editor_dock, self.preview_dock)
        self.editor_dock.raise_()
        self.sidebar_dock.show()
        self.editor_dock.show()
        self.preview_dock.show()

    def setup_context_menu(self):
        self.dock_main_window.menuBar().hide()
        self.dock_main_window.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.dock_main_window.customContextMenuRequested.connect(
            self.show_dock_context_menu
        )

    def show_dock_context_menu(self, position):
        context_menu = StyledMenu(self)

        for dock, label in [
            (self.sidebar_dock, "show/hide notes"),
            (self.editor_dock, "show/hide editor"),
            (self.preview_dock, "show/hide preview"),
        ]:
            act = context_menu.addAction(label)
            act.setCheckable(True)
            act.setChecked(dock.isVisible())
            act.triggered.connect(lambda checked, d=dock: d.setVisible(checked))

        context_menu.addSeparator()

        sep_act = context_menu.addAction("separate editor and preview")
        sep_act.triggered.connect(self.separate_editor_preview)

        tab_act = context_menu.addAction("tabify editor and preview")
        tab_act.triggered.connect(self.tabify_editor_preview)

        context_menu.addSeparator()

        ln_act = context_menu.addAction("toggle line numbers")
        ln_act.triggered.connect(self.edit_tab.toggle_line_numbers)

        context_menu.addSeparator()

        reset_act = context_menu.addAction("reset layout")
        reset_act.triggered.connect(self.reset_layout)

        context_menu.exec(self.dock_main_window.mapToGlobal(position))

    def separate_editor_preview(self):
        if self.editor_dock.isFloating():
            self.dock_main_window.addDockWidget(
                Qt.DockWidgetArea.LeftDockWidgetArea, self.editor_dock
            )
        if self.preview_dock.isFloating():
            self.dock_main_window.addDockWidget(
                Qt.DockWidgetArea.RightDockWidgetArea, self.preview_dock
            )
        self.dock_main_window.splitDockWidget(
            self.editor_dock, self.preview_dock, Qt.Orientation.Horizontal
        )

    def tabify_editor_preview(self):
        if self.editor_dock.isFloating():
            self.dock_main_window.addDockWidget(
                Qt.DockWidgetArea.RightDockWidgetArea, self.editor_dock
            )
        if self.preview_dock.isFloating():
            self.dock_main_window.addDockWidget(
                Qt.DockWidgetArea.RightDockWidgetArea, self.preview_dock
            )
        self.dock_main_window.tabifyDockWidget(self.editor_dock, self.preview_dock)
        self.editor_dock.raise_()

    def setup_shortcuts(self):
        shortcuts = [
            ("Ctrl+N", self.create_new_note),
            ("Insert", self.create_new_note),
            ("Ctrl+S", self._save_with_version),
            ("Ctrl+F", self.focus_search),
            ("Ctrl+H", self._show_find_replace),
            ("Ctrl+Shift+D", self._insert_datetime),
            ("Ctrl+L", self._lock_app),
            ("Ctrl+P", self._print_note),
        ]
        for key, slot in shortcuts:
            sc = QShortcut(QKeySequence(key), self)
            sc.activated.connect(slot)

    def setup_auto_save(self):
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.auto_save)
        self.auto_save_timer.setSingleShot(True)

    def update_window_title(self, note_title=None):
        title = f"hiddenote - {note_title}" if note_title else "hiddenote"
        self.title_bar.update_title(title)

    def create_new_note(self):
        title, ok = CustomInputDialog.getText(
            self, "new note", "what should we call it?"
        )
        if ok and title.strip():
            title = title.strip()
            existing_titles = [n[0] for n in self.notes_list.all_notes]
            if title in existing_titles:
                CustomMessageBox.warning(
                    self, "hmm", "you already have a note with that name"
                )
                return
            self.save_current_note(save_version=True)
            self.db_manager.save_note(title, "")
            self.load_notes()
            self._select_note_by_title(title)

    def rename_note_dialog(self, old_title):
        new_title, ok = CustomInputDialog.getText(
            self, "rename note", "new name:", text=old_title
        )
        if ok and new_title.strip() and new_title.strip() != old_title:
            new_title = new_title.strip()
            existing = [n[0] for n in self.notes_list.all_notes]
            if new_title in existing:
                CustomMessageBox.warning(
                    self, "hmm", "a note with that name already exists"
                )
                return
            self.db_manager.rename_note(old_title, new_title)
            if self.current_note == old_title:
                self.current_note = new_title
                self.update_window_title(new_title)
            self.load_notes(keep_selection=True)

    def handle_note_delete(self, title):
        view = self.notes_list.current_view
        if view == "trash":
            self.permanently_delete_note(title)
            return

        reply = CustomMessageBox.question(
            self,
            "move to trash",
            f"move '{title}' to trash?",
            [QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.No],
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.db_manager.trash_note(title)
            if title == self.current_note:
                self.current_note = None
                self.edit_tab.textChanged.disconnect()
                self.edit_tab.clear()
                self.edit_tab.textChanged.connect(self.on_text_changed)
                self.preview_tab.clear()
                self.update_window_title()
            self.load_notes()

    def permanently_delete_note(self, title):
        reply = CustomMessageBox.question(
            self,
            "delete permanently",
            f"permanently delete '{title}'? this cannot be undone.",
            [QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.No],
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.db_manager.delete_note_permanently(title)
            if title == self.current_note:
                self.current_note = None
                self.edit_tab.textChanged.disconnect()
                self.edit_tab.clear()
                self.edit_tab.textChanged.connect(self.on_text_changed)
                self.preview_tab.clear()
                self.update_window_title()
            self.load_notes()

    def restore_note_from_trash(self, title):
        self.db_manager.restore_from_trash(title)
        self.load_notes()

    def empty_trash(self):
        reply = CustomMessageBox.question(
            self,
            "empty trash",
            "permanently delete all notes in trash?",
            [QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.No],
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.db_manager.empty_trash()
            self.load_notes()

    def toggle_pin_note(self, title):
        self.db_manager.toggle_pin(title)
        self.load_notes(keep_selection=True)

    def toggle_archive_note(self, title):
        self.db_manager.toggle_archive(title)
        if self.current_note == title:
            self.current_note = None
            self.edit_tab.textChanged.disconnect()
            self.edit_tab.clear()
            self.edit_tab.textChanged.connect(self.on_text_changed)
            self.preview_tab.clear()
            self.update_window_title()
        self.load_notes()

    def manage_note_tags(self, title):
        current_tags = self.db_manager.get_note_tags(title)
        all_tags = self.db_manager.get_all_tags()
        dialog = TagsDialog(current_tags, all_tags, parent=self)
        if dialog.exec():
            self.db_manager.set_note_tags(title, dialog.selected_tags)
            self._refresh_tag_filter()
            self.load_notes(keep_selection=True)

    def set_note_readonly(self, title, read_only):
        self.db_manager.set_setting(f"readonly_{title}", "1" if read_only else "0")
        if title == self.current_note:
            self.edit_tab.setReadOnly(read_only)
            self._update_status_bar_readonly(read_only)

    def export_note(self, title, fmt):
        ext_map = {"md": ("Markdown (*.md)", ".md"), "html": ("HTML (*.html)", ".html"), "txt": ("Text (*.txt)", ".txt")}
        filter_str, ext = ext_map.get(fmt, ("All Files (*)", ""))
        path, _ = QFileDialog.getSaveFileName(self, "export note", f"{title}{ext}", filter_str)
        if not path:
            return
        try:
            if fmt == "html":
                self.db_manager.export_note_as_html(title, path)
            else:
                self.db_manager.export_note_as_text(title, path)
            CustomMessageBox.warning(self, "done", f"note exported to:\n{path}")
        except Exception as e:
            CustomMessageBox.critical(self, "error", f"export failed: {e}")

    def show_version_history(self, title):
        versions = self.db_manager.get_note_versions(title)
        if not versions:
            CustomMessageBox.warning(self, "version history", "no saved versions for this note yet.\npress Ctrl+S to create a snapshot.")
            return
        dialog = VersionHistoryDialog(versions, self.db_manager, parent=self)
        if dialog.exec() and dialog.restored_content is not None:
            reply = CustomMessageBox.question(
                self,
                "restore version",
                "replace current content with this version?",
                [QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.No],
            )
            if reply == QMessageBox.StandardButton.Yes and title == self.current_note:
                self.edit_tab.textChanged.disconnect()
                self.edit_tab.setPlainText(dialog.restored_content)
                self.edit_tab.textChanged.connect(self.on_text_changed)
                self.update_preview()
                self.save_current_note(save_version=True)

    def load_notes(self, keep_selection=False):
        selected_title = self.current_note if keep_selection else None
        view = self.notes_list.current_view
        notes = self.db_manager.get_all_notes(
            sort_by=self._sort_key(),
            view=view,
            tag_filter=self._tag_filter(),
        )
        self.notes_list.set_all_notes(notes)
        self.notes_list.clear()

        for note in notes:
            title, created_at, updated_at = note[0], note[1], note[2]
            pinned = bool(note[3]) if len(note) > 3 else False
            archived = bool(note[4]) if len(note) > 4 else False
            tags = note[5] if len(note) > 5 else None
            item = QListWidgetItem()
            widget = NoteItemWidget(title, created_at, updated_at, pinned, archived, tags)
            item.setSizeHint(widget.sizeHint())
            self.notes_list.addItem(item)
            self.notes_list.setItemWidget(item, widget)

        if selected_title:
            self._select_note_by_title(selected_title)
        elif notes:
            self.notes_list.setCurrentRow(0)

        self._refresh_tag_filter()

    def _refresh_tag_filter(self):
        if self.db_manager is None:
            return
        current_tag = self.tag_filter_combo.currentText()
        self.tag_filter_combo.blockSignals(True)
        self.tag_filter_combo.clear()
        self.tag_filter_combo.addItem("all tags")
        for tag in self.db_manager.get_all_tags():
            self.tag_filter_combo.addItem(tag)
        idx = self.tag_filter_combo.findText(current_tag)
        if idx >= 0:
            self.tag_filter_combo.setCurrentIndex(idx)
        self.tag_filter_combo.blockSignals(False)

    def _select_note_by_title(self, title):
        for i in range(self.notes_list.count()):
            item = self.notes_list.item(i)
            widget = self.notes_list.itemWidget(item)
            if widget:
                label = widget.findChild(QLabel, "noteTitle")
                if label and label.text() == title:
                    self.notes_list.setCurrentRow(i)
                    return

    def load_note(self, index):
        if index >= 0 and index < self.notes_list.count():
            self.save_current_note(save_version=True)

            item = self.notes_list.item(index)
            widget = self.notes_list.itemWidget(item)
            if widget is None:
                return
            label = widget.findChild(QLabel, "noteTitle")
            if label is None:
                return
            title = label.text()
            content = self.db_manager.load_note(title)
            self.current_note = title

            read_only = self.db_manager.get_setting(f"readonly_{title}") == "1"

            self.edit_tab.textChanged.disconnect()
            self.edit_tab.setReadOnly(False)
            self.edit_tab.setPlainText(content)
            self.edit_tab.setReadOnly(read_only)
            self.edit_tab.textChanged.connect(self.on_text_changed)

            self.update_preview()
            self.update_window_title(title)
            self._update_status_bar(1, 1)
            self._update_status_bar_readonly(read_only)
        else:
            self.current_note = None
            self.update_window_title()

    def save_current_note(self, save_version=False):
        if self.current_note and not self.edit_tab.isReadOnly():
            content = self.edit_tab.toPlainText()
            self.db_manager.save_note(self.current_note, content, save_version=save_version)
            self.db_manager.update_integrity_hash()

    def _save_with_version(self):
        self.save_current_note(save_version=True)

    def on_text_changed(self):
        self.auto_save_timer.stop()
        self.auto_save_timer.start(1500)
        self.update_preview()
        words, chars = self.edit_tab.word_count()
        cursor = self.edit_tab.textCursor()
        self._update_status_bar(
            cursor.blockNumber() + 1, cursor.columnNumber() + 1, words, chars
        )

    def auto_save(self):
        self.save_current_note(save_version=False)

    def update_preview(self):
        text = self.edit_tab.toPlainText()
        try:
            html = markdown.markdown(
                text,
                extensions=["fenced_code", "codehilite", "tables", "toc"],
            )
        except Exception:
            html = markdown.markdown(text)
        self.preview_tab.setHtml(html)

    def _update_status_bar(self, line=1, col=1, words=None, chars=None):
        if words is None or chars is None:
            w, c = self.edit_tab.word_count()
        else:
            w, c = words, chars
        readonly_indicator = "  [READ-ONLY]" if self.edit_tab.isReadOnly() else ""
        self.status_bar.setText(
            f"words: {w}  chars: {c}  line {line}, col {col}{readonly_indicator}"
        )

    def _update_status_bar_readonly(self, is_readonly):
        words, chars = self.edit_tab.word_count()
        cursor = self.edit_tab.textCursor()
        self._update_status_bar(
            cursor.blockNumber() + 1, cursor.columnNumber() + 1, words, chars
        )

    def _show_find_replace(self):
        if self._find_replace_dialog is None:
            self._find_replace_dialog = FindReplaceDialog(self)
            self._find_replace_dialog.find_requested.connect(self._do_find)
            self._find_replace_dialog.replace_requested.connect(self._do_replace)
            self._find_replace_dialog.replace_all_requested.connect(self._do_replace_all)
        self._find_replace_dialog.focus_find()

    def _do_find(self, text, forward, case_sensitive):
        if not text:
            return
        found = self.edit_tab.find_text(text, forward=forward, case_sensitive=case_sensitive)
        if self._find_replace_dialog:
            self._find_replace_dialog.show_result("" if found else "not found")

    def _do_replace(self, find_text, replace_text, case_sensitive):
        if not find_text:
            return
        self.edit_tab.replace_current(find_text, replace_text, case_sensitive=case_sensitive)

    def _do_replace_all(self, find_text, replace_text, case_sensitive):
        if not find_text:
            return
        count = self.edit_tab.replace_all(find_text, replace_text, case_sensitive=case_sensitive)
        if self._find_replace_dialog:
            self._find_replace_dialog.show_result(f"replaced {count} occurrence{'s' if count != 1 else ''}")

    def _insert_datetime(self):
        if self.edit_tab.isReadOnly():
            return
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor = self.edit_tab.textCursor()
        cursor.insertText(ts)

    def _print_note(self):
        printer = QPrinter()
        dialog = QPrintDialog(printer, self)
        if dialog.exec():
            self.preview_tab.print(printer)

    def _import_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "import file", "", "Text Files (*.txt *.md);;All Files (*)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            title = os.path.splitext(os.path.basename(path))[0]
            existing = [n[0] for n in self.notes_list.all_notes]
            base = title
            counter = 1
            while title in existing:
                title = f"{base} ({counter})"
                counter += 1
            self.db_manager.save_note(title, content)
            self.load_notes()
            self._select_note_by_title(title)
        except Exception as e:
            CustomMessageBox.critical(self, "error", f"could not import file: {e}")

    def _show_stats(self):
        if self.db_manager is None:
            return
        stats = self.db_manager.get_statistics()
        dialog = StatisticsDialog(stats, parent=self)
        dialog.exec()

    def _show_settings(self):
        if self.db_manager is None:
            return
        dialog = SettingsDialog(self.db_manager, parent=self)
        if dialog.exec():
            self._apply_auto_lock_setting()
            self._apply_trash_clean_setting()

    def _apply_status_bar_style(self, bl, br):
        self.status_bar.setStyleSheet(
            f"color: #6C6F7E; font-size: 12px; padding: 4px 14px;"
            f"background: #1E2029; border-top: 1px solid #35384A; border-radius: 0;"
            f"border-bottom-left-radius: {bl}px; border-bottom-right-radius: {br}px;"
        )

    def _update_editor_corners(self):
        if self.editor_dock.isFloating() or not self.isVisible():
            self._apply_status_bar_style(0, 0)
            return

        ref = self.dock_main_window
        ref_rect = ref.rect()
        ref_br = ref.mapToGlobal(ref_rect.bottomRight())
        ref_bl = ref.mapToGlobal(ref_rect.bottomLeft())

        w = self.editor_container
        w_rect = w.rect()
        ed_br = w.mapToGlobal(w_rect.bottomRight())
        ed_bl = w.mapToGlobal(w_rect.bottomLeft())

        tol = 10
        radius = 18
        br = radius if abs(ed_br.x() - ref_br.x()) < tol and abs(ed_br.y() - ref_br.y()) < tol else 0
        bl = radius if abs(ed_bl.x() - ref_bl.x()) < tol and abs(ed_bl.y() - ref_bl.y()) < tol else 0

        self._apply_status_bar_style(bl, br)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(0, self._update_editor_corners)

    def closeEvent(self, event):
        self.save_current_note(save_version=True)
        self.db_manager.update_integrity_hash()
        event.accept()

    def focus_search(self):
        self.search_input.setFocus()
        self.search_input.selectAll()

    def filter_notes(self, search_text):
        if search_text.strip():
            self.notes_list.filter_notes(search_text)
        else:
            self.load_notes(keep_selection=True)
