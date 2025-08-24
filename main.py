import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont, QIcon

from src.app import HiddenoteApp
from src.ui.theme import load_custom_fonts, apply_theme


def main():
    app = QApplication(sys.argv)

    icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

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

    HiddenoteApp()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
