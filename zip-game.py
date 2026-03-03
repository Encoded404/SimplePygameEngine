import os
import zipfile
import argparse

# List of game names to create individual zip files for
game_names = [
    "2DShooter",
    "adventure",
    "pong"
]

# Base files that are common to all games
base_files_to_pack = [
    # Do not include virtual environment (OS-specific). Use requirements.txt instead.
    "requirements.txt",
    "engine" + os.sep + "core.py",
    "engine" + os.sep + "createBackgrounds.py",
    "engine" + os.sep + "internal_sprites" + os.sep + "missing_texture.png"
]

# Minimum required files/folders that must exist in each game directory (relative to ./_[name]/ directory)
# If any of these are missing, the game will be skipped. If all exist, ALL files in the game directory are packed.
game_specific_files = [
    "game.py",
]

game_specific_files_reccomended = [
    "sprites" + os.sep,
    "levels" + os.sep
]

def create_game_zip(game_name):
    """Create a zip file for a specific game"""
    # Create zipped subfolder if it doesn't exist
    zipped_dir = "zipped"
    if not os.path.exists(zipped_dir):
        os.makedirs(zipped_dir)
    
    output_zip_file = os.path.join(zipped_dir, f"packed_game_{game_name}.zip")
    game_dir = f"_{game_name}"
    
    print(f"Creating zip for game: {game_name}")
    
    if not os.path.exists(game_dir):
        print(f"Warning: Game directory {game_dir} does not exist. Skipping {game_name}.")
        return None
    
    with zipfile.ZipFile(output_zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add base/common files
        for item in base_files_to_pack:
            if os.path.exists(item):
                if os.path.isdir(item):
                    for root, dirs, files in os.walk(item):
                        for file in files:
                            file_path = os.path.join(root, file)
                            zipf.write(file_path, file_path)
                else:
                    zipf.write(item, item)
            else:
                print(f"Warning: Base file \"{item}\" not found")
                return None

        # Add generated setup scripts for Linux and Windows into the zip
        linux_setup = """#!/bin/sh
set -e
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
echo "Setup complete"
"""

        windows_setup = """@echo off
python -m venv .venv
call .venv\\Scripts\\activate
python -m pip install -r requirements.txt
echo Setup complete
"""

        try:
            from zipfile import ZipInfo
            import time

            zi = ZipInfo('setup_linux.sh')
            zi.date_time = tuple(time.localtime()[:6])
            zi.external_attr = 0o755 << 16  # Unix executable bit
            zipf.writestr(zi, linux_setup)

            zi = ZipInfo('setup_windows.bat')
            zi.date_time = tuple(time.localtime()[:6])
            zi.external_attr = 0o644 << 16
            zipf.writestr(zi, windows_setup)
        except Exception as e:
            print(f"Warning: failed to add generated setup scripts: {e}")

        # Check if all required game files exist first (minimum requirements)
        missing_files = []
        for item in game_specific_files:
            game_file_path = os.path.join(game_dir, item)
            if not os.path.exists(game_file_path):
                missing_files.append(item)
        
        if missing_files:
            print(f"ERROR: Required game files missing for {game_name}: {missing_files}")
            print(f"Skipping {game_name} - minimum requirements not met")
            return None
        
        missing_optional_files = []
        for item in game_specific_files_reccomended:
            game_file_path = os.path.join(game_dir, item)
            if not os.path.exists(game_file_path):
                missing_optional_files.append(item)

        if missing_optional_files:
            print(f"WARNING: these files: {missing_optional_files} are very common in games, but missing for {game_name}. The game might not be structured correctly. if these are not needed, ignore this")
        
        
        # All required files exist, now add ALL files from the game directory
        for root, dirs, files in os.walk(game_dir):
            for file in files:
                file_path = os.path.join(root, file)
                # Store with relative path (without the ._[name] prefix)
                arc_name = os.path.relpath(file_path, game_dir)
                zipf.write(file_path, arc_name)
    
    print(f"Created {output_zip_file}")
    return output_zip_file

# look for removable media (like a USB drive) and copy the zip file there
import shutil
def find_removable_drives():
    drives = []
    if os.name == 'nt':  # Windows
        import string
        from ctypes import windll

        bitmask = windll.kernel32.GetLogicalDrives()
        for letter in string.ascii_uppercase:
            if bitmask & 1:
                drive_type = windll.kernel32.GetDriveTypeW(f"{letter}:/")
                if drive_type == 2:  # DRIVE_REMOVABLE
                    drives.append(f"{letter}:/")
            bitmask >>= 1
    else:  # Unix-like systems
        # Method 1: Check /sys/block for removable devices
        block_devices = []
        try:
            for device in os.listdir('/sys/block'):
                removable_path = f'/sys/block/{device}/removable'
                if os.path.exists(removable_path):
                    with open(removable_path, 'r') as f:
                        if f.read().strip() == '1':
                            block_devices.append(f'/dev/{device}')
        except (OSError, IOError):
            pass
        
        # Method 2: Check mounted filesystems for removable devices
        try:
            with open('/proc/mounts', 'r') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2:
                        device, mount_point = parts[0], parts[1]
                        # Check if this device is in our removable list
                        device_base = device.rstrip('0123456789')  # Remove partition numbers
                        if device_base in block_devices:
                            # Additional check: skip if mounted on system directories
                            if not any(mount_point.startswith(sys_dir) for sys_dir in 
                                     ['/', '/boot', '/home', '/usr', '/var', '/tmp', '/opt']):
                                drives.append(mount_point)
        except (OSError, IOError):
            pass
        
        # Method 3: Fallback - check common mount points for media
        if not drives:
            common_media_paths = ['/media', '/mnt', '/run/media']
            for base_path in common_media_paths:
                if os.path.exists(base_path):
                    try:
                        # Handle direct mounts (like /media/drive or /mnt/drive)
                        for item in os.listdir(base_path):
                            item_path = os.path.join(base_path, item)
                            if os.path.isdir(item_path):
                                if os.path.ismount(item_path):
                                    drives.append(item_path)
                                else:
                                    # Handle nested structure (like /run/media/username/drive)
                                    try:
                                        for subitem in os.listdir(item_path):
                                            subitem_path = os.path.join(item_path, subitem)
                                            if os.path.isdir(subitem_path) and os.path.ismount(subitem_path):
                                                drives.append(subitem_path)
                                    except (OSError, IOError):
                                        continue
                    except (OSError, IOError):
                        continue
    
    return drives

def copy_zip_to_removable_drive(zip_file, game_name):
    drives = find_removable_drives()
    index = 0
    if drives:
        for drive in drives:
            print(f"copy {game_name} to removable drive: {drive}?")
            if(input().lower() in ['y', 'yes']):
                # Copy the zip file to the first removable drive found
                shutil.copy(zip_file, drives[0])
                print(f"Copied {zip_file} to {drives[0]}")
                break
    else:
        print("No removable drive found.")

def main(argv=None):
    parser = argparse.ArgumentParser(description="Pack games into zips (non-interactive for CI)")
    parser.add_argument("--games", nargs="*", help="Games to pack (default: all)", default=None)
    parser.add_argument("--copy-to", help="Copy zips to this path (non-interactive)")
    parser.add_argument("--auto-copy-first-drive", action="store_true", help="Auto-copy zips to first removable drive if found")
    args = parser.parse_args(argv)

    to_pack = args.games if args.games else game_names

    created = []
    for g in to_pack:
        z = create_game_zip(g)
        if z:
            created.append((z, g))

    if args.copy_to:
        for zip_file, _ in created:
            try:
                shutil.copy(zip_file, args.copy_to)
                print(f"Copied {zip_file} to {args.copy_to}")
            except Exception as e:
                print(f"Error copying {zip_file} to {args.copy_to}: {e}")
    elif args.auto_copy_first_drive:
        drives = find_removable_drives()
        if drives:
            dest = drives[0]
            for zip_file, _ in created:
                try:
                    shutil.copy(zip_file, dest)
                    print(f"Copied {zip_file} to {dest}")
                except Exception as e:
                    print(f"Error copying {zip_file} to {dest}: {e}")
        else:
            print("No removable drive found.")
    else:
        # preserve original interactive behavior when no args provided
        for zip_file, game_name in created:
            copy_zip_to_removable_drive(zip_file, game_name)


if __name__ == "__main__":
    main()