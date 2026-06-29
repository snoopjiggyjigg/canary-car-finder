# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


playwright_cache = Path(os.environ.get("LOCALAPPDATA", "")) / "ms-playwright"

datas = [
    ("config/default_settings.json", "config"),
    ("config/app_config.json", "config"),
    ("assets/app_icon.ico", "assets"),
]
datas += collect_data_files("customtkinter")

if playwright_cache.exists():
    datas.append((str(playwright_cache), "ms-playwright"))

hiddenimports = collect_submodules("playwright")


a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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
    name="CanaryCarFinder",
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
    icon="assets/app_icon.ico",
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="CanaryCarFinder",
)
