"""Application bootstrap (dev + frozen exe)."""
import sys

from itias_coder.qt_bindings import QApplication, Qt, qt_exec


def _selftest() -> int:
    """Smoke check for CI on the frozen exe (issue #14): import every
    itias_coder submodule and report the charts state.

    The SELFTEST output lines are contractual (CI greps them); keep them
    stable. Never constructs a QApplication, so it is safe to run headless.
    """
    import pkgutil
    import traceback

    import itias_coder
    from itias_coder import qt_bindings

    walk_errors = []

    def _record_walk_error(name):
        walk_errors.append(name)

    try:
        for _, name, _ in pkgutil.walk_packages(
            itias_coder.__path__, prefix="itias_coder.", onerror=_record_walk_error
        ):
            __import__(name)
    except Exception:
        traceback.print_exc()
        return 1

    if walk_errors:
        print("SELFTEST FAIL import failed: %s" % ", ".join(sorted(walk_errors)))
        return 1

    if not qt_bindings.CHARTS_AVAILABLE:
        if "--allow-no-charts" not in sys.argv:
            print("SELFTEST FAIL charts unavailable")
            return 1
        print("SELFTEST OK qt_api=%d charts=degraded" % qt_bindings.QT_API)
        return 0

    print("SELFTEST OK qt_api=%d charts=ok" % qt_bindings.QT_API)
    return 0


def run() -> None:
    # Dispatch BEFORE QApplication creation: both entries (python -m and the
    # frozen exe via packaging/entry.py) reach run() first, and the selftest
    # path must stay headless.
    if "--selftest" in sys.argv:
        sys.exit(_selftest())

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
