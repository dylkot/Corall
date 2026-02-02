# Building Corall as a Standalone Application

This directory contains everything needed to build Corall as a standalone application that can be distributed without requiring users to install Python.

## Quick Start

### macOS / Linux

```bash
./scripts/build_app.sh
```

### Windows

```cmd
scripts\build_app.bat
```

## Output

| Platform | Output | Location |
|----------|--------|----------|
| macOS | `Corall.app` | `dist/Corall.app` |
| Windows | `Corall.exe` (folder) | `dist/Corall/` |
| Linux | `Corall` (folder) | `dist/Corall/` |

## What Gets Bundled

The standalone app includes:

- Python runtime (3.8+)
- All Python dependencies
- Flask web server
- Sentence-transformers ML model (~80MB, downloaded on first use)
- Application templates and source code

## User Data Location

The application stores user data (config, cache, embeddings) in platform-specific locations:

| Platform | Data Directory |
|----------|----------------|
| macOS | `~/Library/Application Support/Corall/` |
| Windows | `%APPDATA%\Corall\` |
| Linux | `~/.local/share/Corall/` |

This directory contains:
- `config.json` - Application configuration
- `.env` - API keys and credentials
- `.cache/` - Cached embeddings and search data

## Build Requirements

- Python 3.8 or higher
- ~2GB disk space for build process
- Internet connection (to download ML model)

## Build Options

### Clean Build

Remove all previous build artifacts before building:

```bash
./scripts/build_app.sh --clean
```

### Using Existing Virtual Environment

Skip creating a new virtual environment (faster for repeated builds):

```bash
./scripts/build_app.sh --no-venv
```

## Code Signing (macOS)

For distribution outside the App Store, you'll need to:

1. Sign the application:
   ```bash
   codesign --force --deep --sign "Developer ID Application: Your Name" dist/Corall.app
   ```

2. Notarize the application:
   ```bash
   xcrun notarytool submit dist/Corall.app --apple-id "your@email.com" --team-id "TEAMID"
   ```

Without signing, users will see a warning when opening the app.

## Creating a DMG (macOS)

If you have `create-dmg` installed, the build script will automatically create a DMG:

```bash
brew install create-dmg
./scripts/build_app.sh
```

## Troubleshooting

### Build fails with import errors

Ensure all dependencies are in `requirements.txt` and hidden imports are listed in `corall.spec`.

### App crashes on startup

Check the console output. Common issues:
- Missing hidden imports
- Missing data files
- Path issues

Run from terminal to see errors:
```bash
dist/Corall.app/Contents/MacOS/Corall
```

### ML model download fails

The sentence-transformers model is downloaded on first use. Ensure internet connection is available.

### "App is damaged" on macOS

This happens with unsigned apps. Either sign the app or tell users to run:
```bash
xattr -cr /path/to/Corall.app
```

## Files in This Directory

```
packaging/
├── corall.spec          # PyInstaller build specification
├── README.md            # This file
└── resources/
    ├── README.md        # How to create icons
    └── corall.icns      # macOS app icon (optional)
```

## Customizing the Build

Edit `packaging/corall.spec` to:
- Add/remove hidden imports
- Include additional data files
- Change app metadata (name, version, bundle ID)
- Modify macOS Info.plist settings
