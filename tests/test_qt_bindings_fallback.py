"""Chart-degradation contract tests for itias_coder.qt_bindings (issue #14).

Red baseline (T2): three tests fail on purpose because qt_bindings.py has no
defensive QtCharts import yet. T3 pins the contract implemented here:

- ``qt_bindings.CHARTS_AVAILABLE``: True when QtCharts imports, False otherwise
- broken ``PySide6.QtCharts`` in sys.modules must not make reload raise
- ``ITIAS_FORCE_NO_QTCHARTS=1`` forces ``CHARTS_AVAILABLE = False`` on reload
- UI window modules stay importable while the charts-missing flag is forced

Layer 1 discipline (docs/test.md): module import only, no QApplication, no
widget instantiation, no network, no media files.
"""

from __future__ import annotations

import importlib
import sys
import types

WINDOW_MODULES = ("itias_coder.ui.analysis_window", "itias_coder.ui.compare_window")


def test_happy_import():
    """Clean environment: PySide6 chain wins and chart symbols are bound."""
    qt_bindings = importlib.import_module("itias_coder.qt_bindings")
    assert qt_bindings.QT_API == 6
    assert qt_bindings.QChart is not None
    assert qt_bindings.QChartView is not None
    assert qt_bindings.QLineSeries is not None


def test_broken_module_reload():
    """Broken PySide6.QtCharts in sys.modules: reload must not raise (post-T3)."""
    qt_bindings = importlib.import_module("itias_coder.qt_bindings")
    real_charts = sys.modules.get("PySide6.QtCharts")
    sys.modules["PySide6.QtCharts"] = types.ModuleType("PySide6.QtCharts")
    try:
        reloaded = importlib.reload(qt_bindings)
        assert reloaded.QT_API == 6
        assert reloaded.CHARTS_AVAILABLE is False
    finally:
        if real_charts is not None:
            sys.modules["PySide6.QtCharts"] = real_charts
        else:
            sys.modules.pop("PySide6.QtCharts", None)
        importlib.reload(qt_bindings)  # restore clean module state


def test_windows_importable_when_charts_missing(monkeypatch):
    """UI window modules import even when the charts-missing flag is forced."""
    qt_bindings = importlib.import_module("itias_coder.qt_bindings")
    monkeypatch.setattr(qt_bindings, "CHARTS_AVAILABLE", False)
    for name in WINDOW_MODULES:
        monkeypatch.delitem(sys.modules, name, raising=False)
        assert importlib.import_module(name) is not None


def test_env_switch_forces_no_charts(monkeypatch):
    """ITIAS_FORCE_NO_QTCHARTS=1 + reload forces CHARTS_AVAILABLE=False."""
    qt_bindings = importlib.import_module("itias_coder.qt_bindings")
    monkeypatch.setenv("ITIAS_FORCE_NO_QTCHARTS", "1")
    try:
        reloaded = importlib.reload(qt_bindings)
        assert reloaded.CHARTS_AVAILABLE is False
    finally:
        monkeypatch.undo()
        importlib.reload(qt_bindings)  # restore clean module state
