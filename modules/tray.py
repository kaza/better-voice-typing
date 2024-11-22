import os
import threading
from typing import Any, Dict

import pyperclip
import pystray
from PIL import Image, ImageDraw

from modules.audio_manager import get_input_devices, get_default_device_id, set_input_device, create_device_identifier

def create_tray_icon(icon_path: str) -> Image.Image:
    """Create tray icon from file path"""
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    icon_path = os.path.join(current_dir, icon_path)
    return Image.open(icon_path)

def on_exit(icon, item):
    icon.stop()
    # Ensure clean exit of the application
    os._exit(0)

def create_copy_menu(app):
    """Creates dynamic menu of recent transcriptions"""
    def make_copy_handler(text):
        return lambda icon, item: pyperclip.copy(text)

    return [
        pystray.MenuItem(
            app.history.get_preview(text),
            make_copy_handler(text)
        )
        for text in app.history.get_recent()
    ]

def create_microphone_menu(app):
    """Creates dynamic menu of available microphones"""
    devices = sorted(get_input_devices(), key=lambda d: d['name'].lower())
    current_identifier = app.settings.get('selected_microphone')
    favorite_identifiers = app.settings.get('favorite_microphones')
    default_device_id = get_default_device_id()

    def make_mic_handler(device: Dict[str, any]):
        def handler(icon, item):
            identifier = create_device_identifier(device)._asdict()
            app.settings.set('selected_microphone', identifier)
            set_input_device(device['id'])
        return handler

    def make_favorite_handler(device: Dict[str, any]):
        def handler(icon, item):
            identifier = create_device_identifier(device)._asdict()
            favorites = app.settings.get('favorite_microphones')

            if identifier in favorites:
                favorites.remove(identifier)
            else:
                favorites.append(identifier)

            app.settings.set('favorite_microphones', favorites)
            app.update_icon_menu()
        return handler

    # Create menu items
    select_items = []
    favorite_items = []

    for device in devices:
        identifier = create_device_identifier(device)._asdict()
        is_favorite = identifier in favorite_identifiers
        is_selected = identifier == current_identifier
        is_default = device['id'] == default_device_id

        star_prefix = "💫 " if is_favorite else "    "
        default_prefix = "🎙️ " if is_default else "    "
        combined_prefix = default_prefix if is_default else star_prefix

        select_items.append(
            pystray.MenuItem(
                f"{combined_prefix}{device['name']}",
                make_mic_handler(device),
                checked=lambda item, dev=device: create_device_identifier(dev)._asdict() == current_identifier
            )
        )

        favorite_items.append(
            pystray.MenuItem(
                f"{default_prefix}{device['name']}",
                make_favorite_handler(device),
                checked=lambda item, dev=device: create_device_identifier(dev)._asdict() in favorite_identifiers
            )
        )

    menu_items = [
        pystray.MenuItem(
            'Select Device',
            pystray.Menu(*select_items)
        ),
        pystray.MenuItem(
            'Manage Favorites',
            pystray.Menu(*favorite_items)
        ),
        pystray.MenuItem('Refresh Devices', lambda icon, item: app.refresh_microphones())
    ]

    return menu_items

def setup_tray_icon(app):
    # Create a single icon instance
    icon = pystray.Icon(
        'Voice Typing',
        icon=create_tray_icon('assets/microphone-blue.png')
    )

    def update_icon(emoji_prefix: str, tooltip_text: str) -> None:
        """Update both the tray icon and tooltip"""
        try:
            # Update icon image from current status config
            icon.icon = create_tray_icon(app.status_manager.current_config.tray_icon_file)
            # Update tooltip with status message
            icon.title = f"{emoji_prefix} {tooltip_text}"
        except Exception as e:
            print(f"Error updating tray icon: {e}")

    # Store the update function in the app
    app.update_tray_tooltip = update_icon

    def get_menu():
        # Dynamic menu that updates when called
        copy_menu = create_copy_menu(app)
        microphone_menu = create_microphone_menu(app)

        return pystray.Menu(
            pystray.MenuItem(
                '🔄 Retry Last Transcription',
                lambda icon, item: app.retry_transcription(),
                enabled=lambda item: app.last_recording is not None
            ),
            pystray.MenuItem(
                'Recent Transcriptions',
                pystray.Menu(*copy_menu) if copy_menu else pystray.Menu(
                    pystray.MenuItem('No transcriptions yet', None, enabled=False)
                ),
                enabled=bool(copy_menu)
            ),
            pystray.MenuItem(
                'Microphone',
                pystray.Menu(*microphone_menu)
            ),
            pystray.MenuItem(
                'Settings',
                pystray.Menu(
                    pystray.MenuItem(
                        'Continuous Capture',
                        lambda icon, item: None,
                        checked=lambda item: app.settings.get('continuous_capture')
                    ),
                    pystray.MenuItem(
                        'Clean Transcription',
                        lambda icon, item: app.toggle_clean_transcription(),
                        checked=lambda item: app.settings.get('clean_transcription')
                    ),
                    pystray.MenuItem(
                        'Auto-Stop on Silence',
                        lambda icon, item: app.toggle_silence_detection(),
                        checked=lambda item: app.settings.get('silence_timeout') is not None
                    ),
                    pystray.MenuItem(
                        'Smart Capture',
                        lambda icon, item: None,
                        enabled=False
                    )
                )
            ),
            pystray.MenuItem('Exit', on_exit)
        )

    # Initial menu setup
    icon.menu = get_menu()
    # Store the update function in the app to call it from elsewhere
    app.update_icon_menu = lambda: setattr(icon, 'menu', get_menu()) # Updates the tray icon's menu

    # Start the icon's event loop in its own thread
    threading.Thread(target=icon.run).start()