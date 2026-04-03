# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for TZH Promet vs Banka
# Run on Windows: pyinstaller build.spec

import os
import importlib

# Find streamlit and plotly package paths for data collection
streamlit_path = os.path.dirname(importlib.import_module("streamlit").__file__)
plotly_path = os.path.dirname(importlib.import_module("plotly").__file__)

a = Analysis(
    ["launcher.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("app.py", "."),
        ("version.py", "."),
        ("src", "src"),
        (".streamlit", ".streamlit"),
        (streamlit_path, "streamlit"),
        (plotly_path, "plotly"),
    ],
    hiddenimports=[
        "streamlit",
        "streamlit.web.cli",
        "streamlit.runtime.scriptrunner",
        "plotly",
        "plotly.express",
        "plotly.graph_objects",
        "openpyxl",
        "pdfplumber",
        "fpdf",
        "webview",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="TZH-Promet-vs-Banka",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window
    icon="assets/icon.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="TZH-Promet-vs-Banka",
)
