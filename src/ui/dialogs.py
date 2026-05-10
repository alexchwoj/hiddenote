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
    QListWidget,
    QListWidgetItem,
    QTextEdit,
    QSplitter,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QScrollArea,
    QMenu,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QTextCursor


class StyledMenu(QMenu):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)


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

        btn_map = {
            QMessageBox.StandardButton.Ok: ("ok", QMessageBox.StandardButton.Ok),
            QMessageBox.StandardButton.Yes: ("yes", QMessageBox.StandardButton.Yes),
            QMessageBox.StandardButton.No: ("no", QMessageBox.StandardButton.No),
            QMessageBox.StandardButton.Cancel: ("cancel", QMessageBox.StandardButton.Cancel),
        }

        for button in buttons:
            label, result = btn_map.get(button, ("ok", QMessageBox.StandardButton.Ok))
            btn = QPushButton(label)
            btn.clicked.connect(lambda _, r=result: self.set_result(r))
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
        else:
            screen = QApplication.primaryScreen()
        geo = screen.availableGeometry()
        self.move(
            geo.x() + (geo.width() - self.width()) // 2,
            geo.y() + (geo.height() - self.height()) // 2,
        )

    def set_result(self, result):
        self.result_value = result
        self.accept()

    @staticmethod
    def warning(parent, title, message):
        d = CustomMessageBox(parent, title, message, [QMessageBox.StandardButton.Ok])
        d.exec()
        return d.result_value

    @staticmethod
    def question(parent, title, message, buttons=None):
        if not buttons:
            buttons = [QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.No]
        d = CustomMessageBox(parent, title, message, buttons)
        d.exec()
        return d.result_value

    @staticmethod
    def critical(parent, title, message):
        d = CustomMessageBox(parent, title, message, [QMessageBox.StandardButton.Ok])
        d.exec()
        return d.result_value


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
            content_layout.addWidget(QLabel(label))

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
        else:
            screen = QApplication.primaryScreen()
        geo = screen.availableGeometry()
        self.move(
            geo.x() + (geo.width() - self.width()) // 2,
            geo.y() + (geo.height() - self.height()) // 2,
        )

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
    def __init__(self, is_new_user=False, parent=None, remaining=None):
        super().__init__(None)
        self.parent_window = parent
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.is_new_user = is_new_user
        self.password = None

        height = 260 if is_new_user else (230 if remaining is not None and remaining < 5 else 200)
        self.setFixedSize(360, height)

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

        if is_new_user:
            self.confirm_input = QLineEdit()
            self.confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.confirm_input.setPlaceholderText("confirm password...")
            self.confirm_input.returnPressed.connect(self.accept_password)
            content_layout.addWidget(self.confirm_input)
        else:
            self.confirm_input = None

        if remaining is not None and remaining < 5:
            warn = QLabel(f"  {remaining} {'attempt' if remaining == 1 else 'attempts'} remaining")
            warn.setStyleSheet("color: #FF6B6B; font-size: 13px; padding: 0;")
            content_layout.addWidget(warn)

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
        else:
            screen = QApplication.primaryScreen()
        geo = screen.availableGeometry()
        self.move(
            geo.x() + (geo.width() - self.width()) // 2,
            geo.y() + (geo.height() - self.height()) // 2,
        )

    def accept_password(self):
        pwd = self.password_input.text()
        if not pwd:
            CustomMessageBox.warning(self, "oops", "password can't be empty")
            return
        if self.is_new_user and self.confirm_input:
            if pwd != self.confirm_input.text():
                CustomMessageBox.warning(self, "oops", "passwords don't match")
                return
        self.password = pwd
        self.accept()


