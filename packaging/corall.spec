# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Corall application.

This spec file configures PyInstaller to create a standalone application
that bundles Python, all dependencies, and application files.

Usage:
    pyinstaller packaging/corall.spec

The output will be in the dist/ directory.
"""

import sys
from pathlib import Path

# Get the project root directory
SPEC_DIR = Path(SPECPATH)
PROJECT_ROOT = SPEC_DIR.parent

# Application metadata
APP_NAME = 'Corall'
APP_VERSION = '1.0.0'
APP_BUNDLE_ID = 'com.corall.paperrecommender'

# Determine platform-specific settings
is_macos = sys.platform == 'darwin'
is_windows = sys.platform == 'win32'
is_linux = sys.platform.startswith('linux')

# Analysis: determine what to include
a = Analysis(
    # Entry point script
    [str(PROJECT_ROOT / 'launcher.py')],

    # Additional paths to search for imports
    pathex=[str(PROJECT_ROOT)],

    # Binary files to include (native extensions, DLLs)
    binaries=[],

    # Data files to include (non-Python files)
    datas=[
        # Templates
        (str(PROJECT_ROOT / 'templates'), 'templates'),
        # Example config files
        (str(PROJECT_ROOT / 'config.example.json'), '.'),
        (str(PROJECT_ROOT / '.env.example'), '.'),
        # Source modules (needed for imports)
        (str(PROJECT_ROOT / 'src'), 'src'),
        # Main app file
        (str(PROJECT_ROOT / 'app.py'), '.'),
        (str(PROJECT_ROOT / 'recommend.py'), '.'),
    ],

    # Hidden imports that PyInstaller might miss
    hiddenimports=[
        # Flask and extensions
        'flask',
        'flask_cors',
        'werkzeug',
        'jinja2',

        # Sentence transformers and dependencies
        'sentence_transformers',
        'sentence_transformers.models',
        'transformers',
        'transformers.models',
        'transformers.models.bert',
        'transformers.models.bert.modeling_bert',
        'transformers.models.bert.tokenization_bert',
        'transformers.models.bert.tokenization_bert_fast',

        # PyTorch
        'torch',
        'torch.nn',
        'torch.nn.functional',
        'torch.utils',
        'torch.utils.data',

        # NumPy and SciPy
        'numpy',
        'scipy',
        'scipy.spatial',
        'scipy.spatial.distance',

        # Other dependencies
        'pyzotero',
        'requests',
        'dotenv',
        'click',
        'tqdm',
        'pickle',
        'json',

        # Standard library modules used
        'email.mime.text',
        'email.mime.multipart',
        'smtplib',
        'ssl',
        'threading',
        'concurrent.futures',

        # Huggingface tokenizers
        'tokenizers',

        # Source modules
        'src',
        'src.recommender',
        'src.zotero_client',
        'src.openalex_client',
        'src.similarity_engine',
        'src.citation_scorer',
        'src.config_manager',
        'src.email_sender',
        'src.reviewed_papers',
        'src.journal_lists',
    ],

    # Packages to include completely
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],

    # Modules to exclude (to reduce size)
    excludes=[
        'tkinter',
        'matplotlib',
        'PIL',
        'pandas',
        'IPython',
        'jupyter',
        'notebook',
        'pytest',
        'setuptools',
    ],

    # Don't warn about missing imports for these
    noarchive=False,
    optimize=0,
)

# Remove duplicate entries
pyz = PYZ(a.pure)

# Create the executable
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False if (is_macos or is_windows) else True,  # GUI mode on macOS/Windows
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(PROJECT_ROOT / 'packaging' / 'resources' / 'corall.icns') if is_macos else None,
)

# Collect all files into a directory
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_NAME,
)

# macOS-specific: Create an app bundle
if is_macos:
    app = BUNDLE(
        coll,
        name=f'{APP_NAME}.app',
        icon=str(PROJECT_ROOT / 'packaging' / 'resources' / 'corall.icns') if (PROJECT_ROOT / 'packaging' / 'resources' / 'corall.icns').exists() else None,
        bundle_identifier=APP_BUNDLE_ID,
        version=APP_VERSION,
        info_plist={
            'CFBundleName': APP_NAME,
            'CFBundleDisplayName': 'Corall - Paper Recommendations',
            'CFBundleVersion': APP_VERSION,
            'CFBundleShortVersionString': APP_VERSION,
            'CFBundleIdentifier': APP_BUNDLE_ID,
            'CFBundlePackageType': 'APPL',
            'CFBundleSignature': '????',
            'CFBundleExecutable': APP_NAME,
            'NSHighResolutionCapable': True,
            'NSRequiresAquaSystemAppearance': False,  # Support dark mode
            'LSMinimumSystemVersion': '10.15.0',
            'CFBundleDocumentTypes': [],
            'LSApplicationCategoryType': 'public.app-category.productivity',
        },
    )
