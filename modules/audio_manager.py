import re
from typing import List, Dict, Optional, NamedTuple
import sounddevice as sd

class DeviceIdentifier(NamedTuple):
    """Unique identifier for an audio device that persists across sessions"""
    name: str
    channels: int
    default_samplerate: float

def create_device_identifier(device: Dict[str, any]) -> DeviceIdentifier:
    """Creates a persistent identifier for a device"""
    return DeviceIdentifier(
        name=device['name'],
        channels=device['max_input_channels'],  # Match the key used in device info
        default_samplerate=device['default_samplerate']
    )

def find_device_by_identifier(identifier: DeviceIdentifier) -> Optional[Dict[str, any]]:
    """Finds the best matching device for a saved identifier"""
    devices = get_input_devices()

    # First try exact match
    for device in devices:
        if create_device_identifier(device) == identifier:
            return device

    # Fall back to name match with best specs
    matching_devices = [
        d for d in devices
        if d['name'] == identifier.name
    ]

    if matching_devices:
        return max(
            matching_devices,
            key=lambda d: (d['max_input_channels'], d['default_samplerate'])
        )

    return None

def get_device_by_id(device_id: int) -> Optional[Dict[str, any]]:
    """Gets device info by ID, returns None if device not found"""
    try:
        device = sd.query_devices(device_id)
        if device['max_input_channels'] > 0:
            return {
                'id': device_id,
                'name': device['name'],
                'max_input_channels': device['max_input_channels'],
                'hostapi': device['hostapi'],
                'default_samplerate': device['default_samplerate']
            }
        return None
    except:
        return None

def get_input_devices() -> List[Dict[str, any]]:
    """Returns a list of available input (microphone) devices"""
    devices = []
    seen_devices: Dict[str, Dict] = {}  # Track devices by original name

    # Get all devices first
    all_devices = sd.query_devices()

    # Filter for input devices
    for i in range(len(all_devices)):
        device = all_devices[i]
        if device['max_input_channels'] > 0:
            device_info = {
                'id': i,
                'name': device['name'],
                'max_input_channels': device['max_input_channels'],  # Changed key name
                'hostapi': device['hostapi'],
                'default_samplerate': device['default_samplerate']
            }

            # If we haven't seen this device, or if this variant is "better"
            if device['name'] not in seen_devices or (
                device_info['max_input_channels'] > seen_devices[device['name']]['max_input_channels'] or
                (device_info['max_input_channels'] == seen_devices[device['name']]['max_input_channels'] and
                 device_info['default_samplerate'] > seen_devices[device['name']]['default_samplerate'])
            ):
                seen_devices[device['name']] = device_info

    return list(seen_devices.values())

def get_default_device_id() -> int:
    """Returns the system default input device ID"""
    device = sd.query_devices(None, kind='input')
    return device['index']

def set_input_device(device_id: int) -> None:
    """Sets the active input device for recording"""
    sd.default.device[0] = device_id  # Sets input device only

def get_all_device_variants() -> Dict[str, List[Dict[str, any]]]:
    """Returns all variants of input devices grouped by device name"""
    device_groups: Dict[str, List[Dict]] = {}

    for i, device in enumerate(sd.query_devices()):
        if device['max_input_channels'] > 0:
            original_name = device['name']

            if original_name not in device_groups:
                device_groups[original_name] = []

            device_groups[original_name].append({
                'id': i,
                'name': original_name,
                'channels': device['max_input_channels'],
                'hostapi': device['hostapi'],
                'default_samplerate': device['default_samplerate']
            })

    return device_groups

def is_valid_device_id(device_id: int) -> bool:
    """Checks if a device ID exists in the current device list"""
    return any(device['id'] == device_id for device in get_input_devices())

if __name__ == '__main__':
    print("Available Input Devices (Grouped):")
    print("-----------------------")
    device_groups = get_all_device_variants()
    default_id = get_default_device_id()

    for base_name, variants in device_groups.items():
        print(f"\nDevice: {base_name}")
        for variant in variants:
            default_marker = " (Default)" if variant['id'] == default_id else ""
            print(f"  ID: {variant['id']}{default_marker}")
            print(f"  Channels: {variant['channels']}")
            print(f"  Host API: {variant['hostapi']}")
            print(f"  Sample Rate: {variant['default_samplerate']} Hz")
            print("  -----------------------")

    print(f"\nTotal unique devices: {len(device_groups)}")
    print(f"Total variants across all devices: {sum(len(variants) for variants in device_groups.values())}")
