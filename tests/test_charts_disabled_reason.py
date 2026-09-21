"""Layer 1 tests for qt_bindings.charts_disabled_reason (issue #14, T4).

The degradation notice string is contractual: analysis/compare windows show it
verbatim when QtCharts is unavailable, so the expected text is asserted as a
literal here, not imported back from the module.

Layer 1 discipline (docs/test.md): module import only, no QApplication, no
widget instantiation, no network, no media files.
"""

from __future__ import annotations

import importlib

DEGRADED_NOTICE = (
    "图表模块不可用（QtCharts 缺失，兼容模式）：矩阵、统计与导出不受影响"
)


def test_notice_returned_when_charts_unavailable(monkeypatch):
    """Given charts flag forced off, the notice text is the exact contract."""
    qt_bindings = importlib.import_module("itias_coder.qt_bindings")
    monkeypatch.setattr(qt_bindings, "CHARTS_AVAILABLE", False)
    assert qt_bindings.charts_disabled_reason() == DEGRADED_NOTICE


def test_none_returned_when_charts_available(monkeypatch):
    """Given charts flag forced on, no degradation notice is produced."""
    qt_bindings = importlib.import_module("itias_coder.qt_bindings")
    monkeypatch.setattr(qt_bindings, "CHARTS_AVAILABLE", True)
    assert qt_bindings.charts_disabled_reason() is None


def test_callable_and_none_in_normal_dev_env():
    """Normal dev env (PySide6 charts installed): callable, returns None."""
    qt_bindings = importlib.import_module("itias_coder.qt_bindings")
    assert callable(qt_bindings.charts_disabled_reason)
    assert qt_bindings.charts_disabled_reason() is None
