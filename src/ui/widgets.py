from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QLabel,
    QListWidgetItem,
    QFileDialog,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from .dialogs import StyledMenu


class NoteItemWidget(QWidget):
    def __init__(self, title, created_at, updated_at, pinned=False, archived=False, tags=None):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(2)

        title_row = QHBoxLayout()
        title_row.setSpacing(4)

        if pinned:
            pin_label = QLabel("★")
            pin_label.setObjectName("pinIcon")
            pin_label.setStyleSheet("color: #FFD580; font-size: 13px; padding: 0;")
            title_row.addWidget(pin_label)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("noteTitle")
        title_row.addWidget(self.title_label)
        title_row.addStretch()

        if archived:
            arc_label = QLabel("archived")
            arc_label.setStyleSheet(
                "color: #6C6F7E; font-size: 11px; background: #35384A;"
                "border-radius: 4px; padding: 1px 5px;"
            )
            title_row.addWidget(arc_label)

        layout.addLayout(title_row)

        date_to_show = updated_at if updated_at else created_at
        try:
            date_dt = datetime.fromisoformat(
                date_to_show.replace("Z", "+00:00")
            ).replace(tzinfo=None)
            date_str = date_dt.strftime("%m/%d/%Y %H:%M")
        except Exception:
            date_str = date_to_show or ""

        self.updated_label = QLabel(f"updated: {date_str}")
        self.updated_label.setObjectName("noteDate")
        layout.addWidget(self.updated_label)

        if tags:
            tag_names = [t.strip() for t in tags.split(",") if t.strip()]
            if tag_names:
                tags_row = QHBoxLayout()
                tags_row.setSpacing(4)
                for tag in tag_names[:4]:
                    tag_label = QLabel(tag)
                    tag_label.setStyleSheet(
                        "color: #FFD580; font-size: 11px; background: #2E3140;"
                        "border-radius: 4px; padding: 1px 6px;"
                    )
                    tags_row.addWidget(tag_label)
                tags_row.addStretch()
                layout.addLayout(tags_row)

        self.setLayout(layout)
        self.set_unselected_style()

    def set_selected_style(self):
        self.title_label.setStyleSheet(
            "color: #23262F; font-weight: bold; font-size: 16px;"
        )
        self.updated_label.setStyleSheet("color: #6C6F7E; font-size: 13px;")

    def set_unselected_style(self):
        self.title_label.setStyleSheet(
            "color: #6C6F7E; font-weight: bold; font-size: 16px;"
        )
        self.updated_label.setStyleSheet("color: #6C6F7E; font-size: 13px;")


class NoteListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.all_notes = []
        self.current_view = "all"
        self.currentRowChanged.connect(self.update_item_styles)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def set_all_notes(self, notes):
        self.all_notes = notes

    def _get_title_at(self, index):
        item = self.item(index)
        if item is None:
            return None
        widget = self.itemWidget(item)
        if widget is None:
            return None
        label = widget.findChild(QLabel, "noteTitle")
        return label.text() if label else None

    def filter_notes(self, search_text):
        self.clear()
        for note in self.all_notes:
            title = note[0]
            if search_text.lower() in title.lower():
                pinned = note[3] if len(note) > 3 else False
                archived = note[4] if len(note) > 4 else False
                tags = note[5] if len(note) > 5 else None
                item = QListWidgetItem()
                widget = NoteItemWidget(title, note[1], note[2], pinned, archived, tags)
                item.setSizeHint(widget.sizeHint())
                self.addItem(item)
                self.setItemWidget(item, widget)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            current_item = self.currentItem()
            if current_item:
                title = self._get_title_at(self.currentRow())
                if title:
                    self.parent_app.handle_note_delete(title)
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

    def _show_context_menu(self, position):
        row = self.indexAt(position).row()
        if row < 0:
            return

        title = self._get_title_at(row)
        if not title:
            return

        app = self.parent_app
        db = app.db_manager
        view = self.current_view

        menu = StyledMenu(self)

        if view == "trash":
            restore_act = QAction("restore", self)
            restore_act.triggered.connect(lambda: app.restore_note_from_trash(title))
            menu.addAction(restore_act)

            delete_act = QAction("delete permanently", self)
            delete_act.triggered.connect(lambda: app.permanently_delete_note(title))
            menu.addAction(delete_act)

            menu.addSeparator()

            empty_act = QAction("empty trash", self)
            empty_act.triggered.connect(app.empty_trash)
            menu.addAction(empty_act)
        else:
            open_act = QAction("open", self)
            open_act.triggered.connect(lambda: self.setCurrentRow(row))
            menu.addAction(open_act)

            rename_act = QAction("rename", self)
            rename_act.triggered.connect(lambda: app.rename_note_dialog(title))
            menu.addAction(rename_act)

            menu.addSeparator()

            note_data = next((n for n in self.all_notes if n[0] == title), None)
            is_pinned = bool(note_data[3]) if note_data and len(note_data) > 3 else False
            is_archived = bool(note_data[4]) if note_data and len(note_data) > 4 else False

            pin_act = QAction("unpin" if is_pinned else "pin", self)
            pin_act.triggered.connect(lambda: app.toggle_pin_note(title))
            menu.addAction(pin_act)

            if view == "archived":
                unarchive_act = QAction("unarchive", self)
                unarchive_act.triggered.connect(lambda: app.toggle_archive_note(title))
                menu.addAction(unarchive_act)
            else:
                archive_act = QAction("archive", self)
                archive_act.triggered.connect(lambda: app.toggle_archive_note(title))
                menu.addAction(archive_act)

            menu.addSeparator()

            tags_act = QAction("tags...", self)
            tags_act.triggered.connect(lambda: app.manage_note_tags(title))
            menu.addAction(tags_act)

            readonly_act = QAction("read-only mode", self)
            readonly_act.setCheckable(True)
            readonly_act.setChecked(db.get_setting(f"readonly_{title}") == "1")
            readonly_act.triggered.connect(lambda checked: app.set_note_readonly(title, checked))
            menu.addAction(readonly_act)

            menu.addSeparator()

            export_menu = menu.addMenu("export as")
            md_act = QAction("markdown (.md)", self)
            md_act.triggered.connect(lambda: app.export_note(title, "md"))
            export_menu.addAction(md_act)

            html_act = QAction("html (.html)", self)
            html_act.triggered.connect(lambda: app.export_note(title, "html"))
            export_menu.addAction(html_act)

            txt_act = QAction("plain text (.txt)", self)
            txt_act.triggered.connect(lambda: app.export_note(title, "txt"))
            export_menu.addAction(txt_act)

            menu.addSeparator()

            history_act = QAction("version history", self)
            history_act.triggered.connect(lambda: app.show_version_history(title))
            menu.addAction(history_act)

            menu.addSeparator()

            trash_act = QAction("move to trash", self)
            trash_act.triggered.connect(lambda: app.handle_note_delete(title))
            menu.addAction(trash_act)

        menu.exec(self.mapToGlobal(position))
