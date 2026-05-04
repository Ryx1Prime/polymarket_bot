import os
import json
from pathlib import Path
from cryptography.fernet import Fernet
from utils.logger import logger_instance

class ConfigManager:
    def __init__(self):
        self.appdata_dir = Path(os.environ.get('APPDATA', os.path.expanduser('~/.config'))) / 'PolyBot'
        self.key_path = self.appdata_dir / 'secret.key'
        self.config_path = Path('config.enc')
        self.fernet = None
        self._initialize_key()

    def _initialize_key(self):
        try:
            self.appdata_dir.mkdir(parents=True, exist_ok=True)
            if not self.key_path.exists():
                key = Fernet.generate_key()
                self.key_path.write_bytes(key)
                logger_instance.info("ConfigManager", "Generated new encryption key")
            
            key = self.key_path.read_bytes()
            self.fernet = Fernet(key)
        except Exception as e:
            logger_instance.critical("ConfigManager", f"Key initialization failed: {str(e)}")

    def load_config(self) -> dict:
        if not self.config_path.exists():
            return {}
        try:
            encrypted_data = self.config_path.read_bytes()
            decrypted_data = self.fernet.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode('utf-8'))
        except Exception as e:
            logger_instance.error("ConfigManager", f"Config load failed: {str(e)}")
            return {}

    def save_config(self, config_data: dict):
        try:
            json_data = json.dumps(config_data).encode('utf-8')
            encrypted_data = self.fernet.encrypt(json_data)
            self.config_path.write_bytes(encrypted_data)
            logger_instance.info("ConfigManager", "Config saved successfully")
        except Exception as e:
            logger_instance.error("ConfigManager", f"Config save failed: {str(e)}")