class FindReplaceDialog(QDialog):
    find_requested = pyqtSignal(str, bool, bool)
    replace_requested = pyqtSignal(str, str, bool)
    replace_all_requested = pyqtSignal(str, str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(480, 230)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.main_frame = QFrame()
        self.main_frame.setObjectName("dialogFrame")
        frame_layout = QVBoxLayout(self.main_frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)

        self.title_bar = CustomTitleBar(self, "find & replace")
        frame_layout.addWidget(self.title_bar)

        content = QVBoxLayout()
        content.setContentsMargins(20, 16, 20, 20)
        content.setSpacing(10)

        find_row = QHBoxLayout()
        find_row.addWidget(QLabel("find:"))
        self.find_input = QLineEdit()
        self.find_input.setPlaceholderText("search text...")
        self.find_input.returnPressed.connect(self._find_next)
        find_row.addWidget(self.find_input)
        content.addLayout(find_row)

        replace_row = QHBoxLayout()
        replace_row.addWidget(QLabel("replace:"))
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("replacement...")
        replace_row.addWidget(self.replace_input)
        content.addLayout(replace_row)

        options_row = QHBoxLayout()
        self.case_check = QCheckBox("case sensitive")
        options_row.addWidget(self.case_check)
        options_row.addStretch()

        self.result_label = QLabel("")
        self.result_label.setStyleSheet("color: #6C6F7E; font-size: 13px;")
        options_row.addWidget(self.result_label)
        content.addLayout(options_row)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        for label, slot in [
            ("prev", self._find_prev),
            ("next", self._find_next),
            ("replace", self._replace),
            ("replace all", self._replace_all),
        ]:
            btn = QPushButton(label)
            btn.clicked.connect(slot)
            btn_row.addWidget(btn)

        content.addLayout(btn_row)
        frame_layout.addLayout(content)
        main_layout.addWidget(self.main_frame)

        self.center_on_parent()

    def center_on_parent(self):
        parent = self.parent()
        if parent:
            center = parent.geometry().center()
            screen = QApplication.screenAt(center)
            if screen is None:
                screen = QApplication.primaryScreen()
        else:
            screen = QApplication.primaryScreen()
        geo = screen.availableGeometry()
        self.move(
            geo.x() + (geo.width() - self.width()) // 2,
            geo.y() + (geo.height() - self.height()) // 2,
        )

    def _find_next(self):
        self.find_requested.emit(
            self.find_input.text(), True, self.case_check.isChecked()
        )

    def _find_prev(self):
        self.find_requested.emit(
            self.find_input.text(), False, self.case_check.isChecked()
        )

    def _replace(self):
        self.replace_requested.emit(
            self.find_input.text(),
            self.replace_input.text(),
            self.case_check.isChecked(),
        )

    def _replace_all(self):
        self.replace_all_requested.emit(
            self.find_input.text(),
            self.replace_input.text(),
            self.case_check.isChecked(),
        )

    def show_result(self, text):
        self.result_label.setText(text)

    def focus_find(self):
        self.find_input.setFocus()
        self.find_input.selectAll()
        self.show()
        self.raise_()


class ChangePasswordDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(None)
        self.parent_window = parent
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.setFixedSize(380, 300)
        self.old_password = None
        self.new_password = None

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.main_frame = QFrame()
        self.main_frame.setObjectName("dialogFrame")
        frame_layout = QVBoxLayout(self.main_frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)

        self.title_bar = CustomTitleBar(self, "change password")
        frame_layout.addWidget(self.title_bar)

        content = QVBoxLayout()
        content.setContentsMargins(24, 16, 24, 24)
        content.setSpacing(12)

        self.old_input = QLineEdit()
        self.old_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.old_input.setPlaceholderText("current password...")
        content.addWidget(self.old_input)

        self.new_input = QLineEdit()
        self.new_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_input.setPlaceholderText("new password...")
        content.addWidget(self.new_input)

        self.confirm_input = QLineEdit()
        self.confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_input.setPlaceholderText("confirm new password...")
        self.confirm_input.returnPressed.connect(self.accept_change)
        content.addWidget(self.confirm_input)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        cancel_btn = QPushButton("cancel")
        cancel_btn.clicked.connect(self.reject)
        ok_btn = QPushButton("change")
        ok_btn.clicked.connect(self.accept_change)
        ok_btn.setDefault(True)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(ok_btn)
        content.addLayout(btn_row)

        frame_layout.addLayout(content)
        main_layout.addWidget(self.main_frame)
        self.old_input.setFocus()
        self._center()

    def _center(self):
        if self.parent_window:
            center = self.parent_window.geometry().center()
            screen = QApplication.screenAt(center)
            if screen is None:
                screen = QApplication.primaryScreen()
        else:
            screen = QApplication.primaryScreen()
        geo = screen.availableGeometry()
        self.move(
            geo.x() + (geo.width() - self.width()) // 2,
            geo.y() + (geo.height() - self.height()) // 2,
        )

    def accept_change(self):
        old = self.old_input.text()
        new = self.new_input.text()
        confirm = self.confirm_input.text()

        if not old or not new:
            CustomMessageBox.warning(self, "oops", "all fields are required")
            return
        if new != confirm:
            CustomMessageBox.warning(self, "oops", "new passwords don't match")
            return
        if len(new) < 4:
            CustomMessageBox.warning(self, "oops", "password must be at least 4 characters")
            return

        self.old_password = old
        self.new_password = new
        self.accept()


class TagsDialog(QDialog):
    def __init__(self, current_tags, all_tags, parent=None):
        super().__init__(None)
        self.parent_window = parent
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.setFixedSize(400, 320)
        self.selected_tags = list(current_tags)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.main_frame = QFrame()
        self.main_frame.setObjectName("dialogFrame")
        frame_layout = QVBoxLayout(self.main_frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)

        self.title_bar = CustomTitleBar(self, "manage tags")
        frame_layout.addWidget(self.title_bar)

        content = QVBoxLayout()
        content.setContentsMargins(24, 16, 24, 24)
        content.setSpacing(12)

        add_row = QHBoxLayout()
        self.tag_input = QLineEdit()
        self.tag_input.setPlaceholderText("add tag...")
        self.tag_input.returnPressed.connect(self._add_tag)
        add_row.addWidget(self.tag_input)
        add_btn = QPushButton("+")
        add_btn.setFixedWidth(40)
        add_btn.clicked.connect(self._add_tag)
        add_row.addWidget(add_btn)
        content.addLayout(add_row)

        self.tag_list = QListWidget()
        self.tag_list.setFixedHeight(140)
        all_known = sorted(set(all_tags) | set(current_tags))
        for tag in all_known:
            item = QListWidgetItem(tag)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked if tag in self.selected_tags else Qt.CheckState.Unchecked
            )
            self.tag_list.addItem(item)
        content.addWidget(self.tag_list)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        cancel_btn = QPushButton("cancel")
        cancel_btn.clicked.connect(self.reject)
        ok_btn = QPushButton("save")
        ok_btn.clicked.connect(self._save)
        ok_btn.setDefault(True)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(ok_btn)
        content.addLayout(btn_row)

        frame_layout.addLayout(content)
        main_layout.addWidget(self.main_frame)
        self._center()

    def _center(self):
        if self.parent_window:
            center = self.parent_window.geometry().center()
            screen = QApplication.screenAt(center)
            if screen is None:
                screen = QApplication.primaryScreen()
        else:
            screen = QApplication.primaryScreen()
        geo = screen.availableGeometry()
        self.move(
            geo.x() + (geo.width() - self.width()) // 2,
            geo.y() + (geo.height() - self.height()) // 2,
        )

    def _add_tag(self):
        name = self.tag_input.text().strip()
        if not name:
            return
        existing = [
            self.tag_list.item(i).text()
            for i in range(self.tag_list.count())
        ]
        if name not in existing:
            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self.tag_list.addItem(item)
        else:
            for i in range(self.tag_list.count()):
                if self.tag_list.item(i).text() == name:
                    self.tag_list.item(i).setCheckState(Qt.CheckState.Checked)
        self.tag_input.clear()

    def _save(self):
        self.selected_tags = [
            self.tag_list.item(i).text()
            for i in range(self.tag_list.count())
            if self.tag_list.item(i).checkState() == Qt.CheckState.Checked
        ]
        self.accept()


