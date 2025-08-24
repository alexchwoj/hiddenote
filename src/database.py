import sqlite3
import hashlib
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64


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

        is_first_setup = result is None

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

        if is_first_setup:
            self.create_welcome_note()

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

    def create_welcome_note(self):
        welcome_content = """# Welcome to hiddenote!

Thanks for trying out hiddenote, a simple encrypted note-taking app built with Python and PyQt6.

## Getting Started

Here are some essential shortcuts to help you navigate:

### Basic Controls
- **Ctrl+N** or **Insert** - Create a new note
- **Ctrl+S** - Save current note
- **Ctrl+F** - Focus search box
- **Delete** - Delete selected note (when note is selected in list)

### Interface Tips
- **Auto-save**: Your notes automatically save after 1.5 seconds of inactivity
- **Markdown**: Write in markdown and see the preview in the Preview tab
- **Search**: Use the search box to quickly find notes by title
- **Docks**: Right-click in the main area to show/hide panels or reset layout

## Features

- **Encryption**: All your notes are encrypted with your password
- **Markdown Support**: Write formatted text with markdown syntax
- **Cross-platform**: Works on Windows, Linux, and macOS
- **Customizable Layout**: Drag and arrange panels to your liking

## Want to Contribute?

hiddenote is open source! If you'd like to help improve it, check out the repository:
https://github.com/alexchwoj/hiddenote

You can:
- Report bugs or suggest features
- Submit pull requests
- Help with documentation
- Share your experience with others

## Your Privacy

Your notes are encrypted locally using your password. No data is sent to any servers - everything stays on your device.

---

*You can delete this note anytime by selecting it and pressing Delete.*

Happy note-taking! 📝"""

        self.save_note("Welcome to hiddenote", welcome_content)
