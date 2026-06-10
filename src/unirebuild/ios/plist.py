import os
import plistlib
from typing import Any


def extract_plist_icon_filenames(plist_path: str) -> list[str]:
    if not os.path.exists(plist_path):
        raise FileNotFoundError(f"The .plist file '{plist_path}' does not exist.")

    with open(plist_path, "rb") as fp:
        try:
            plist_data = plistlib.load(fp)
        except Exception as e:
            raise ValueError(f"Failed to parse .plist file: {e}")

    found_icons = []

    def walk_plist(obj: Any, key: str | None = None):
        if isinstance(obj, dict):
            for k, v in obj.items():
                walk_plist(v, k)
        elif isinstance(obj, list):
            if key and "CFBundleIconFiles" in key:
                for item in obj:
                    if isinstance(item, str):
                        found_icons.append(item)
            else:
                for item in obj:
                    walk_plist(item, key)
        elif isinstance(obj, str):
            if key and ("CFBundleIconFile" in key or "CFBundleIconName" in key):
                found_icons.append(obj)

    walk_plist(plist_data)

    valid_icons = []
    for icon in found_icons:
        icon_cleaned = icon.strip()
        if not icon_cleaned:
            continue

        if not icon_cleaned.lower().endswith(".png"):
            icon_cleaned += ".png"

        if icon_cleaned not in valid_icons:
            valid_icons.append(icon_cleaned)

    return valid_icons
