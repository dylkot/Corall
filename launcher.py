#!/usr/bin/env python3
"""
Corall Application Launcher

This is the main entry point for the standalone Corall application.
It handles:
- Setting up the user data directory (config, cache, etc.)
- Starting the Flask web server
- Opening the browser
- Graceful shutdown
"""
import os
import sys
import json
import signal
import threading
import time
import webbrowser
from pathlib import Path


def get_app_data_dir() -> Path:
    """Get the appropriate application data directory for the current platform.

    Returns:
        Path to the application data directory
    """
    if sys.platform == 'darwin':
        # macOS: ~/Library/Application Support/Corall
        base = Path.home() / 'Library' / 'Application Support'
    elif sys.platform == 'win32':
        # Windows: %APPDATA%/Corall
        base = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming'))
    else:
        # Linux/Unix: ~/.local/share/corall
        base = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share'))

    return base / 'Corall'


def get_bundle_dir() -> Path:
    """Get the directory where the application bundle is located.

    When running as a PyInstaller bundle, this returns the directory containing
    the bundled files. When running from source, returns the script directory.

    Returns:
        Path to the bundle directory
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled/frozen (PyInstaller)
        return Path(sys._MEIPASS)
    else:
        # Running from source
        return Path(__file__).parent.resolve()


def setup_data_directory(app_data_dir: Path) -> None:
    """Set up the application data directory with necessary files.

    Creates a clean default config that triggers the setup wizard on first run,
    rather than copying example files that contain placeholder values.

    Args:
        app_data_dir: Path to the user's application data directory
    """
    # Create data directory if it doesn't exist
    app_data_dir.mkdir(parents=True, exist_ok=True)

    # Create cache directory
    cache_dir = app_data_dir / '.cache'
    cache_dir.mkdir(exist_ok=True)

    # Create default config if it doesn't exist
    # Use empty values (not placeholders) so the setup wizard detects
    # that configuration is needed and prompts the user properly.
    config_file = app_data_dir / 'config.json'
    if not config_file.exists():
        default_config = {
            'setup_completed': False,
            'zotero': {
                'api_key': '',
                'user_id': '',
                'library_type': 'user',
                'collection_id': '',
                'collection_name': ''
            },
            'openalex': {
                'email': ''
            },
            'recommendation': {
                'citation_weight': 0.3,
                'similarity_weight': 0.7,
                'default_days_back': 30,
                'default_top_n': 100
            },
            'email': {
                'smtp_server': 'smtp.gmail.com',
                'smtp_port': 587,
                'smtp_username': '',
                'smtp_password': '',
                'smtp_from_email': ''
            }
        }
        with open(config_file, 'w') as f:
            json.dump(default_config, f, indent=2)

    # Create empty .env if it doesn't exist
    # The setup wizard will populate this via ConfigManager.update_env_file()
    env_file = app_data_dir / '.env'
    if not env_file.exists():
        env_file.touch()


def open_browser(port: int = 5050, delay: float = 2.0) -> None:
    """Open the browser after a delay to ensure server is ready.

    Args:
        port: The port the server is running on
        delay: Seconds to wait before opening browser
    """
    time.sleep(delay)
    webbrowser.open(f'http://127.0.0.1:{port}/')


def run_app(port: int = 5050, open_browser_flag: bool = True) -> None:
    """Run the Corall application.

    Args:
        port: Port to run the server on
        open_browser_flag: Whether to automatically open the browser
    """
    bundle_dir = get_bundle_dir()
    app_data_dir = get_app_data_dir()

    print(f"Corall - Paper Recommendation System")
    print(f"=" * 40)
    print(f"Data directory: {app_data_dir}")
    print(f"Bundle directory: {bundle_dir}")
    print()

    # Set up the data directory
    setup_data_directory(app_data_dir)

    # Change to data directory so relative paths work
    original_cwd = os.getcwd()
    os.chdir(app_data_dir)

    # Add bundle directory to path for imports
    if str(bundle_dir) not in sys.path:
        sys.path.insert(0, str(bundle_dir))

    # Set template folder for Flask
    os.environ['CORALL_TEMPLATE_DIR'] = str(bundle_dir / 'templates')
    os.environ['CORALL_BUNDLE_DIR'] = str(bundle_dir)

    # Import and configure Flask app
    # Note: app.py calls load_dotenv() at import time, which will load
    # .env from the CWD (app_data_dir). We don't pre-load here to avoid
    # double-loading. The setup wizard populates .env via ConfigManager.
    from app import app

    # Update Flask template and static folders if running from bundle
    if getattr(sys, 'frozen', False):
        app.template_folder = str(bundle_dir / 'templates')
        if (bundle_dir / 'static').exists():
            app.static_folder = str(bundle_dir / 'static')

    # Start browser in background thread
    if open_browser_flag:
        browser_thread = threading.Thread(target=open_browser, args=(port,))
        browser_thread.daemon = True
        browser_thread.start()

    # Handle shutdown gracefully
    def signal_handler(signum, frame):
        print("\nShutting down Corall...")
        os.chdir(original_cwd)
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print(f"Starting server on http://127.0.0.1:{port}/")
    print("Press Ctrl+C to stop")
    print()

    # Run Flask app (production mode for standalone)
    try:
        app.run(host='127.0.0.1', port=port, debug=False, use_reloader=False)
    finally:
        os.chdir(original_cwd)


def main():
    """Main entry point for the application."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Corall - Paper Recommendation System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  corall                    Start the application (opens browser)
  corall --port 8080        Start on a different port
  corall --no-browser       Start without opening browser
  corall --data-dir         Show the data directory location
        """
    )
    parser.add_argument(
        '--port', '-p',
        type=int,
        default=5050,
        help='Port to run the server on (default: 5050)'
    )
    parser.add_argument(
        '--no-browser',
        action='store_true',
        help='Do not automatically open the browser'
    )
    parser.add_argument(
        '--data-dir',
        action='store_true',
        help='Print the data directory location and exit'
    )
    parser.add_argument(
        '--version', '-v',
        action='store_true',
        help='Print version and exit'
    )

    args = parser.parse_args()

    if args.version:
        print("Corall v1.0.0")
        sys.exit(0)

    if args.data_dir:
        print(get_app_data_dir())
        sys.exit(0)

    run_app(port=args.port, open_browser_flag=not args.no_browser)


if __name__ == '__main__':
    main()