class VersionHistoryDialog(QDialog):
    def __init__(self, versions, db_manager, parent=None):
        super().__init__(None)
        self.parent_window = parent
        self.db_manager = db_manager
        self.versions = versions
        self.restored_content = None

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.setFixedSize(700, 500)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.main_frame = QFrame()
        self.main_frame.setObjectName("dialogFrame")
        frame_layout = QVBoxLayout(self.main_frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)

        self.title_bar = CustomTitleBar(self, "version history")
        frame_layout.addWidget(self.title_bar)

        content = QVBoxLayout()
        content.setContentsMargins(20, 16, 20, 20)
        content.setSpacing(12)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.version_list = QListWidget()
        self.version_list.setFixedWidth(200)
        for v_id, saved_at in versions:
            self.version_list.addItem(QListWidgetItem(f"{saved_at}"))
        self.version_list.currentRowChanged.connect(self._preview_version)
        splitter.addWidget(self.version_list)

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        splitter.addWidget(self.preview)

        content.addWidget(splitter)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        close_btn = QPushButton("close")
        close_btn.clicked.connect(self.reject)
        self.restore_btn = QPushButton("restore this version")
        self.restore_btn.clicked.connect(self._restore)
        self.restore_btn.setEnabled(False)
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        btn_row.addWidget(self.restore_btn)
        content.addLayout(btn_row)

        frame_layout.addLayout(content)
        main_layout.addWidget(self.main_frame)

        if versions:
            self.version_list.setCurrentRow(0)

        self._center()

    def _center(self):
        if self.parent_window:
            center = self.parent_window.geometry().center()
            screen = QApplication.screenAt(center)
            if screen is None:
                screen = QApplication.primaryScreen()
        else:
            screen = QApplication.primaryScreen()
        geo = screen.availableGeometry()
        self.move(
            geo.x() + (geo.width() - self.width()) // 2,
            geo.y() + (geo.height() - self.height()) // 2,
        )

    def _preview_version(self, row):
        if row < 0 or row >= len(self.versions):
            return
        v_id = self.versions[row][0]
        content = self.db_manager.load_version_content(v_id)
        self.preview.setPlainText(content)
        self.restore_btn.setEnabled(True)

    def _restore(self):
        row = self.version_list.currentRow()
        if row < 0 or row >= len(self.versions):
            return
        v_id = self.versions[row][0]
        self.restored_content = self.db_manager.load_version_content(v_id)
        self.accept()


