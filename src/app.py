import sys
import markdown
from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QTextBrowser,
    QTabWidget,
    QFrame,
    QListWidgetItem,
    QLabel,
    QMessageBox,
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QShortcut, QKeySequence

from .auth import AuthManager
from .ui.dialogs import CustomTitleBar, CustomInputDialog, CustomMessageBox
from .ui.widgets import NoteListWidget, NoteItemWidget


class HiddenoteApp(QWidget):
    def __init__(self):
        super().__init__()
        self.auth_manager = AuthManager()
        self.db_manager = None
        self.current_note = None

        if not self.auth_manager.authenticate_user():
            sys.exit()

        self.db_manager = self.auth_manager.get_database_manager()
        self.init_ui()
        self.setup_shortcuts()
        self.setup_auto_save()
        self.load_notes()

    def init_ui(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setGeometry(100, 100, 1200, 800)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.main_frame = QFrame()
        self.main_frame.setObjectName("mainFrame")
        frame_layout = QVBoxLayout(self.main_frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(0)

        self.title_bar = CustomTitleBar(self, "hiddenote")
        frame_layout.addWidget(self.title_bar)

        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(1)

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

        editor_frame = QFrame()
        editor_frame.setObjectName("editorFrame")
        editor_layout = QVBoxLayout(editor_frame)

        self.tabs = QTabWidget()
        self.edit_tab = QTextEdit()
        self.preview_tab = QTextBrowser()

        self.tabs.addTab(self.edit_tab, "edit")
        self.tabs.addTab(self.preview_tab, "preview")
        self.tabs.currentChanged.connect(self.update_preview)

        editor_layout.addWidget(self.tabs)

        content_layout.addWidget(sidebar)
        content_layout.addWidget(editor_frame)

        frame_layout.addLayout(content_layout)
        main_layout.addWidget(self.main_frame)

        self.edit_tab.textChanged.connect(self.on_text_changed)

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

        if self.tabs.currentWidget() == self.preview_tab:
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
