import os
from PyQt6.QtGui import QFontDatabase


def load_custom_fonts():
    font_dir = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "fonts")

    if not os.path.exists(font_dir):
        return None

    font_files = [
        f for f in os.listdir(font_dir) if f.lower().endswith((".ttf", ".otf"))
    ]

    if not font_files:
        return None

    loaded_families = {}

    for filename in font_files:
        font_path = os.path.join(font_dir, filename)
        font_id = QFontDatabase.addApplicationFont(font_path)

        if font_id != -1:
            font_families = QFontDatabase.applicationFontFamilies(font_id)
            for family in font_families:
                if family not in loaded_families:
                    loaded_families[family] = []
                loaded_families[family].append(filename.lower())

    for family, files in loaded_families.items():
        for preferred in ["regular", "normal", "medium"]:
            for file in files:
                if preferred in file:
                    return family
        return family

    return None


def apply_theme(app, custom_font_family=None):
    font_family = (
        f"'{custom_font_family}', 'Cascadia Code', monospace"
        if custom_font_family
        else "'Cascadia Code', monospace"
    )

    app.setStyleSheet(f"""
        QWidget {{
            background-color: #181A20;
            color: #E6E6E6;
            font-family: {font_family};
            font-size: 16px;
            font-weight: 400;
            border-radius: 14px;
        }}

        QFrame#mainFrame {{
            background-color: #181A20;
            border: 2px solid #35384A;
            border-radius: 20px;
        }}

        QFrame#dialogFrame {{
            background-color: #23262F;
            border: 2px solid #35384A;
            border-radius: 18px;
        }}

        QLabel#customTitleLabel {{
            color: #FFD580;
            font-size: 18px;
            font-weight: 700;
            background: transparent;
            border: none;
            font-family: {font_family};
            padding-left: 5px;
        }}

        QPushButton#closeButton {{
            background-color: #FF6B6B;
            color: #FFFFFF;
            border: none;
            border-radius: 6px;
            font-size: 18px;
            font-weight: normal;
            font-family: Arial, sans-serif;
            min-width: 22px;
            max-width: 22px;
            min-height: 22px;
            max-height: 22px;
            padding: 0px;
            margin: 0px;
        }}

        QPushButton#closeButton:hover {{
            background-color: #FF5252;
        }}

        QPushButton#closeButton:pressed {{
            background-color: #E53935;
        }}

        QDialog {{
            background-color: transparent;
        }}
        QDialog QLabel#titleLabel {{
            color: #FFD580;
            font-size: 20px;
            font-weight: 700;
            padding: 8px 0 8px 0;
            margin-bottom: 8px;
            background: transparent;
            font-family: {font_family};
        }}
        QDialog QLineEdit {{
            background-color: #181A20;
            color: #FFD580;
            border: 1.5px solid #FFD580;
            border-radius: 8px;
            padding: 15px;
            font-size: 15px;
            min-height: 20px;
            font-family: {font_family};
        }}
        QDialog QPushButton {{
            background-color: #FFD580;
            color: #23262F;
            border: none;
            border-radius: 8px;
            padding: 12px 20px;
            min-width: 100px;
            font-size: 15px;
            font-weight: 700;
            font-family: {font_family};
        }}
        QDialog QPushButton:hover {{
            background-color: #DEB86A;
            color: #23262F;
        }}
        QDialog QPushButton:pressed {{
            background-color: #C9A100;
            color: #181A20;
        }}

        QFrame {{
            background-color: #23262F;
            border: none;
            border-radius: 18px;
        }}

        QFrame#sidebarFrame {{
            background-color: #23262F;
            border: none;
            border-top-left-radius: 0px;
            border-top-right-radius: 0px;
            border-bottom-left-radius: 18px;
            border-bottom-right-radius: 0px;
        }}

        QFrame#editorFrame {{
            background-color: #23262F;
            border: none;
            border-top-left-radius: 0px;
            border-top-right-radius: 0px;
            border-bottom-left-radius: 0px;
            border-bottom-right-radius: 18px;
        }}

        QPushButton {{
            background-color: #FFD580;
            color: #23262F;
            border: none;
            border-radius: 10px;
            padding: 12px 24px;
            min-width: 100px;
            font-size: 15px;
            font-weight: 700;
            letter-spacing: 0.5px;
            font-family: {font_family};
        }}

        QPushButton:hover {{
            background-color: #DEB86A;
            color: #181A20;
        }}

        QPushButton:pressed {{
            background-color: #C9A100;
            color: #181A20;
        }}

        QPushButton:default {{
            background-color: #FFD580;
            color: #23262F;
            border: 2px solid #FFD580;
        }}

        QLineEdit {{
            background-color: #23262F;
            color: #E6E6E6;
            border: 1.5px solid #35384A;
            border-radius: 8px;
            padding: 12px;
            font-size: 15px;
            font-weight: 400;
            font-family: {font_family};
        }}

        QLineEdit:focus {{
            border: 1.5px solid #FFD580;
            background-color: #23262F;
        }}

        QLineEdit[placeholderText] {{
            color: #6C6F7E;
        }}

        QListWidget {{
            background-color: #23262F;
            color: #E6E6E6;
            border: none;
            outline: none;
            font-weight: 400;
            font-family: {font_family};
            border-radius: 14px;
            font-size: 15px;
        }}

        QListWidget::item {{
            padding: 0px;
            border: none;
            background: transparent;
            border-radius: 10px;
            margin: 4px 0px;
        }}

        QListWidget::item:selected {{
            background-color: #FFD580;
            color: #23262F;
            border-radius: 10px;
        }}

        QListWidget::item:selected QLabel#noteTitle {{
            color: #23262F;
            font-weight: bold;
        }}

        QListWidget::item QLabel#noteTitle {{
            color: #6C6F7E;
            font-weight: bold;
            font-size: 16px;
        }}

        QListWidget::item:selected QLabel#noteDate {{
            color: #6C6F7E;
        }}

        QListWidget::item:hover {{
            background-color: #35384A;
            border-radius: 10px;
        }}

        QTextEdit, QTextBrowser {{
            background-color: #181A20;
            color: #E6E6E6;
            border: none;
            border-top-left-radius: 0px;
            border-top-right-radius: 14px;
            border-bottom-left-radius: 14px;
            border-bottom-right-radius: 14px;
            font-family: {font_family};
            font-size: 17px;
            font-weight: 400;
            line-height: 1.5;
            padding: 18px;
        }}

        QTabWidget::pane {{
            border: none;
            background-color: #181A20;
            border-top-left-radius: 0px;
            border-top-right-radius: 18px;
            border-bottom-left-radius: 18px;
            border-bottom-right-radius: 18px;
            margin-top: 0px;
        }}

        QTabBar {{
            qproperty-drawBase: 0;
            background-color: transparent;
        }}

        QTabBar::tab {{
            background-color: #35384A;
            color: #E6E6E6;
            padding: 12px 32px;
            border: none;
            font-weight: 600;
            font-size: 17px;
            border-top-left-radius: 14px;
            border-top-right-radius: 14px;
            margin-right: 4px;
            margin-bottom: 2px;
            font-family: {font_family};
            min-width: 120px;
        }}

        QTabBar::tab:selected {{
            background-color: #FFD580;
            color: #23262F;
            margin-bottom: 0px;
        }}

        QTabBar::tab:hover {{
            background-color: #DEB86A;
            color: #181A20;
        }}

        QTabBar::tab:!selected {{
            margin-top: 2px;
        }}

        QScrollBar:vertical {{
            background: transparent;
            width: 12px;
            border: none;
            margin: 0px;
        }}

        QScrollBar::handle:vertical {{
            background-color: rgba(53, 56, 74, 0.6);
            border-radius: 6px;
            min-height: 30px;
            margin: 2px;
            border: none;
        }}

        QScrollBar::handle:vertical:hover {{
            background-color: rgba(255, 213, 128, 0.8);
        }}

        QScrollBar::handle:vertical:pressed {{
            background-color: rgba(255, 213, 128, 1);
        }}

        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            border: none;
            background: transparent;
            height: 0px;
            width: 0px;
        }}

        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: transparent;
        }}

        QScrollBar:horizontal {{
            background: transparent;
            height: 12px;
            border: none;
            margin: 0px;
        }}

        QScrollBar::handle:horizontal {{
            background-color: rgba(53, 56, 74, 0.6);
            border-radius: 6px;
            min-width: 30px;
            margin: 2px;
            border: none;
        }}

        QScrollBar::handle:horizontal:hover {{
            background-color: rgba(255, 213, 128, 0.8);
        }}

        QScrollBar::handle:horizontal:pressed {{
            background-color: rgba(255, 213, 128, 1);
        }}

        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            border: none;
            background: transparent;
            height: 0px;
            width: 0px;
        }}

        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
            background: transparent;
        }}

        QListWidget QScrollBar:vertical {{
            background: transparent;
            width: 8px;
            border: none;
            margin: 4px 1px;
        }}

        QListWidget QScrollBar::handle:vertical {{
            background-color: rgba(108, 111, 126, 0.3);
            border-radius: 4px;
            min-height: 20px;
            margin: 0px;
            border: none;
        }}

        QListWidget QScrollBar::handle:vertical:hover {{
            background-color: rgba(255, 213, 128, 0.6);
            width: 8px;
        }}

        QListWidget QScrollBar::handle:vertical:pressed {{
            background-color: rgba(255, 213, 128, 0.8);
        }}

        QListWidget QScrollBar::add-line:vertical, QListWidget QScrollBar::sub-line:vertical {{
            border: none;
            background: transparent;
            height: 0px;
        }}

        QListWidget QScrollBar::add-page:vertical, QListWidget QScrollBar::sub-page:vertical {{
            background: transparent;
        }}

        QListWidget QScrollBar:horizontal {{
            background: transparent;
            height: 8px;
            border: none;
            margin: 1px 4px;
        }}

        QListWidget QScrollBar::handle:horizontal {{
            background-color: rgba(108, 111, 126, 0.3);
            border-radius: 4px;
            min-width: 20px;
            margin: 0px;
            border: none;
        }}

        QListWidget QScrollBar::handle:horizontal:hover {{
            background-color: rgba(255, 213, 128, 0.6);
        }}

        QListWidget QScrollBar::handle:horizontal:pressed {{
            background-color: rgba(255, 213, 128, 0.8);
        }}

        QListWidget QScrollBar::add-line:horizontal, QListWidget QScrollBar::sub-line:horizontal {{
            border: none;
            background: transparent;
            width: 0px;
        }}

        QListWidget QScrollBar::add-page:horizontal, QListWidget QScrollBar::sub-page:horizontal {{
            background: transparent;
        }}

        QTextEdit QScrollBar:vertical, QTextBrowser QScrollBar:vertical {{
            background: transparent;
            width: 10px;
            border: none;
            margin: 4px 2px;
        }}

        QTextEdit QScrollBar::handle:vertical, QTextBrowser QScrollBar::handle:vertical {{
            background-color: rgba(53, 56, 74, 0.5);
            border-radius: 5px;
            min-height: 25px;
            margin: 1px;
            border: none;
        }}

        QTextEdit QScrollBar::handle:vertical:hover, QTextBrowser QScrollBar::handle:vertical:hover {{
            background-color: rgba(108, 111, 126, 0.8);
        }}

        QTextEdit QScrollBar::handle:vertical:pressed, QTextBrowser QScrollBar::handle:vertical:pressed {{
            background-color: rgba(255, 213, 128, 1);
        }}

        QTextEdit QScrollBar:horizontal, QTextBrowser QScrollBar:horizontal {{
            background: transparent;
            height: 10px;
            border: none;
            margin: 2px 4px;
        }}

        QTextEdit QScrollBar::handle:horizontal, QTextBrowser QScrollBar::handle:horizontal {{
            background-color: rgba(53, 56, 74, 0.5);
            border-radius: 5px;
            min-width: 25px;
            margin: 1px;
            border: none;
        }}

        QTextEdit QScrollBar::handle:horizontal:hover, QTextBrowser QScrollBar::handle:horizontal:hover {{
            background-color: rgba(108, 111, 126, 0.8);
        }}

        QTextEdit QScrollBar::handle:horizontal:pressed, QTextBrowser QScrollBar::handle:horizontal:pressed {{
            background-color: rgba(255, 213, 128, 1);
        }}

        QTextEdit QScrollBar::add-line, QTextEdit QScrollBar::sub-line,
        QTextBrowser QScrollBar::add-line, QTextBrowser QScrollBar::sub-line {{
            border: none;
            background: transparent;
            height: 0px;
            width: 0px;
        }}

        QTextEdit QScrollBar::add-page, QTextEdit QScrollBar::sub-page,
        QTextBrowser QScrollBar::add-page, QTextBrowser QScrollBar::sub-page {{
            background: transparent;
        }}

        QMessageBox {{
            background-color: #23262F;
            color: #E6E6E6;
            border-radius: 16px;
        }}

        QMessageBox QLabel {{
            color: #E6E6E6;
            background: transparent;
            font-weight: 400;
            font-size: 16px;
            font-family: {font_family};
        }}

        QInputDialog {{
            background-color: #23262F;
            color: #E6E6E6;
            border-radius: 16px;
        }}

        QInputDialog QLabel {{
            color: #E6E6E6;
            background: transparent;
            font-weight: 400;
            font-size: 16px;
            font-family: {font_family};
        }}

        QLabel {{
            color: #E6E6E6;
            font-weight: 400;
            padding: 2px;
            background: transparent;
            border: none;
            font-size: 16px;
            font-family: {font_family};
        }}

        QLabel#titleLabel {{
            color: #FFD580;
            font-size: 22px;
            font-weight: 700;
            padding: 16px 0 10px 0;
            margin-bottom: 8px;
            background: transparent;
            font-family: {font_family};
        }}

        QLabel#noteDate {{
            color: #6C6F7E;
            font-size: 13px;
            font-weight: 400;
            font-family: {font_family};
            background: transparent;
        }}
    """)