class StatisticsDialog(QDialog):
    def __init__(self, stats, parent=None):
        super().__init__(None)
        self.parent_window = parent
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.setFixedSize(400, 420)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.main_frame = QFrame()
        self.main_frame.setObjectName("dialogFrame")
        frame_layout = QVBoxLayout(self.main_frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)

        self.title_bar = CustomTitleBar(self, "statistics")
        frame_layout.addWidget(self.title_bar)

        content = QVBoxLayout()
        content.setContentsMargins(28, 24, 28, 28)
        content.setSpacing(14)

        def fmt_date(raw):
            if not raw:
                return "—"
            try:
                dt = raw.split(".")[0]
                return dt.replace("T", "  ")
            except Exception:
                return str(raw)

        simple_rows = [
            ("notes", str(stats.get("total", 0))),
            ("pinned", str(stats.get("pinned", 0))),
            ("archived", str(stats.get("archived", 0))),
            ("in trash", str(stats.get("trash", 0))),
            ("tags", str(stats.get("tags", 0))),
            ("saved versions", str(stats.get("versions", 0))),
        ]

        date_rows = [
            ("oldest note", fmt_date(stats.get("oldest"))),
            ("last updated", fmt_date(stats.get("last_updated"))),
        ]

        for label, value in simple_rows:
            row = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #6C6F7E;")
            val = QLabel(value)
            val.setAlignment(Qt.AlignmentFlag.AlignRight)
            row.addWidget(lbl)
            row.addStretch()
            row.addWidget(val)
            content.addLayout(row)

        for label, value in date_rows:
            block = QVBoxLayout()
            block.setSpacing(2)
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #6C6F7E;")
            val = QLabel(value)
            val.setStyleSheet("color: #E6E6E6; font-size: 13px;")
            block.addWidget(lbl)
            block.addWidget(val)
            content.addLayout(block)

        frame_layout.addLayout(content)
        main_layout.addWidget(self.main_frame)
        self._center()

    def _center(self):
        if self.parent_window:
            center = self.parent_window.geometry().center()
            screen = QApplication.screenAt(center)
            if screen is None:
                screen = QApplication.primaryScreen()
        else:
            screen = QApplication.primaryScreen()
        geo = screen.availableGeometry()
        self.move(
            geo.x() + (geo.width() - self.width()) // 2,
            geo.y() + (geo.height() - self.height()) // 2,
        )


