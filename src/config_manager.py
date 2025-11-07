"""
Configuration manager for Corall application.
Handles persistent configuration storage and .env file management.
"""
import os
import json
from typing import Dict, Any, Optional


class ConfigManager:
    """Manages application configuration and initialization state."""

    def __init__(self, config_file: str = "config.json"):
        """Initialize the config manager.

        Args:
            config_file: Path to the configuration file
        """
        self.config_file = config_file
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file.

        Returns:
            Dictionary containing configuration
        """
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return self._default_config()
        return self._default_config()

    def _default_config(self) -> Dict[str, Any]:
        """Get default configuration.

        Returns:
            Default configuration dictionary
        """
        return {
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

    def save_config(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Save configuration to file.

        Args:
            config: Configuration dictionary to save (uses self.config if None)
        """
        if config is not None:
            self.config = config

        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)

    def is_setup_completed(self) -> bool:
        """Check if initial setup has been completed.

        Returns:
            True if setup is complete, False otherwise
        """
        return self.config.get('setup_completed', False)

    def mark_setup_completed(self) -> None:
        """Mark setup as completed."""
        self.config['setup_completed'] = True
        self.save_config()

    def get_zotero_config(self) -> Dict[str, str]:
        """Get Zotero configuration.

        Returns:
            Dictionary with Zotero configuration
        """
        return self.config.get('zotero', {})

    def get_recommendation_config(self) -> Dict[str, float]:
        """Get recommendation configuration (weights, defaults).

        Returns:
            Dictionary with recommendation configuration
        """
        return self.config.get('recommendation', {})

    def update_env_file(self) -> None:
        """Update .env file with current configuration."""
        env_lines = []

        # Zotero configuration
        zotero = self.config.get('zotero', {})
        env_lines.append("# Zotero API Configuration")
        env_lines.append(f"ZOTERO_API_KEY={zotero.get('api_key', '')}")
        env_lines.append(f"ZOTERO_USER_ID={zotero.get('user_id', '')}")
        env_lines.append(f"ZOTERO_LIBRARY_TYPE={zotero.get('library_type', 'user')}")
        if zotero.get('collection_id'):
            env_lines.append(f"ZOTERO_COLLECTION_ID={zotero.get('collection_id', '')}")
        env_lines.append("")

        # OpenAlex configuration
        openalex = self.config.get('openalex', {})
        env_lines.append("# OpenAlex Configuration (optional, but recommended for higher rate limits)")
        env_lines.append(f"OPENALEX_EMAIL={openalex.get('email', '')}")
        env_lines.append("")

        # Email configuration
        email = self.config.get('email', {})
        env_lines.append("# Email Configuration (for sending search results)")
        env_lines.append(f"SMTP_SERVER={email.get('smtp_server', 'smtp.gmail.com')}")
        env_lines.append(f"SMTP_PORT={email.get('smtp_port', 587)}")
        env_lines.append(f"SMTP_USERNAME={email.get('smtp_username', '')}")
        env_lines.append(f"SMTP_PASSWORD={email.get('smtp_password', '')}")
        env_lines.append(f"SMTP_FROM_EMAIL={email.get('smtp_from_email', '')}")
        env_lines.append("")

        # Recommendation settings
        rec = self.config.get('recommendation', {})
        env_lines.append("# Recommendation Settings")
        env_lines.append(f"DEFAULT_DAYS_BACK={rec.get('default_days_back', 30)}")
        env_lines.append(f"DEFAULT_TOP_N={rec.get('default_top_n', 100)}")
        env_lines.append("CACHE_DIR=.cache")
        env_lines.append("")

        # Write to .env file
        with open('.env', 'w') as f:
            f.write('\n'.join(env_lines))

    def validate_zotero_config(self) -> tuple[bool, str]:
        """Validate Zotero configuration.

        Returns:
            Tuple of (is_valid, error_message)
        """
        zotero = self.config.get('zotero', {})

        if not zotero.get('api_key'):
            return False, "Zotero API key is required"

        if not zotero.get('user_id'):
            return False, "Zotero user ID is required"

        if zotero.get('library_type') not in ['user', 'group']:
            return False, "Library type must be 'user' or 'group'"

        return True, ""

    def test_zotero_connection(self) -> tuple[bool, str]:
        """Test Zotero connection with current configuration.

        Returns:
            Tuple of (is_valid, message)
        """
        try:
            from src.zotero_client import ZoteroClient

            # Temporarily set environment variables
            os.environ['ZOTERO_API_KEY'] = self.config['zotero']['api_key']
            os.environ['ZOTERO_USER_ID'] = self.config['zotero']['user_id']
            os.environ['ZOTERO_LIBRARY_TYPE'] = self.config['zotero']['library_type']

            client = ZoteroClient()
            # Try to list collections as a connection test
            collections = client.list_collections()

            return True, f"Successfully connected! Found {len(collections)} collections."
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
