"""Application bootstrap (dev + frozen exe)."""
import sys

from itias_coder.qt_bindings import QApplication, Qt, qt_exec


def run() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("ITIAS Coder")
    app.setOrganizationName("ITIAS-Coder")
    app.setStyle("Fusion")
    if hasattr(Qt, "ApplicationAttribute"):
        app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)

    from itias_coder.ui.main_window import MainWindow

    window = MainWindow()
    window.show()
    sys.exit(qt_exec(app))
