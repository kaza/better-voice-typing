import json
import os
from typing import Any, Dict

class Settings:
    def __init__(self) -> None:
        self.settings_file: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'settings.json')
        self.default_settings: Dict[str, Any] = {
            'continuous_capture': True,
            'smart_capture': False,
            'clean_transcription': True,
            'selected_microphone': None,
            'favorite_microphones': []
        }
        self.current_settings: Dict[str, Any] = self.load_settings()
        self._migrate_device_settings()

    def _migrate_device_settings(self) -> None:
        """Migrates old device ID settings to new identifier format"""
        from modules.audio_manager import get_device_by_id, create_device_identifier

        # Migrate selected microphone
        if isinstance(self.current_settings.get('selected_microphone'), int):
            device = get_device_by_id(self.current_settings['selected_microphone'])
            if device:
                identifier = create_device_identifier(device)
                self.current_settings['selected_microphone'] = identifier._asdict()
            else:
                self.current_settings['selected_microphone'] = None

        # Migrate favorite microphones
        if self.current_settings.get('favorite_microphones'):
            new_favorites = []
            for device_id in self.current_settings['favorite_microphones']:
                if isinstance(device_id, int):
                    device = get_device_by_id(device_id)
                    if device:
                        identifier = create_device_identifier(device)
                        new_favorites.append(identifier._asdict())
            self.current_settings['favorite_microphones'] = new_favorites

        self.save_settings()

    def load_settings(self) -> Dict[str, Any]:
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    return {**self.default_settings, **json.load(f)}
            return self.default_settings.copy()
        except Exception as e:
            print(f"Error loading settings: {str(e)}")
            return self.default_settings.copy()

    def save_settings(self) -> None:
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.current_settings, f, indent=4)
        except Exception as e:
            print(f"Error saving settings: {str(e)}")

    def get(self, key: str) -> Any:
        return self.current_settings.get(key, self.default_settings.get(key))

    def set(self, key: str, value: Any) -> None:
        self.current_settings[key] = value
        self.save_settings()