"""Run with QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -v."""

import base64
import hashlib
import os
import sqlite3
import sys
import tempfile
import traceback
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from cryptography.fernet import Fernet
from PyQt6.QtCore import QEvent
from PyQt6.QtWidgets import QApplication, QMessageBox

from src.app import HiddenoteApp
from src.database import DatabaseManager


class DatabaseRegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "notes.db"

    def test_legacy_database_migrates_without_losing_credentials_or_notes(self):
        password = "legacy-password"
        salt = b"0123456789abcdef"
        key = base64.urlsafe_b64encode(
            hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000, 32)
        )
        ciphertext = Fernet(key).encrypt(b"legacy content")
        with closing(sqlite3.connect(self.path)) as conn, conn:
            conn.execute("CREATE TABLE user_auth (id INTEGER PRIMARY KEY, password_hash TEXT NOT NULL, salt BLOB NOT NULL)")
            conn.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL UNIQUE, content BLOB NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
            conn.execute("INSERT INTO user_auth VALUES (1, ?, ?)", (hashlib.sha256(password.encode()).hexdigest(), salt))
            conn.execute("INSERT INTO notes (title, content) VALUES ('Legacy', ?)", (ciphertext,))

        db = DatabaseManager(str(self.path))
        self.assertTrue(db.verify_password(password))
        db.setup_encryption(password)
        self.assertEqual(db.load_note("Legacy"), "legacy content")
        with closing(sqlite3.connect(self.path)) as conn:
            row = conn.execute("SELECT pinned, archived, in_trash, trash_date FROM notes").fetchone()
            self.assertEqual(row, (0, 0, 0, None))
            indexes = {row[1] for row in conn.execute("PRAGMA index_list(notes)")}
            self.assertTrue({"idx_notes_pinned", "idx_notes_archived", "idx_notes_trash"} <= indexes)

        reopened = DatabaseManager(str(self.path))
        self.assertTrue(reopened.verify_password(password))
        reopened.setup_encryption(password)
        self.assertEqual(reopened.load_note("Legacy"), "legacy content")

    def test_duplicate_insert_and_rename_leave_database_writable(self):
        db = DatabaseManager(str(self.path))
        db.setup_encryption("demo")
        db.create_note("One", "original")
        db.create_note("Two", "second")
        db.toggle_archive("One")
        self.assertTrue(db.note_exists("One"))
        with self.assertRaises(sqlite3.IntegrityError):
            db.create_note("One", "replacement")
        with self.assertRaises(sqlite3.IntegrityError):
            db.rename_note("Two", "One")
        # Keep the caught traceback alive while writing, as Qt may do after an error.
        try:
            db.rename_note("Two", "One")
        except sqlite3.IntegrityError as error:
            saved_error = error
        db.save_note("Two", "still writable")
        self.assertIsInstance(saved_error, sqlite3.IntegrityError)
        self.assertEqual(db.load_note("One"), "original")
        self.assertEqual(db.load_note("Two"), "still writable")


class IsolatedWindow(HiddenoteApp):
    def __init__(self, db_path):
        self.test_db_path = db_path
        super().__init__(test_mode=True)

    def show(self):
        # No native windows or application data are used by these tests.
        pass

    def _init_test_db(self):
        self.db_manager = DatabaseManager(self.test_db_path)
        self.db_manager.setup_encryption("demo")
        self.db_manager.create_note("Alpha", "original A")
        self.db_manager.create_note("Beta", "original B")
        self.auth_manager.db_manager = self.db_manager


class EditorRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt_app = QApplication.instance() or QApplication([])
        cls.qt_app.setQuitOnLastWindowClosed(False)
        cls.callback_errors = []
        cls.previous_hook = sys.excepthook
        # Fail tests on unhandled Qt callbacks instead of aborting Python on macOS.
        sys.excepthook = lambda *args: cls.callback_errors.append(
            "".join(traceback.format_exception(*args))
        )

    @classmethod
    def tearDownClass(cls):
        sys.excepthook = cls.previous_hook

    def setUp(self):
        self.callback_errors.clear()
        self.temp = tempfile.TemporaryDirectory()
        self.window = IsolatedWindow(str(Path(self.temp.name) / "notes.db"))
        self.db = self.window.db_manager
        self.window._select_note_by_title("Alpha")

    def tearDown(self):
        try:
            self.window.close()
            self.window.deleteLater()
            self.qt_app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            self.qt_app.processEvents()
        finally:
            self.temp.cleanup()
        self.assertEqual(self.callback_errors, [], "\n".join(self.callback_errors))

    def edit(self, content="pending edit"):
        self.window.edit_tab.setPlainText(content)
        self.assertTrue(self.window.auto_save_timer.isActive())

    def test_pin_and_sort_preserve_pending_edits_and_selection(self):
        self.edit()
        self.window.toggle_pin_note("Alpha")
        self.assertEqual(self.db.load_note("Alpha"), "pending edit")
        self.assertEqual(self.window.current_note, "Alpha")
        self.assertEqual(self.window.edit_tab.toPlainText(), "pending edit")
        self.edit("second edit")
        self.window.sort_combo.setCurrentIndex(2)
        self.assertEqual(self.db.load_note("Alpha"), "second edit")
        self.assertEqual(self.window.current_note, "Alpha")

    def test_search_saves_old_note_and_keeps_results_editable(self):
        self.edit()
        self.window.search_input.setText("Beta")
        self.assertEqual(self.db.load_note("Alpha"), "pending edit")
        self.assertEqual(self.window.current_note, "Beta")
        self.assertFalse(self.window.edit_tab.isReadOnly())
        self.edit("edited search result")
        self.window.auto_save()
        self.assertEqual(self.db.load_note("Beta"), "edited search result")
        self.window.toggle_pin_note("Beta")
        self.assertEqual(self.window.notes_list.count(), 1)

    def test_empty_search_results_save_and_disable_the_buffer(self):
        self.edit()
        self.window.notes_list.filter_notes("no matches")
        self.assertEqual(self.db.load_note("Alpha"), "pending edit")
        self.assertIsNone(self.window.current_note)
        self.assertEqual(self.window.edit_tab.toPlainText(), "")
        self.assertTrue(self.window.edit_tab.isReadOnly())
        self.assertFalse(self.window.auto_save_timer.isActive())
        self.window.search_input.clear()
        self.assertIsNotNone(self.window.current_note)
        self.assertFalse(self.window.edit_tab.isReadOnly())

    def test_tag_and_view_changes_save_pending_edits(self):
        self.db.set_note_tags("Beta", ["work"])
        self.window.load_notes(keep_selection=True)
        self.edit()
        self.window.tag_filter_combo.setCurrentText("work")
        self.assertEqual(self.db.load_note("Alpha"), "pending edit")
        self.assertEqual(self.window.current_note, "Beta")
        self.edit("before empty view")
        self.window._set_view("archived")
        self.assertEqual(self.db.load_note("Beta"), "before empty view")
        self.assertIsNone(self.window.current_note)
        self.assertTrue(self.window.edit_tab.isReadOnly())

    def test_archive_and_trash_preserve_pending_content(self):
        self.edit("before archive")
        self.window.toggle_archive_note("Alpha")
        self.assertEqual(self.db.load_note("Alpha"), "before archive")
        self.window._select_note_by_title("Beta")
        self.edit("before trash")
        with patch("src.app.CustomMessageBox.question", return_value=QMessageBox.StandardButton.Yes):
            self.window.handle_note_delete("Beta")
        self.assertEqual(self.db.load_note("Beta"), "before trash")

    def test_emptying_trash_does_not_resurrect_the_selected_note(self):
        self.db.trash_note("Alpha")
        self.window._set_view("trash")
        self.window._select_note_by_title("Alpha")
        self.edit("last trash edit")
        with patch("src.app.CustomMessageBox.question", return_value=QMessageBox.StandardButton.Yes):
            self.window.empty_trash()
        self.window.auto_save()
        self.assertFalse(self.db.note_exists("Alpha"))
        self.assertIsNone(self.window.current_note)
        self.assertTrue(self.window.edit_tab.isReadOnly())

    def test_hidden_titles_cannot_be_created_or_renamed_over(self):
        for hidden_view in ("archived", "trash", "tag"):
            with self.subTest(hidden_view=hidden_view):
                title = f"Hidden {hidden_view}"
                self.db.create_note(title, "keep this secret")
                if hidden_view == "archived":
                    self.db.toggle_archive(title)
                elif hidden_view == "trash":
                    self.db.trash_note(title)
                else:
                    self.db.set_note_tags("Alpha", ["visible"])
                    self.window.load_notes(keep_selection=True)
                    self.window.tag_filter_combo.setCurrentText("visible")
                self.window.load_notes(keep_selection=True)
                self.assertNotIn(title, [note[0] for note in self.window.notes_list.all_notes])
                with patch("src.app.CustomInputDialog.getText", return_value=(title, True)), patch("src.app.CustomMessageBox.warning") as warning:
                    self.window.create_new_note()
                    self.window.rename_note_dialog("Alpha")
                    self.assertEqual(warning.call_count, 2)
                self.assertEqual(self.db.load_note(title), "keep this secret")
                self.assertTrue(self.db.note_exists("Alpha"))

    def test_concurrent_title_collisions_are_handled(self):
        self.db.create_note("Duplicate", "keep")
        # Model a title inserted by another instance after the existence check.
        with patch.object(self.db, "note_exists", return_value=False), patch("src.app.CustomInputDialog.getText", return_value=("Duplicate", True)), patch("src.app.CustomMessageBox.warning") as warning:
            self.window.create_new_note()
            self.window.rename_note_dialog("Alpha")
            self.assertEqual(warning.call_count, 2)
        self.edit("save after rejected rename")
        self.window.save_current_note()
        self.assertEqual(self.db.load_note("Duplicate"), "keep")
        self.assertEqual(self.db.load_note("Alpha"), "save after rejected rename")

    def test_import_deduplicates_against_archived_and_trashed_notes(self):
        self.db.create_note("Import", "archived content")
        self.db.toggle_archive("Import")
        self.db.create_note("Import (1)", "trashed content")
        self.db.trash_note("Import (1)")
        source = Path(self.temp.name) / "Import.md"
        source.write_text("imported content", encoding="utf-8")
        self.edit()
        with patch("src.app.QFileDialog.getOpenFileName", return_value=(str(source), "")):
            self.window._import_file()
        self.assertEqual(self.db.load_note("Alpha"), "pending edit")
        self.assertEqual(self.db.load_note("Import"), "archived content")
        self.assertEqual(self.db.load_note("Import (1)"), "trashed content")
        self.assertEqual(self.db.load_note("Import (2)"), "imported content")

    def test_successful_rename_preserves_pending_edits(self):
        self.edit()
        with patch("src.app.CustomInputDialog.getText", return_value=("Renamed", True)):
            self.window.rename_note_dialog("Alpha")
        self.assertFalse(self.db.note_exists("Alpha"))
        self.assertEqual(self.db.load_note("Renamed"), "pending edit")
        self.assertEqual(self.window.current_note, "Renamed")

    def test_lock_flushes_edits_and_stops_timers_before_clearing_key(self):
        self.edit("before lock")
        def authenticate(parent):
            self.assertIsNone(self.db.cipher_suite)
            self.assertIsNone(self.window.current_note)
            self.assertEqual(self.window.edit_tab.toPlainText(), "")
            self.assertFalse(self.window.auto_save_timer.isActive())
            self.assertFalse(self.window._preview_timer.isActive())
            self.assertFalse(self.window._auto_lock_timer.isActive())
            self.db.setup_encryption("demo")
            self.assertEqual(self.db.load_note("Alpha"), "before lock")
            versions = self.db.get_note_versions("Alpha")
            self.assertIn("before lock", [self.db.load_version_content(row[0]) for row in versions])
            return True
        with patch.object(self.window.auth_manager, "re_authenticate", side_effect=authenticate):
            self.window._lock_app()
        self.assertEqual(self.db.load_note("Alpha"), "before lock")


if __name__ == "__main__":
    unittest.main()
