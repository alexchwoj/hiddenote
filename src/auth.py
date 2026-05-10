from PyQt6.QtWidgets import QDialog
from .ui.dialogs import PasswordDialog, CustomMessageBox
from .database import DatabaseManager

MAX_FAILED_ATTEMPTS = 5


class AuthManager:
    def __init__(self):
        self.db_manager = None
        self.is_authenticated = False
        self.failed_attempts = 0

    def authenticate_user(self, parent=None):
        db_manager = DatabaseManager()

        if db_manager.is_first_time():
            dialog = PasswordDialog(is_new_user=True, parent=parent)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                db_manager.setup_encryption(dialog.password)
                self.db_manager = db_manager
                self.is_authenticated = True
                self.failed_attempts = 0
                return True
            return False

        return self._run_auth_loop(db_manager, parent)

    def _run_auth_loop(self, db_manager, parent):
        while self.failed_attempts < MAX_FAILED_ATTEMPTS:
            remaining = MAX_FAILED_ATTEMPTS - self.failed_attempts
            dialog = PasswordDialog(is_new_user=False, parent=parent, remaining=remaining)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return False

            if db_manager.verify_password(dialog.password):
                db_manager.setup_encryption(dialog.password)
                self.db_manager = db_manager
                self.is_authenticated = True
                self.failed_attempts = 0
                return True

            self.failed_attempts += 1
            remaining = MAX_FAILED_ATTEMPTS - self.failed_attempts

            if remaining <= 0:
                CustomMessageBox.critical(
                    parent,
                    "locked out",
                    "too many failed attempts. the app will close.",
                )
                return False

            CustomMessageBox.critical(
                parent,
                "wrong password",
                f"incorrect password. {remaining} {'attempt' if remaining == 1 else 'attempts'} remaining.",
            )

        return False

    def re_authenticate(self, parent=None):
        if self.db_manager is None:
            return False

        attempts = 0
        while attempts < MAX_FAILED_ATTEMPTS:
            remaining = MAX_FAILED_ATTEMPTS - attempts
            dialog = PasswordDialog(is_new_user=False, parent=parent, remaining=remaining)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return False

            if self.db_manager.verify_password(dialog.password):
                self.db_manager.setup_encryption(dialog.password)
                self.is_authenticated = True
                return True

            attempts += 1
            remaining = MAX_FAILED_ATTEMPTS - attempts
            if remaining <= 0:
                CustomMessageBox.critical(
                    parent,
                    "locked out",
                    "too many failed attempts. the app will close.",
                )
                return False

            CustomMessageBox.critical(
                parent,
                "wrong password",
                f"incorrect password. {remaining} {'attempt' if remaining == 1 else 'attempts'} remaining.",
            )

        return False

    def get_database_manager(self):
        return self.db_manager
