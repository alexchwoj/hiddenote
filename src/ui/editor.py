from PyQt6.QtWidgets import QPlainTextEdit, QWidget, QTextEdit
from PyQt6.QtCore import Qt, QRect, QSize, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QTextFormat, QTextCursor, QFont


class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)


class NoteEditor(QPlainTextEdit):
    cursor_position_changed = pyqtSignal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._show_line_numbers = False
        self._line_number_area = LineNumberArea(self)

        self.blockCountChanged.connect(self._update_margins)
        self.updateRequest.connect(self._update_line_number_area)
        self.cursorPositionChanged.connect(self._on_cursor_moved)

        self._update_margins(0)

    def line_number_area_width(self):
        if not self._show_line_numbers:
            return 0
        digits = max(1, len(str(self.blockCount())))
        return 14 + self.fontMetrics().horizontalAdvance("9") * digits

    def _update_margins(self, _=None):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _update_line_number_area(self, rect, dy):
        if dy:
            self._line_number_area.scroll(0, dy)
        else:
            self._line_number_area.update(
                0, rect.y(), self._line_number_area.width(), rect.height()
            )
        if rect.contains(self.viewport().rect()):
            self._update_margins()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._line_number_area.setGeometry(
            QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height())
        )

    def line_number_area_paint_event(self, event):
        if not self._show_line_numbers:
            return
        painter = QPainter(self._line_number_area)
        painter.fillRect(event.rect(), QColor("#1A1D25"))

        block = self.firstVisibleBlock()
        block_num = block.blockNumber()
        offset = self.contentOffset()
        top = round(self.blockBoundingGeometry(block).translated(offset).top())
        bottom = top + round(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(QColor("#6C6F7E"))
                painter.drawText(
                    0,
                    top,
                    self._line_number_area.width() - 6,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight,
                    str(block_num + 1),
                )
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_num += 1

    def _on_cursor_moved(self):
        cursor = self.textCursor()
        line = cursor.blockNumber() + 1
        col = cursor.columnNumber() + 1
        self.cursor_position_changed.emit(line, col)

    def toggle_line_numbers(self):
        self._show_line_numbers = not self._show_line_numbers
        self._update_margins()
        self._line_number_area.update()
        return self._show_line_numbers

    def line_numbers_visible(self):
        return self._show_line_numbers

    def word_count(self):
        text = self.toPlainText()
        words = len(text.split()) if text.strip() else 0
        return words, len(text)

    def find_text(self, text, forward=True, case_sensitive=False):
        flags = QTextEdit.FindFlag(0)
        if not forward:
            flags |= QTextEdit.FindFlag.FindBackward
        if case_sensitive:
            flags |= QTextEdit.FindFlag.FindCaseSensitively
        found = self.find(text, flags)
        if not found:
            cursor = self.textCursor()
            if forward:
                cursor.movePosition(QTextCursor.MoveOperation.Start)
            else:
                cursor.movePosition(QTextCursor.MoveOperation.End)
            self.setTextCursor(cursor)
            found = self.find(text, flags)
        return found

    def replace_current(self, find_text, replace_text, case_sensitive=False):
        cursor = self.textCursor()
        if cursor.hasSelection():
            selected = cursor.selectedText()
            match = (
                selected == find_text
                if case_sensitive
                else selected.lower() == find_text.lower()
            )
            if match:
                cursor.insertText(replace_text)
                return True
        return self.find_text(find_text, forward=True, case_sensitive=case_sensitive)

    def replace_all(self, find_text, replace_text, case_sensitive=False):
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self.setTextCursor(cursor)

        count = 0
        flags = QTextEdit.FindFlag(0)
        if case_sensitive:
            flags |= QTextEdit.FindFlag.FindCaseSensitively

        while self.find(find_text, flags):
            c = self.textCursor()
            c.insertText(replace_text)
            count += 1
        return count
