"""Application bootstrap (dev + frozen exe)."""
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from itias_coder.ui.main_window import MainWindow


def run() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("ITIAS Coder")
    app.setOrganizationName("ITIAS-Coder")
    app.setStyle("Fusion")
    app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