class SettingsDialog(QDialog):
    def __init__(self, db_manager, parent=None):
        super().__init__(None)
        self.parent_window = parent
        self.db_manager = db_manager
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.setFixedSize(400, 460)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.main_frame = QFrame()
        self.main_frame.setObjectName("dialogFrame")
        frame_layout = QVBoxLayout(self.main_frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)

        self.title_bar = CustomTitleBar(self, "settings")
        frame_layout.addWidget(self.title_bar)

        content = QVBoxLayout()
        content.setContentsMargins(28, 24, 28, 28)
        content.setSpacing(6)

        lock_lbl = QLabel("auto-lock after inactivity:")
        lock_lbl.setStyleSheet("color: #6C6F7E; font-size: 13px;")
        content.addWidget(lock_lbl)
        self.lock_combo = QComboBox()
        self.lock_combo.addItems(["disabled", "5 minutes", "10 minutes", "30 minutes", "1 hour"])
        lock_values = {"0": 0, "5": 1, "10": 2, "30": 3, "60": 4}
        saved = db_manager.get_setting("auto_lock_minutes", "0")
        self.lock_combo.setCurrentIndex(lock_values.get(str(saved), 0))
        content.addWidget(self.lock_combo)

        content.addSpacing(16)

        trash_lbl = QLabel("auto-clean trash after:")
        trash_lbl.setStyleSheet("color: #6C6F7E; font-size: 13px;")
        content.addWidget(trash_lbl)
        self.trash_combo = QComboBox()
        self.trash_combo.addItems(["never", "7 days", "30 days", "90 days"])
        trash_values = {"0": 0, "7": 1, "30": 2, "90": 3}
        saved_trash = db_manager.get_setting("trash_clean_days", "30")
        self.trash_combo.setCurrentIndex(trash_values.get(str(saved_trash), 2))
        content.addWidget(self.trash_combo)

        content.addSpacing(8)
        content.addWidget(self._separator())
        content.addSpacing(8)

        change_pwd_btn = QPushButton("change password...")
        change_pwd_btn.clicked.connect(self._change_password)
        content.addWidget(change_pwd_btn)

        content.addSpacing(8)
        content.addWidget(self._separator())
        content.addSpacing(8)

        backup_btn = QPushButton("backup database now")
        backup_btn.clicked.connect(self._backup_now)
        content.addWidget(backup_btn)

        content.addStretch()

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        cancel_btn = QPushButton("cancel")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("save")
        save_btn.clicked.connect(self._save)
        save_btn.setDefault(True)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        content.addLayout(btn_row)

        frame_layout.addLayout(content)
        main_layout.addWidget(self.main_frame)
        self._center()

    def _separator(self):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background: #35384A; max-height: 1px; border: none;")
        return line

    def _center(self):
        if self.parent_window:
            center = self.parent_window.geometry().center()
            screen = QApplication.screenAt(center)
            if screen is None:
                screen = QApplication.primaryScreen()
        else:
            screen = QApplication.primaryScreen()
        geo = screen.availableGeometry()
        self.move(
            geo.x() + (geo.width() - self.width()) // 2,
            geo.y() + (geo.height() - self.height()) // 2,
        )

    def _change_password(self):
        dialog = ChangePasswordDialog(parent=self.parent_window)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if self.db_manager.change_password(dialog.old_password, dialog.new_password):
                CustomMessageBox.warning(
                    self.parent_window, "done", "password changed successfully"
                )
            else:
                CustomMessageBox.critical(
                    self.parent_window, "error", "current password is incorrect"
                )

    def _backup_now(self):
        path, _ = QFileDialog.getSaveFileName(
            None,
            "save backup",
            "hiddenote_backup.db",
            "Database (*.db)",
        )
        if path:
            try:
                self.db_manager.backup_database(path)
                CustomMessageBox.warning(
                    self.parent_window, "done", f"backup saved to:\n{path}"
                )
            except Exception as e:
                CustomMessageBox.critical(
                    self.parent_window, "error", f"backup failed: {e}"
                )

    def _save(self):
        lock_map = {0: "0", 1: "5", 2: "10", 3: "30", 4: "60"}
        trash_map = {0: "0", 1: "7", 2: "30", 3: "90"}
        self.db_manager.set_setting("auto_lock_minutes", lock_map[self.lock_combo.currentIndex()])
        self.db_manager.set_setting(
            "trash_clean_days", trash_map[self.trash_combo.currentIndex()]
        )
        self.accept()
