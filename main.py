import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont

from src.app import HiddenoteApp
from src.ui.theme import load_custom_fonts, apply_theme


def main():
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

    editor = HiddenoteApp()
    editor.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
