import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class ConfigManager:
    def __init__(self, config_path="config.json"):
        self.config_path = Path(config_path)
        self._last_modified = None
        self.relays = []
        self.load_config()

    def load_config(self):
        """Load relay configuration from file"""
        try:
            current_modified = self.config_path.stat().st_mtime
            if self._last_modified is None or current_modified > self._last_modified:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    self.relays = config.get('relays', [])
                self._last_modified = current_modified
                logger.info(f"Loaded {len(self.relays)} relays from config")
                return True
        except Exception as e:
            logger.error(f"Error loading config: {e}")
        return False

    def get_relays(self):
        """Get current relay list, checking for updates"""
        self.load_config()
        return self.relays
