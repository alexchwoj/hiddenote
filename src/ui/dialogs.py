from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QDialog,
    QLineEdit,
    QPushButton,
    QLabel,
    QMessageBox,
    QFrame,
    QApplication,
)
from PyQt6.QtCore import Qt


class CustomTitleBar(QWidget):
    def __init__(self, parent=None, title="hiddenote"):
        super().__init__(parent)
        self.parent_window = parent
        self.title = title
        self.setFixedHeight(40)
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(15, 5, 15, 5)
        layout.setSpacing(0)

        self.title_label = QLabel(self.title)
        self.title_label.setObjectName("customTitleLabel")
        layout.addWidget(self.title_label)

        layout.addStretch()

        self.close_button = QPushButton("×")
        self.close_button.setObjectName("closeButton")
        self.close_button.setFixedSize(22, 22)
        self.close_button.clicked.connect(self.close_window)
        layout.addWidget(self.close_button)

        self.setLayout(layout)

        self.old_pos = None

    def close_window(self):
        if self.parent_window:
            self.parent_window.close()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.old_pos is not None and self.parent_window:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.parent_window.move(self.parent_window.pos() + delta)
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.old_pos = None

    def update_title(self, title):
        self.title = title
        self.title_label.setText(title)


class CustomMessageBox(QDialog):
    def __init__(self, parent=None, title="", message="", buttons=None):
        super().__init__(None)
        self.parent_window = parent
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.setFixedSize(400, 220)
        self.result_value = QMessageBox.StandardButton.Cancel

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.main_frame = QFrame()
        self.main_frame.setObjectName("dialogFrame")
        frame_layout = QVBoxLayout(self.main_frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(0)

        self.title_bar = CustomTitleBar(self, title)
        frame_layout.addWidget(self.title_bar)

        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(25, 20, 25, 25)
        content_layout.setSpacing(20)

        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(message_label)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        if not buttons:
            buttons = [QMessageBox.StandardButton.Ok]

        for button in buttons:
            if button == QMessageBox.StandardButton.Ok:
                btn = QPushButton("ok")
                btn.clicked.connect(
                    lambda: self.set_result(QMessageBox.StandardButton.Ok)
                )
            elif button == QMessageBox.StandardButton.Yes:
                btn = QPushButton("yes")
                btn.clicked.connect(
                    lambda: self.set_result(QMessageBox.StandardButton.Yes)
                )
            elif button == QMessageBox.StandardButton.No:
                btn = QPushButton("no")
                btn.clicked.connect(
                    lambda: self.set_result(QMessageBox.StandardButton.No)
                )
            elif button == QMessageBox.StandardButton.Cancel:
                btn = QPushButton("cancel")
                btn.clicked.connect(
                    lambda: self.set_result(QMessageBox.StandardButton.Cancel)
                )
            else:
                btn = QPushButton("ok")
                btn.clicked.connect(
                    lambda: self.set_result(QMessageBox.StandardButton.Ok)
                )

            button_layout.addWidget(btn)

        content_layout.addLayout(button_layout)
        frame_layout.addLayout(content_layout)
        main_layout.addWidget(self.main_frame)

        self.center_on_screen()

    def center_on_screen(self):
        if self.parent_window:
            parent_center = self.parent_window.geometry().center()
            screen = QApplication.screenAt(parent_center)
            if screen is None:
                screen = QApplication.primaryScreen()
            screen_geometry = screen.availableGeometry()
        else:
            screen = QApplication.primaryScreen()
            screen_geometry = screen.availableGeometry()

        x = screen_geometry.x() + (screen_geometry.width() - self.width()) // 2
        y = screen_geometry.y() + (screen_geometry.height() - self.height()) // 2
        self.move(x, y)

    def set_result(self, result):
        self.result_value = result
        self.accept()

    @staticmethod
    def warning(parent, title, message):
        dialog = CustomMessageBox(
            parent, title, message, [QMessageBox.StandardButton.Ok]
        )
        dialog.exec()
        return dialog.result_value

    @staticmethod
    def question(parent, title, message, buttons=None):
        if not buttons:
            buttons = [QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.No]
        dialog = CustomMessageBox(parent, title, message, buttons)
        dialog.exec()
        return dialog.result_value

    @staticmethod
    def critical(parent, title, message):
        dialog = CustomMessageBox(
            parent, title, message, [QMessageBox.StandardButton.Ok]
        )
        dialog.exec()
        return dialog.result_value


class CustomInputDialog(QDialog):
    def __init__(self, parent=None, title="", label="", text=""):
        super().__init__(None)
        self.parent_window = parent
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.setFixedSize(450, 250)
        self.text_value = ""
        self.ok_pressed = False

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.main_frame = QFrame()
        self.main_frame.setObjectName("dialogFrame")
        frame_layout = QVBoxLayout(self.main_frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(0)

        self.title_bar = CustomTitleBar(self, title)
        frame_layout.addWidget(self.title_bar)

        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(30, 25, 30, 30)
        content_layout.setSpacing(20)

        if label:
            label_widget = QLabel(label)
            content_layout.addWidget(label_widget)

        self.line_edit = QLineEdit(text)
        self.line_edit.returnPressed.connect(self.accept_text)
        content_layout.addWidget(self.line_edit)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        cancel_btn = QPushButton("cancel")
        cancel_btn.clicked.connect(self.reject)
        ok_btn = QPushButton("ok")
        ok_btn.clicked.connect(self.accept_text)
        ok_btn.setDefault(True)

        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(ok_btn)

        content_layout.addLayout(button_layout)
        frame_layout.addLayout(content_layout)
        main_layout.addWidget(self.main_frame)

        self.line_edit.setFocus()
        self.center_on_screen()

    def center_on_screen(self):
        if self.parent_window:
            parent_center = self.parent_window.geometry().center()
            screen = QApplication.screenAt(parent_center)
            if screen is None:
                screen = QApplication.primaryScreen()
            screen_geometry = screen.availableGeometry()
        else:
            screen = QApplication.primaryScreen()
            screen_geometry = screen.availableGeometry()

        x = screen_geometry.x() + (screen_geometry.width() - self.width()) // 2
        y = screen_geometry.y() + (screen_geometry.height() - self.height()) // 2
        self.move(x, y)

    def accept_text(self):
        self.text_value = self.line_edit.text()
        self.ok_pressed = True
        self.accept()

    @staticmethod
    def getText(parent, title, label, text=""):
        dialog = CustomInputDialog(parent, title, label, text)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.text_value, dialog.ok_pressed
        return "", False


class PasswordDialog(QDialog):
    def __init__(self, is_new_user=False, parent=None):
        super().__init__(None)
        self.parent_window = parent
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.setFixedSize(360, 200)
        self.setModal(True)
        self.is_new_user = is_new_user
        self.password = None

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.main_frame = QFrame()
        self.main_frame.setObjectName("dialogFrame")
        frame_layout = QVBoxLayout(self.main_frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(0)

        title_text = "create your password" if is_new_user else "enter password"
        self.title_bar = CustomTitleBar(self, title_text)
        frame_layout.addWidget(self.title_bar)

        content_layout = QVBoxLayout()
        content_layout.setSpacing(12)
        content_layout.setContentsMargins(20, 10, 20, 20)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("your password...")
        self.password_input.returnPressed.connect(self.accept_password)
        content_layout.addWidget(self.password_input)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        cancel_button = QPushButton("bye")
        cancel_button.clicked.connect(self.reject)
        ok_button = QPushButton("ok")
        ok_button.clicked.connect(self.accept_password)
        ok_button.setDefault(True)

        button_layout.addWidget(cancel_button)
        button_layout.addWidget(ok_button)
        content_layout.addLayout(button_layout)

        frame_layout.addLayout(content_layout)
        main_layout.addWidget(self.main_frame)

        self.setLayout(main_layout)
        self.password_input.setFocus()
        self.center_on_screen()

    def center_on_screen(self):
        if self.parent_window:
            parent_center = self.parent_window.geometry().center()
            screen = QApplication.screenAt(parent_center)
            if screen is None:
                screen = QApplication.primaryScreen()
            screen_geometry = screen.availableGeometry()
        else:
            screen = QApplication.primaryScreen()
            screen_geometry = screen.availableGeometry()

        x = screen_geometry.x() + (screen_geometry.width() - self.width()) // 2
        y = screen_geometry.y() + (screen_geometry.height() - self.height()) // 2
        self.move(x, y)

    def accept_password(self):
        self.password = self.password_input.text()
        if self.password:
            self.accept()
        else:
            CustomMessageBox.warning(self, "oops", "password can't be empty")
