from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QListWidget,
    QLabel,
    QListWidgetItem,
)
from PyQt6.QtCore import Qt


class NoteItemWidget(QWidget):
    def __init__(self, title, created_at, updated_at):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(2)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("noteTitle")
        layout.addWidget(self.title_label)

        created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00")).replace(
            tzinfo=None
        )
        updated_dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00")).replace(
            tzinfo=None
        )

        self.created_label = QLabel(f"created: {created_dt.strftime('%m/%d/%Y %H:%M')}")
        self.created_label.setObjectName("noteDate")
        layout.addWidget(self.created_label)

        self.updated_label = QLabel(f"updated: {updated_dt.strftime('%m/%d/%Y %H:%M')}")
        self.updated_label.setObjectName("noteDate")
        layout.addWidget(self.updated_label)

        self.setLayout(layout)
        self.set_unselected_style()

    def set_selected_style(self):
        self.title_label.setStyleSheet(
            "color: #23262F; font-weight: bold; font-size: 16px;"
        )
        self.created_label.setStyleSheet("color: #6C6F7E; font-size: 13px;")
        self.updated_label.setStyleSheet("color: #6C6F7E; font-size: 13px;")

    def set_unselected_style(self):
        self.title_label.setStyleSheet(
            "color: #6C6F7E; font-weight: bold; font-size: 16px;"
        )
        self.created_label.setStyleSheet("color: #6C6F7E; font-size: 13px;")
        self.updated_label.setStyleSheet("color: #6C6F7E; font-size: 13px;")


class NoteListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.all_notes = []
        self.currentRowChanged.connect(self.update_item_styles)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

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

    def update_item_styles(self, current_row):
        for i in range(self.count()):
            item = self.item(i)
            widget = self.itemWidget(item)
            if widget:
                if i == current_row:
                    widget.set_selected_style()
                else:
                    widget.set_unselected_style()
