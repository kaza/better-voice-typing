from typing import Tuple
import requests
import os
import sys
import shutil
import zipfile
from pathlib import Path

def get_latest_release() -> Tuple[str, str]:
    """Get the latest release version and download URL from GitHub."""
    try:
        response = requests.get(
            "https://github.com/Elevate-Code/better-voice-typing/releases/latest"
        )
        response.raise_for_status()
        data = response.json()
        return data["tag_name"], data["zipball_url"]
    except Exception as e:
        print(f"Error checking for updates: {e}")
        return None, None

def get_current_version() -> str:
    """Read current version from version.txt."""
    try:
        with open("version.txt", "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "0.0.0"

def verify_backup_integrity(backup_dir: Path, preserve_items: list) -> bool:
    """Verify all important files were backed up correctly."""
    for item in preserve_items:
        backup_path = backup_dir / item
        if not backup_path.exists():
            return False
    return True

def download_and_extract(url: str, temp_dir: Path) -> bool:
    """Download and extract the latest release."""
    try:
        # Backup important user files first
        backup_dir = temp_dir / "backup"
        backup_dir.mkdir(exist_ok=True)

        # List of files/folders to preserve
        preserve_items = [
            '.env',                    # API keys and user settings
            'venv',                    # Virtual environment
            'transcription_history',   # User's transcription history
            'user_settings.json',      # Any additional user settings
            'custom_shortcuts.json'    # Any custom keyboard shortcuts
        ]

        # Create backups
        for item in preserve_items:
            src = Path.cwd() / item
            if src.exists():
                if src.is_dir():
                    shutil.copytree(src, backup_dir / item, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, backup_dir / item)

        # Download and extract new version
        response = requests.get(url, stream=True)
        response.raise_for_status()

        zip_path = temp_dir / "update.zip"
        with open(zip_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Extract to a temporary directory
            extract_dir = temp_dir / "extracted"
            zip_ref.extractall(extract_dir)

            # Get the extracted folder name (usually includes the repo name and commit hash)
            extracted_folder = next(extract_dir.iterdir())

            # Update files while preserving user data
            for item in extracted_folder.iterdir():
                if item.name not in preserve_items:
                    dest = Path.cwd() / item.name
                    if dest.exists():
                        if dest.is_dir():
                            shutil.rmtree(dest)
                        else:
                            dest.unlink()
                    if item.is_dir():
                        shutil.copytree(item, dest)
                    else:
                        shutil.copy2(item, dest)

        # Restore preserved files from backup
        for item in preserve_items:
            backup_path = backup_dir / item
            if backup_path.exists():
                dest = Path.cwd() / item
                if dest.exists():
                    if dest.is_dir():
                        shutil.rmtree(dest)
                    else:
                        dest.unlink()
                if backup_path.is_dir():
                    shutil.copytree(backup_path, dest)
                else:
                    shutil.copy2(backup_path, dest)

        if not verify_backup_integrity(backup_dir, preserve_items):
            print("Backup verification failed, aborting update")
            return False

        return True
    except Exception as e:
        # If anything fails, try to restore from backup
        try:
            for item in preserve_items:
                backup_path = backup_dir / item
                if backup_path.exists():
                    dest = Path.cwd() / item
                    if backup_path.is_dir():
                        shutil.copytree(backup_path, dest, dirs_exist_ok=True)
                    else:
                        shutil.copy2(backup_path, dest)
        except Exception as restore_error:
            print(f"Error restoring backup: {restore_error}")

        print(f"Error downloading/extracting update: {e}")
        return False

def update_app() -> bool:
    """Check for and apply updates if available."""
    current = get_current_version()
    latest, download_url = get_latest_release()

    if not latest or not download_url:
        return False

    if latest == current:
        print("Already up to date!")
        return True

    print(f"Updating from version {current} to {latest}")

    temp_dir = Path("temp_update")
    temp_dir.mkdir(exist_ok=True)

    try:
        if download_and_extract(download_url, temp_dir):
            print("Update successful!")
            return True
        return False
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    success = update_app()
    sys.exit(0 if success else 1)