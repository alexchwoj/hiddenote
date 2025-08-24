from PyQt6.QtWidgets import QDialog
from .ui.dialogs import PasswordDialog, CustomMessageBox
from .database import DatabaseManager


class AuthManager:
    def __init__(self):
        self.db_manager = None
        self.is_authenticated = False

    def authenticate_user(self):
        db_manager = DatabaseManager()

        if db_manager.is_first_time():
            dialog = PasswordDialog(is_new_user=True)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                db_manager.setup_encryption(dialog.password)
                self.db_manager = db_manager
                self.is_authenticated = True
                return True
            return False
        else:
            dialog = PasswordDialog(is_new_user=False)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                if db_manager.verify_password(dialog.password):
                    db_manager.setup_encryption(dialog.password)
                    self.db_manager = db_manager
                    self.is_authenticated = True
                    return True
                else:
                    CustomMessageBox.critical(
                        None,
                        "wrong password",
                        "that's not the right password",
                    )
                    return False
            return False

    def get_database_manager(self):
        return self.db_manager
