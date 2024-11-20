from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Dict, Any

class AppStatus(Enum):
    IDLE = auto()
    RECORDING = auto()
    PROCESSING = auto()
    ERROR = auto()

@dataclass
class StatusConfig:
    tray_icon: str  # Emoji for tooltip
    tray_icon_file: str  # Path to icon file
    ui_color: str  # Must be valid hex color (e.g., '#FF0000')
    ui_text: str
    ui_fg_color: str = '#FFFFFF'  # Default to white
    pulse: bool = False

class StatusManager:
    STATUS_CONFIGS: Dict[AppStatus, StatusConfig] = {
        AppStatus.IDLE: StatusConfig(
            tray_icon="🎤",
            tray_icon_file='assets/microphone-blue.png',
            ui_color='#333333',
            ui_text="Ready",
            pulse=False
        ),
        AppStatus.RECORDING: StatusConfig(
            tray_icon="⚫",
            tray_icon_file='assets/microphone-red.png',
            ui_color='#FF0000',  # Changed to hex format
            ui_text="🎤 Recording (click to cancel)",
            pulse=True
        ),
        AppStatus.PROCESSING: StatusConfig(
            tray_icon="⚙️",
            tray_icon_file='assets/microphone-yellow.png',
            ui_color='#0066CC',  # Changed to hex format
            ui_text="⚙️ Processing...",
            pulse=True
        ),
        AppStatus.ERROR: StatusConfig(
            tray_icon="⚠️",
            tray_icon_file='assets/microphone-yellow.png',
            ui_color='#FFA500',  # Changed to hex format
            ui_text="⚠️ Error",
            ui_fg_color='#000000',  # Changed to hex format
            pulse=False
        )
    }

    def __init__(self) -> None:
        self._current_status: AppStatus = AppStatus.IDLE
        self._error_message: Optional[str] = None
        self._ui_callback = None
        self._tray_callback = None

    def set_callbacks(self, ui_callback: callable, tray_callback: callable) -> None:
        self._ui_callback = ui_callback
        self._tray_callback = tray_callback

    def set_status(self, status: AppStatus, error_message: Optional[str] = None) -> None:
        self._current_status = status
        self._error_message = error_message

        config = self.STATUS_CONFIGS[status]

        # Update UI
        if self._ui_callback:
            if status == AppStatus.ERROR and error_message:
                self._ui_callback(config, error_message)
            else:
                self._ui_callback(config)

        # Update tray
        if self._tray_callback:
            self._tray_callback(config.tray_icon)

    @property
    def current_status(self) -> AppStatus:
        return self._current_status

    @property
    def current_config(self) -> StatusConfig:
        return self.STATUS_CONFIGS[self._current_status]