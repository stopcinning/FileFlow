# PyInstaller spec for FileFlow.
#
# Run through scripts/build.py rather than by hand, so the paths stay relative
# to the repository and the build works from a clean clone.
#
# onefile vs onedir is selected with the FILEFLOW_ONEDIR environment variable.
# PyInstaller refuses --onefile/--onedir on the command line when a spec is
# given, so the choice has to live here.

import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

# SPECPATH is the directory holding this spec (packaging/), not the repo root.
ROOT = Path(SPECPATH).resolve().parent
SRC = ROOT / "src"
ICON = ROOT / "packaging" / "fileflow.ico"
VERSION_FILE = ROOT / "packaging" / "version_info.txt"

ONEDIR = os.environ.get("FILEFLOW_ONEDIR") == "1"

block_cipher = None

# PySide6 ships a lot of modules that are not used and that fail to bundle
# cleanly. Trimming them keeps the executable to a sensible size.
excludes = [
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick",
    "PySide6.QtQuick", "PySide6.QtQuick3D", "PySide6.QtQml", "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets", "PySide6.Qt3DCore", "PySide6.QtCharts",
    "PySide6.QtDataVisualization", "PySide6.QtBluetooth", "PySide6.QtNfc",
    "PySide6.QtPositioning", "PySide6.QtLocation", "PySide6.QtSensors",
    "PySide6.QtSerialPort", "PySide6.QtSql", "PySide6.QtTest", "PySide6.QtHelp",
    "PySide6.QtDesigner", "PySide6.QtUiTools", "PySide6.QtPdf", "PySide6.QtPdfWidgets",
    "PySide6.QtSpatialAudio", "PySide6.QtTextToSpeech", "PySide6.QtRemoteObjects",
    "PySide6.QtScxml", "PySide6.QtStateMachine", "PySide6.QtHttpServer",
    "tkinter", "unittest", "pydoc_data", "test", "lib2to3", "distutils",
    "numpy", "PIL", "matplotlib", "setuptools", "pip",
]

hiddenimports = collect_submodules("fileflow")

a = Analysis(  # noqa: F821
    [str(SRC / "fileflow" / "__main__.py")],
    pathex=[str(SRC)],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="FileFlow",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=False,  # GUI app: no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ICON) if ICON.exists() else None,
    version=str(VERSION_FILE) if VERSION_FILE.exists() else None,
)

if ONEDIR:
    coll = COLLECT(  # noqa: F821
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name="FileFlow",
    )
else:
    # Single file: everything is folded into the executable and extracted to a
    # temporary directory at launch. Slower to start, but it is one file to
    # download and nothing to install.
    exe.binaries = a.binaries
    exe.zipfiles = a.zipfiles
    exe.datas = a.datas
