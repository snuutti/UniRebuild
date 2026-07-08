import collections
import glob
import logging
import os
from typing import Optional, List

import yaml

from unirebuild.context import PatcherContext
from unirebuild.steps import PatcherStep


class FlowDict(dict):
    pass


def represent_flow_dict(self: yaml.Dumper, data: FlowDict) -> yaml.Node:
    return self.represent_mapping("tag:yaml.org,2002:map", data, flow_style=True)


def represent_none(self: yaml.Dumper, _) -> yaml.Node:
    return self.represent_scalar("tag:yaml.org,2002:str", " ")


class PopulateTextureSettings(PatcherStep):
    def __init__(
        self,
        required_order: Optional[List[str]] = None,
        search_patterns: Optional[List[str]] = None,
    ):
        self.required_order = required_order or [
            "DefaultTexturePlatform",
            "Standalone",
            "Android",
            "iPhone",
            "WebGL",
        ]

        self.search_patterns = search_patterns or [
            os.path.join("Assets", "**", "*.png.meta")
        ]

    def execute(self, context: PatcherContext):
        logging.info("Populating texture platform settings...")

        yaml.add_representer(FlowDict, represent_flow_dict)
        yaml.add_representer(type(None), represent_none)

        meta_paths = []
        for pattern in self.search_patterns:
            full_pattern = os.path.join(context.workspace_dir, pattern)
            meta_paths.extend(glob.glob(full_pattern, recursive=True))

        meta_paths = list(set(meta_paths))

        for meta_path in meta_paths:
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)

                if not data or "TextureImporter" not in data:
                    logging.warning(
                        "No TextureImporter section found in '%s'. Skipping.", meta_path
                    )
                    continue

                importer = data["TextureImporter"]
                if "platformSettings" not in importer:
                    continue

                settings_list = importer["platformSettings"]

                existing_targets = collections.defaultdict(list)
                for entry in settings_list:
                    name = entry.get("buildTarget")
                    existing_targets[name].append(entry)

                standalone_template = None
                if existing_targets["Standalone"]:
                    standalone_template = existing_targets["Standalone"][0]
                elif existing_targets["DefaultTexturePlatform"]:
                    standalone_template = existing_targets["DefaultTexturePlatform"][0]

                if not standalone_template:
                    logging.warning(
                        "No suitable template found for '%s'. Skipping.", meta_path
                    )
                    continue

                new_settings_list = []
                modified = False

                for target in self.required_order:
                    if target in existing_targets:
                        new_settings_list.extend(existing_targets[target])
                    else:
                        new_entry = standalone_template.copy()
                        new_entry["buildTarget"] = target
                        new_entry["overridden"] = 0
                        new_settings_list.append(new_entry)
                        modified = True

                for target_name, entries in existing_targets.items():
                    if target_name not in self.required_order:
                        new_settings_list.extend(entries)

                if not modified and new_settings_list != settings_list:
                    modified = True

                if modified:
                    importer["platformSettings"] = new_settings_list

                    for key in ["spritePivot", "spriteBorder"]:
                        if key in importer and isinstance(importer[key], dict):
                            importer[key] = FlowDict(importer[key])

                    if "spriteSheet" in importer:
                        sheet = importer["spriteSheet"]
                        if "outline" in sheet and isinstance(sheet["outline"], list):
                            for polygon in sheet["outline"]:
                                if isinstance(polygon, list):
                                    for i in range(len(polygon)):
                                        if isinstance(polygon[i], dict):
                                            polygon[i] = FlowDict(polygon[i])

                    with open(meta_path, "w", encoding="utf-8") as f:
                        content = yaml.dump(data, sort_keys=False)
                        content = content.replace("' '", "")
                        f.write(content)

                    logging.info("Updated platform settings in '%s'.", meta_path)
            except Exception as e:
                raise RuntimeError(f"Failed to process '{meta_path}': {e}")
