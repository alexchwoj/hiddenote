import sys
import os
import markdown
from PyQt6.QtWidgets import (
    QVBoxLayout,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QTextBrowser,
    QFrame,
    QListWidgetItem,
    QLabel,
    QMessageBox,
    QMainWindow,
    QDockWidget,
    QTabWidget,
    QMenu,
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QShortcut, QKeySequence, QIcon

from .auth import AuthManager
from .ui.dialogs import CustomTitleBar, CustomInputDialog, CustomMessageBox
from .ui.widgets import NoteListWidget, NoteItemWidget


class HiddenoteApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.auth_manager = AuthManager()
        self.db_manager = None
        self.current_note = None

        self.init_ui()
        self.show()

        if not self.auth_manager.authenticate_user(self):
            sys.exit()

        self.db_manager = self.auth_manager.get_database_manager()
        self.setup_shortcuts()
        self.setup_auto_save()
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
        frame_layout.addWidget(self.title_bar)

        dock_container = QMainWindow()
        dock_container.setObjectName("dockContainer")
        frame_layout.addWidget(dock_container)

        self.dock_main_window = dock_container
        self.setCentralWidget(self.main_frame)

        self.setup_sidebar()
        self.setup_editor_dock()
        self.setup_preview_dock()
        self.setup_context_menu()

    def setup_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("sidebarFrame")
        sidebar.setFixedWidth(250)
        sidebar_layout = QVBoxLayout(sidebar)

        new_note_btn = QPushButton("new note")
        new_note_btn.clicked.connect(self.create_new_note)
        sidebar_layout.addWidget(new_note_btn)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("search notes...")
        self.search_input.textChanged.connect(self.filter_notes)
        sidebar_layout.addWidget(self.search_input)

        self.notes_list = NoteListWidget(self)
        self.notes_list.currentRowChanged.connect(self.load_note)
        sidebar_layout.addWidget(self.notes_list)

        sidebar_dock = QDockWidget("Notes", self.dock_main_window)
        sidebar_dock.setWidget(sidebar)
        sidebar_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.dock_main_window.addDockWidget(
            Qt.DockWidgetArea.LeftDockWidgetArea, sidebar_dock
        )

    def setup_editor_dock(self):
        self.edit_tab = QTextEdit()
        self.edit_tab.textChanged.connect(self.on_text_changed)

        editor_dock = QDockWidget("Editor", self.dock_main_window)
        editor_dock.setWidget(self.edit_tab)
        editor_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.dock_main_window.addDockWidget(
            Qt.DockWidgetArea.RightDockWidgetArea, editor_dock
        )
        self.editor_dock = editor_dock

    def setup_preview_dock(self):
        self.preview_tab = QTextBrowser()

        preview_dock = QDockWidget("Preview", self.dock_main_window)
        preview_dock.setWidget(self.preview_tab)
        preview_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.dock_main_window.addDockWidget(
            Qt.DockWidgetArea.RightDockWidgetArea, preview_dock
        )
        self.preview_dock = preview_dock

        self.dock_main_window.tabifyDockWidget(self.editor_dock, preview_dock)
        self.editor_dock.raise_()

        self.dock_main_window.setTabPosition(
            Qt.DockWidgetArea.AllDockWidgetAreas, QTabWidget.TabPosition.North
        )

    def get_dock_widgets(self):
        return {"editor": self.editor_dock, "preview": self.preview_dock}

    def setup_context_menu(self):
        self.dock_main_window.menuBar().hide()

        self.dock_main_window.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.dock_main_window.customContextMenuRequested.connect(
            self.show_dock_context_menu
        )

    def show_dock_context_menu(self, position):
        context_menu = QMenu(self)

        editor_toggle = context_menu.addAction("Show/Hide Editor")
        editor_toggle.setCheckable(True)
        editor_toggle.setChecked(self.editor_dock.isVisible())
        editor_toggle.triggered.connect(
            lambda checked: self.editor_dock.setVisible(checked)
        )

        preview_toggle = context_menu.addAction("Show/Hide Preview")
        preview_toggle.setCheckable(True)
        preview_toggle.setChecked(self.preview_dock.isVisible())
        preview_toggle.triggered.connect(
            lambda checked: self.preview_dock.setVisible(checked)
        )

        context_menu.addSeparator()

        separate_action = context_menu.addAction("Separate Editor and Preview")
        separate_action.triggered.connect(self.separate_editor_preview)

        tabify_action = context_menu.addAction("Tabify Editor and Preview")
        tabify_action.triggered.connect(self.tabify_editor_preview)

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
        new_note_shortcut = QShortcut(QKeySequence("Ctrl+N"), self)
        new_note_shortcut.activated.connect(self.create_new_note)

        insert_shortcut = QShortcut(QKeySequence("Insert"), self)
        insert_shortcut.activated.connect(self.create_new_note)

        save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        save_shortcut.activated.connect(self.save_current_note)

        search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        search_shortcut.activated.connect(self.focus_search)

    def setup_auto_save(self):
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.auto_save)
        self.auto_save_timer.setSingleShot(True)

    def update_window_title(self, note_title=None):
        if note_title:
            title = f"hiddenote - {note_title}"
        else:
            title = "hiddenote"
        self.title_bar.update_title(title)

    def create_new_note(self):
        title, ok = CustomInputDialog.getText(
            self, "new note", "what should we call it?"
        )
        if ok and title.strip():
            title = title.strip()
            existing_titles = []

            for title_data, _, _ in self.notes_list.all_notes:
                existing_titles.append(title_data)

            if title in existing_titles:
                CustomMessageBox.warning(
                    self, "hmm", "you already have a note with that name"
                )
                return

            self.save_current_note()
            self.db_manager.save_note(title, "")
            self.load_notes()

    def delete_note(self, title):
        reply = CustomMessageBox.question(
            self,
            "delete note",
            f"sure you want to delete '{title}'?",
            [QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.No],
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.db_manager.delete_note(title)

            if title == self.current_note:
                self.current_note = None
                self.edit_tab.textChanged.disconnect()
                self.edit_tab.clear()
                self.edit_tab.textChanged.connect(self.on_text_changed)
                self.preview_tab.clear()
                self.update_window_title()

            self.load_notes()

            search_text = self.search_input.text()
            if search_text.strip():
                self.notes_list.filter_notes(search_text)

    def load_notes(self):
        notes = self.db_manager.get_all_notes()
        self.notes_list.set_all_notes(notes)
        self.notes_list.clear()

        for title, created_at, updated_at in notes:
            item = QListWidgetItem()
            widget = NoteItemWidget(title, created_at, updated_at)
            item.setSizeHint(widget.sizeHint())
            self.notes_list.addItem(item)
            self.notes_list.setItemWidget(item, widget)

        if notes:
            self.notes_list.setCurrentRow(0)

    def load_note(self, index):
        if index >= 0:
            self.save_current_note()

            item = self.notes_list.item(index)
            widget = self.notes_list.itemWidget(item)
            title = widget.findChild(QLabel, "noteTitle").text()
            content = self.db_manager.load_note(title)
            self.current_note = title

            self.edit_tab.textChanged.disconnect()
            self.edit_tab.setPlainText(content)
            self.edit_tab.textChanged.connect(self.on_text_changed)

            self.update_preview()
            self.update_window_title(title)
        else:
            self.current_note = None
            self.update_window_title()

    def save_current_note(self):
        if self.current_note:
            content = self.edit_tab.toPlainText()
            self.db_manager.save_note(self.current_note, content)

    def on_text_changed(self):
        self.auto_save_timer.stop()
        self.auto_save_timer.start(1500)
        self.update_preview()

    def auto_save(self):
        self.save_current_note()

    def update_preview(self):
        markdown_text = self.edit_tab.toPlainText()
        html = markdown.markdown(markdown_text)
        self.preview_tab.setHtml(html)

    def closeEvent(self, event):
        self.save_current_note()
        event.accept()

    def focus_search(self):
        self.search_input.setFocus()
        self.search_input.selectAll()

    def filter_notes(self, search_text):
        if search_text.strip():
            self.notes_list.filter_notes(search_text)
        else:
            self.load_notes()
