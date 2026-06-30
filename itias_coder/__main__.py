"""Entry point: python -m itias_coder"""
import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from .ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("ITIAS Coder")
    app.setOrganizationName("ITIAS-Coder")
    app.setStyle("Fusion")

    # High-DPI support
    app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
