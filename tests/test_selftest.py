"""Layer 1 tests for itias_coder.main._selftest (issue #14, T5).

The SELFTEST output lines are contractual: CI (T6) greps them against the
frozen exe, so expected text is asserted as literals here, never imported
back from the module. ``_selftest`` imports every submodule but must not
construct a QApplication.

Layer 1 discipline (docs/test.md): module import + monkeypatch only, no
QApplication, no widget instantiation, no network, no media files.
"""

from __future__ import annotations

import sys

import itias_coder.main as main_module
from itias_coder import qt_bindings


def test_selftest_happy(capsys):
    """Clean env: returns 0 and reports charts=ok."""
    assert main_module._selftest() == 0
    out = capsys.readouterr().out
    assert "SELFTEST OK" in out
    assert "qt_api=%d charts=ok" % qt_bindings.QT_API in out


def test_selftest_degraded_without_flag(monkeypatch, capsys):
    """Charts unavailable, no --allow-no-charts: returns 1 with FAIL line."""
    monkeypatch.setattr(qt_bindings, "CHARTS_AVAILABLE", False)
    monkeypatch.setattr(sys, "argv", ["itias_coder"])
    assert main_module._selftest() == 1
    out = capsys.readouterr().out
    assert "SELFTEST FAIL charts unavailable" in out


def test_selftest_degraded_with_flag(monkeypatch, capsys):
    """Charts unavailable + --allow-no-charts: returns 0 with degraded line."""
    monkeypatch.setattr(qt_bindings, "CHARTS_AVAILABLE", False)
    monkeypatch.setattr(sys, "argv", ["itias_coder", "--allow-no-charts"])
    assert main_module._selftest() == 0
    out = capsys.readouterr().out
    assert "SELFTEST OK" in out
    assert "qt_api=%d charts=degraded" % qt_bindings.QT_API in out
