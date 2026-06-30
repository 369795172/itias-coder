# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for ITIAS Coder (Windows onedir distribution)."""

from pathlib import Path

from PyInstaller.utils.hooks import collect_all

project_dir = Path(SPECPATH).resolve().parent
entry = str(project_dir / "packaging" / "entry.py")

pyside6_datas, pyside6_binaries, pyside6_hiddenimports = collect_all("PySide6")

a = Analysis(
    [entry],
    pathex=[str(project_dir)],
    binaries=pyside6_binaries,
    datas=[
        (str(project_dir / "config" / "profiles"), "config/profiles"),
        *pyside6_datas,
    ],
    hiddenimports=[
        *pyside6_hiddenimports,
        "PySide6.QtMultimedia",
        "PySide6.QtMultimediaWidgets",
        "itias_coder",
        "itias_coder.main",
        "itias_coder.ui.main_window",
        "itias_coder.ui.encoder_window",
        "itias_coder.ui.slicer_dialog",
        "itias_coder.profile",
        "itias_coder.storage",
        "itias_coder.slicer",
        "itias_coder.models",
        "itias_coder.runtime_paths",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ITIAS-Coder",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="ITIAS-Coder",
)
