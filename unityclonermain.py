import os
import sys
import subprocess
import shutil
import ctypes
import time

        #   -   -   -   -   -   -   -   -   -   -   #
                # tools
        #   -   -   -   -   -   -   -   -   -   -   #

def is_admin() -> bool:
    """Check if the script has admin permissions."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def clean_letter(letter: str) -> str:
    """Normalizes a drive letter: 'e', 'E:', 'E:\\' -> 'E:'"""
    letter = letter.strip().upper()
    if letter.endswith("\\") or letter.endswith("/"):
        letter = letter[:-1]
    if len(letter) == 1 and letter.isalpha():
        letter = letter + ":"
    return letter

def drive_exists(letter: str) -> bool:
    """Returns True if the drive is mounted and accessible."""
    path = letter + "\\"
    return os.path.exists(path)

def ask_letter(message: str) -> str:
    """Prompts the user for a drive letter and validates it."""
    while True:
        entry = input(message).strip()
        if not entry:
            print("You haven't written anything. Try again.")
            continue
        letter = clean_letter(entry)
        if len(letter) != 2 or not letter[0].isalpha() or letter[1] != ":":
            print("Wrong format. Write only the letter (e.g. E).")
            continue
        if not drive_exists(letter):
            print(f"Drive {letter} does not exist or is not connected.")
            continue
        return letter


def readable_size(num_bytes: int) -> str:
    """Converts bytes to a human-readable string (KB, MB, GB)."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(num_bytes) < 1024.0:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} PB"

def free_space(letter: str) -> int:
    """Returns the free space in bytes for a drive."""
    total, used, free = shutil.disk_usage(letter + "\\")
    return free

def used_space(letter: str) -> int:
    """Returns the used space in bytes for a drive."""
    total, used, free = shutil.disk_usage(letter + "\\")
    return used

        #   -   -   -   -   -   -   -   -   -   -   #
                # main program
        #   -   -   -   -   -   -   -   -   -   -   #

def step1_source() -> str:
    print("\n" + "=" * 50)
    print("Step 1 - Select SOURCE drive")
    print("=" * 50)
    letter = ask_letter("Enter the letter of the source USB drive: ")
    used = used_space(letter)
    print(f"Source drive: {letter}\\   ({readable_size(used)} in use)")
    return letter


def step2_destination(source: str) -> str:
    print("\n" + "=" * 50)
    print("Step 2 - Select DESTINATION drive")
    print("=" * 50)
    while True:
        letter = ask_letter("Enter the letter of the destination USB drive: ")
        if letter.upper() == source.upper():
            print("The destination cannot be the same drive as the source.")
            continue
        free = free_space(letter)
        source_used = used_space(source)
        print(f"  Destination drive: {letter}\\")
        print(f"     Free space on destination : {readable_size(free)}")
        print(f"     Used space on source      : {readable_size(source_used)}")
        if free < source_used:
            print("WARNING: The destination may not have enough space.")
            go_on = input("Do you want to continue anyway? (y/n): ").strip().lower()
            if go_on != "y":
                continue
        return letter


def step3_drive_name() -> str:
    print("\n" + "=" * 50)
    print("Step 3 - New drive name")
    print("=" * 50)
    while True:
        name = input("  Enter the new name (label) for the destination drive: ").strip()
        if not name:
            print("  The name cannot be empty.")
            continue
        if len(name) > 32:
            print("  The name cannot exceed 32 characters (NTFS limit).")
            continue
        return name


def step4_confirm(source: str, destination: str, name: str) -> None:
    print("\n" + "=" * 50)
    print("Summary")
    print("=" * 50)
    print(f"Source drive      : {source}\\")
    print(f"Destination drive : {destination}\\")
    print(f"Destination name  : {name}")
    print()
    print("The destination drive is about to be FORMATTED.")
    print("ALL data on it will be ERASED.")
    print()
    confirm = input("Type 'Y' to continue: ").strip()
    if confirm != "Y":
        print("\n  Operation cancelled by the user.")
        sys.exit(0)


def step5_format(destination: str, name: str) -> None:
    print("\n" + "=" * 50)
    print("Step 4 - Formatting destination drive as NTFS...")
    print("=" * 50)
    cmd = ["format", destination, "/FS:NTFS", f"/V:{name}", "/Q", "/Y"]

    print(f"  Running: {' '.join(cmd)}\n")
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        shell=True
    )

    if result.stdout:
        for line in result.stdout.splitlines():
            print(f"    {line}")
    if result.stderr:
        for line in result.stderr.splitlines():
            print(f"    [err] {line}")

    if result.returncode != 0:
        print(f"\n  Format failed (code {result.returncode}).")
        sys.exit(1)

    print("\n  Format complete.")
    time.sleep(2)

def step6_copy(source: str, destination: str) -> None:
    print("\n" + "=" * 50)
    print("Step 5 - Copying files...")
    print("=" * 50)

    source_path      = source      + "\\"
    destination_path = destination + "\\"
    cmd = [
        "robocopy",
        source_path,
        destination_path,
        "/E",
        "/COPYALL",
        "/XD",
            "System Volume Information",
        "/R:5",
        "/W:1",
    ]

    print(f"  Running: {' '.join(cmd)}\n")
    result = subprocess.run(cmd, shell=False)
    if result.returncode >= 8:
        print(f"\n  Copy failed (robocopy code: {result.returncode}).")
        sys.exit(1)

    print(f"\n  Copy complete (robocopy code: {result.returncode}).")

        #   -   -   -   -   -   -   -   -   -   -   #
                # input zone (visible part)
        #   -   -   -   -   -   -   -   -   -   -   #
        
def main():
    print("\n" + "+" + "=" * 26 + "+")
    print("|     Partition Cloner     |")
    print("+" + "=" * 26 + "+")

    if sys.platform != "win32":
        print("\n  This script only works on Windows.")
        sys.exit(1)

    if not is_admin():
        print("  Requesting administrator permissions...")
        params = " ".join(f'"{a}"' for a in sys.argv)
        ret = ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            sys.executable,
            params,
            None,
            1
        )
        if ret <= 32:
            print("Error: could not obtain administrator permissions.")
            input("Press ENTER to exit...")
        sys.exit(0)

    source      = step1_source()
    destination = step2_destination(source)
    name        = step3_drive_name()

    step4_confirm(source, destination, name)
    step5_format(destination, name)
    step6_copy(source, destination)

    print("\n" + "=" * 50)
    print("  Done! The destination drive is a")
    print(f"  clone of {source}\\ named '{name}'.")
    print("=" * 50 + "\n")
    input("  Press ENTER to exit...")


if __name__ == "__main__":
    main()