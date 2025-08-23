import sys
import sqlite3
import hashlib
import os
import markdown
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QListWidget,
    QTextEdit,
    QTextBrowser,
    QTabWidget,
    QDialog,
    QLineEdit,
    QPushButton,
    QLabel,
    QMessageBox,
    QInputDialog,
    QFrame,
    QListWidgetItem,
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QShortcut, QKeySequence, QFont, QFontDatabase


class PasswordDialog(QDialog):
    def __init__(self, is_new_user=False):
        super().__init__()
        self.setWindowTitle("hiddenote")
        self.setFixedSize(320, 160)
        self.setModal(True)
        self.is_new_user = is_new_user
        self.password = None

        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        title_label = QLabel(
            "create your password" if is_new_user else "enter password"
        )
        title_label.setObjectName("titleLabel")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("your password...")
        self.password_input.returnPressed.connect(self.accept_password)
        layout.addWidget(self.password_input)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        cancel_button = QPushButton("cancel")
        cancel_button.clicked.connect(self.reject)
        ok_button = QPushButton("ok")
        ok_button.clicked.connect(self.accept_password)
        ok_button.setDefault(True)

        button_layout.addWidget(cancel_button)
        button_layout.addWidget(ok_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.password_input.setFocus()

    def accept_password(self):
        self.password = self.password_input.text()
        if self.password:
            self.accept()
        else:
            QMessageBox.warning(self, "oops", "password can't be empty")


class DatabaseManager:
    def __init__(self, db_path="hiddenote.db"):
        self.db_path = db_path
        self.cipher_suite = None
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_auth (
                id INTEGER PRIMARY KEY,
                password_hash TEXT NOT NULL,
                salt BLOB NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL UNIQUE,
                content BLOB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def setup_encryption(self, password):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT salt FROM user_auth WHERE id = 1")
        result = cursor.fetchone()

        if result:
            salt = result[0]
        else:
            salt = os.urandom(16)
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            cursor.execute(
                "INSERT INTO user_auth (password_hash, salt) VALUES (?, ?)",
                (password_hash, salt),
            )
            conn.commit()

        conn.close()

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        self.cipher_suite = Fernet(key)

    def verify_password(self, password):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM user_auth WHERE id = 1")
        result = cursor.fetchone()
        conn.close()

        if result:
            stored_hash = result[0]
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            return stored_hash == password_hash
        return False

    def is_first_time(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM user_auth")
        count = cursor.fetchone()[0]
        conn.close()
        return count == 0

    def encrypt_content(self, content):
        return self.cipher_suite.encrypt(content.encode())

    def decrypt_content(self, encrypted_content):
        return self.cipher_suite.decrypt(encrypted_content).decode()

    def save_note(self, title, content):
        encrypted_content = self.encrypt_content(content)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM notes WHERE title = ?", (title,))
        existing = cursor.fetchone()

        if existing:
            cursor.execute(
                "UPDATE notes SET content = ?, updated_at = CURRENT_TIMESTAMP WHERE title = ?",
                (encrypted_content, title),
            )
        else:
            cursor.execute(
                "INSERT INTO notes (title, content) VALUES (?, ?)",
                (title, encrypted_content),
            )

        conn.commit()
        conn.close()

    def load_note(self, title):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT content FROM notes WHERE title = ?", (title,))
        result = cursor.fetchone()
        conn.close()

        if result:
            return self.decrypt_content(result[0])
        return ""

    def get_all_notes(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT title, created_at, updated_at FROM notes ORDER BY updated_at DESC"
        )
        notes = cursor.fetchall()
        conn.close()
        return notes

    def delete_note(self, title):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM notes WHERE title = ?", (title,))
        conn.commit()
        conn.close()


class NoteItemWidget(QWidget):
    def __init__(self, title, created_at, updated_at):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(2)

        title_label = QLabel(title)
        title_label.setObjectName("noteTitle")
        layout.addWidget(title_label)

        created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00")).replace(
            tzinfo=None
        )
        updated_dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00")).replace(
            tzinfo=None
        )

        created_label = QLabel(f"created: {created_dt.strftime('%m/%d/%Y %H:%M')}")
        created_label.setObjectName("noteDate")
        layout.addWidget(created_label)

        updated_label = QLabel(f"updated: {updated_dt.strftime('%m/%d/%Y %H:%M')}")
        updated_label.setObjectName("noteDate")
        layout.addWidget(updated_label)

        self.setLayout(layout)


class NoteListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.all_notes = []

    def set_all_notes(self, notes):
        self.all_notes = notes

    def filter_notes(self, search_text):
        self.clear()
        for title, created_at, updated_at in self.all_notes:
            if search_text.lower() in title.lower():
                item = QListWidgetItem()
                widget = NoteItemWidget(title, created_at, updated_at)
                item.setSizeHint(widget.sizeHint())
                self.addItem(item)
                self.setItemWidget(item, widget)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            current_item = self.currentItem()
            if current_item:
                widget = self.itemWidget(current_item)
                title = widget.findChild(QLabel, "noteTitle").text()
                self.parent_app.delete_note(title)
        else:
            super().keyPressEvent(event)


class HiddeNoteApp(QWidget):
    def __init__(self):
        super().__init__()
        self.db_manager = None
        self.current_note = None
        self.is_authenticated = False

        if not self.authenticate_user():
            sys.exit()

        self.init_ui()
        self.setup_shortcuts()
        self.setup_auto_save()
        self.load_notes()

    def authenticate_user(self):
        db_manager = DatabaseManager()

        if db_manager.is_first_time():
            dialog = PasswordDialog(is_new_user=True)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                db_manager.setup_encryption(dialog.password)
                self.db_manager = db_manager
                return True
            return False
        else:
            dialog = PasswordDialog(is_new_user=False)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                if db_manager.verify_password(dialog.password):
                    db_manager.setup_encryption(dialog.password)
                    self.db_manager = db_manager
                    return True
                else:
                    QMessageBox.critical(
                        None,
                        "wrong password",
                        "that's not the right password",
                    )
                    return False
            return False

    def init_ui(self):
        self.setWindowTitle("hiddenote")
        self.setGeometry(100, 100, 1200, 800)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(1)

        sidebar = QFrame()
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
        editor_layout = QVBoxLayout(editor_frame)

        self.tabs = QTabWidget()
        self.edit_tab = QTextEdit()
        self.preview_tab = QTextBrowser()

        self.tabs.addTab(self.edit_tab, "edit")
        self.tabs.addTab(self.preview_tab, "preview")
        self.tabs.currentChanged.connect(self.update_preview)

        editor_layout.addWidget(self.tabs)

        main_layout.addWidget(sidebar)
        main_layout.addWidget(editor_frame)

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

    def create_new_note(self):
        title, ok = QInputDialog.getText(self, "new note", "what should we call it?")
        if ok and title.strip():
            title = title.strip()
            existing_titles = []

            for title_data, _, _ in self.notes_list.all_notes:
                existing_titles.append(title_data)

            if title in existing_titles:
                QMessageBox.warning(
                    self, "hmm", "you already have a note with that name"
                )
                return

            self.save_current_note()
            self.db_manager.save_note(title, "")
            self.load_notes()

    def delete_note(self, title):
        reply = QMessageBox.question(
            self,
            "delete note",
            f"sure you want to delete '{title}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.db_manager.delete_note(title)

            if title == self.current_note:
                self.current_note = None
                self.edit_tab.textChanged.disconnect()
                self.edit_tab.clear()
                self.edit_tab.textChanged.connect(self.on_text_changed)
                self.preview_tab.clear()

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


def load_custom_fonts():
    font_dir = os.path.join(os.path.dirname(__file__), "assets", "fonts")

    if not os.path.exists(font_dir):
        return None

    font_files = [
        f for f in os.listdir(font_dir) if f.lower().endswith((".ttf", ".otf"))
    ]

    if not font_files:
        return None

    loaded_families = {}

    for filename in font_files:
        font_path = os.path.join(font_dir, filename)
        font_id = QFontDatabase.addApplicationFont(font_path)

        if font_id != -1:
            font_families = QFontDatabase.applicationFontFamilies(font_id)
            for family in font_families:
                if family not in loaded_families:
                    loaded_families[family] = []
                loaded_families[family].append(filename.lower())

    for family, files in loaded_families.items():
        for preferred in ["regular", "normal", "medium"]:
            for file in files:
                if preferred in file:
                    return family
        return family

    return None


def apply_theme(app, custom_font_family=None):
    font_family = (
        f"'{custom_font_family}', 'Cascadia Code', monospace"
        if custom_font_family
        else "'Cascadia Code', monospace"
    )

    app.setStyleSheet(f"""
        QWidget {{
            background-color: #1E1E1E;
            color: #D4D4D4;
            font-family: {font_family};
            font-size: 12px;
            font-weight: 400;
        }}
        
        QLabel {{
            color: #CCCCCC;
            font-weight: 400;
            padding: 2px;
            background: transparent;
            border: none;
        }}
        
        QLabel#titleLabel {{
            color: #FFFFFF;
            font-size: 15px;
            font-weight: 600;
            padding: 8px;
            margin-bottom: 4px;
            background: transparent;
            font-family: {font_family};
        }}
        
        QDialog {{
            background-color: #2D2D30;
            border: 1px solid #3F3F46;
        }}
        
        QFrame {{
            background-color: #252526;
            border: none;
        }}
        
        QPushButton {{
            background-color: #0E639C;
            color: #FFFFFF;
            border: none;
            padding: 8px 16px;
            min-width: 80px;
            font-weight: 500;
            font-family: {font_family};
        }}
        
        QPushButton:hover {{
            background-color: #1177BB;
        }}
        
        QPushButton:pressed {{
            background-color: #094771;
        }}
        
        QPushButton:default {{
            background-color: #0E639C;
            border: 2px solid #1177BB;
        }}
        
        QLineEdit {{
            background-color: #3C3C3C;
            color: #D4D4D4;
            border: 1px solid #3F3F46;
            padding: 8px;
            font-size: 13px;
            font-weight: 400;
            font-family: {font_family};
        }}
        
        QLineEdit:focus {{
            border: 1px solid #0E639C;
        }}
        
        QLineEdit[placeholderText] {{
            color: #8C8C8C;
        }}
        
        QListWidget {{
            background-color: #252526;
            color: #D4D4D4;
            border: none;
            outline: none;
            font-weight: 400;
            font-family: {font_family};
        }}
        
        QListWidget::item {{
            padding: 0px;
            border: none;
            background: transparent;
        }}
        
        QListWidget::item:selected {{
            background-color: #094771;
        }}
        
        QListWidget::item:hover {{
            background-color: #2A2D2E;
        }}
        
        QTextEdit, QTextBrowser {{
            background-color: #1E1E1E;
            color: #D4D4D4;
            border: none;
            font-family: {font_family};
            font-size: 13px;
            font-weight: 400;
            line-height: 1.4;
        }}
        
        QTabWidget::pane {{
            border: 1px solid #3F3F46;
            background-color: #1E1E1E;
        }}
        
        QTabBar::tab {{
            background-color: #2D2D30;
            color: #D4D4D4;
            padding: 8px 16px;
            border: none;
            font-weight: 400;
            font-family: {font_family};
        }}
        
        QTabBar::tab:selected {{
            background-color: #1E1E1E;
            border-bottom: 2px solid #0E639C;
        }}
        
        QTabBar::tab:hover {{
            background-color: #3C3C3C;
        }}
        
        QScrollBar:vertical {{
            background-color: #1E1E1E;
            width: 14px;
        }}
        
        QScrollBar::handle:vertical {{
            background-color: #3E3E42;
            border-radius: 7px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background-color: #4E4E52;
        }}
        
        QMessageBox {{
            background-color: #2D2D30;
            color: #D4D4D4;
        }}
        
        QMessageBox QLabel {{
            color: #D4D4D4;
            background: transparent;
            font-weight: 400;
            font-family: {font_family};
        }}
        
        QInputDialog {{
            background-color: #2D2D30;
            color: #D4D4D4;
        }}
        
        QInputDialog QLabel {{
            color: #D4D4D4;
            background: transparent;
            font-weight: 400;
            font-family: {font_family};
        }}
        
        QLabel#noteTitle {{
            color: #FFFFFF;
            font-size: 12px;
            font-weight: 600;
            font-family: {font_family};
            background: transparent;
        }}
        
        QLabel#noteDate {{
            color: #8C8C8C;
            font-size: 10px;
            font-weight: 400;
            font-family: {font_family};
            background: transparent;
        }}
    """)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    custom_font_family = load_custom_fonts()
    apply_theme(app, custom_font_family)

    if custom_font_family:
        font = QFont(custom_font_family, 10, QFont.Weight.Normal)
    else:
        font = QFont("Cascadia Code", 10)
        if not font.exactMatch():
            font = QFont("Cascadia Mono", 10)
            if not font.exactMatch():
                font = QFont("Consolas", 10)

    app.setFont(font)

    editor = HiddeNoteApp()
    editor.show()
    sys.exit(app.exec())
