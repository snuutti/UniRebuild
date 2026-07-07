import ctypes
import logging
import os
import re
import subprocess

import yaml

from unirebuild.context import PatcherContext
from unirebuild.steps import PatcherStep


class RecoverSpriteMaskLayers(PatcherStep):
    def __init__(self, file_extensions: set[str] | None = None):
        if file_extensions is None:
            file_extensions = {".prefab", ".unity"}
        self.file_extensions = file_extensions

    def get_dependencies(self) -> list[str]:
        return ["git"]

    @staticmethod
    def get_git_file_content(context: PatcherContext, file_path: str) -> str | None:
        rel_path = os.path.relpath(file_path, context.workspace_dir)
        git_path = context.find_executable("git")

        try:
            content = subprocess.check_output(
                [git_path, "show", f"HEAD:{rel_path}"], cwd=context.workspace_dir
            )
            return content.decode("utf-8")
        except subprocess.CalledProcessError:
            logging.warning("Failed to get Git content for '%s'!", rel_path)
            return None

    @staticmethod
    def parse_sprite_masks(lines: list[str]) -> dict[str, dict[str, str]]:
        masks = {}
        header_pattern = re.compile(r"^--- !u!\d+ &(\d+)")

        for i in range(len(lines) - 1):
            if lines[i + 1].strip() != "SpriteMask:":
                continue

            match = header_pattern.match(lines[i].strip())
            if not match:
                continue

            anchor_id = match.group(1)
            front_value = None
            front_index = None
            front_layerid_index = None
            back_value = None
            back_index = None
            back_layerid_index = None

            j = i + 1
            while j < len(lines):
                line = lines[j]
                if j > i + 1 and line.startswith("---"):
                    break

                if "m_FrontSortingLayer:" in line:
                    parts = line.split(":")
                    if len(parts) >= 2:
                        front_value = parts[1].strip()
                        front_index = j
                if "m_FrontSortingLayerID:" in line:
                    parts = line.split(":")
                    if len(parts) >= 2:
                        front_layerid_index = j
                elif "m_BackSortingLayer:" in line:
                    parts = line.split(":")
                    if len(parts) >= 2:
                        back_value = parts[1].strip()
                        back_index = j
                elif "m_BackSortingLayerID:" in line:
                    parts = line.split(":")
                    if len(parts) >= 2:
                        back_layerid_index = j

                j += 1

            masks[anchor_id] = {
                "front": front_value,
                "front_index": front_index,
                "front_layerid_index": front_layerid_index,
                "back": back_value,
                "back_index": back_index,
                "back_layerid_index": back_layerid_index,
            }

        return masks

    @staticmethod
    def get_tag_ids(context: PatcherContext) -> dict[int, int]:
        tag_ids = {}

        try:
            tag_manager_path = os.path.join(
                context.workspace_dir, "ProjectSettings", "TagManager.asset"
            )
            with open(tag_manager_path, "r", encoding="utf-8") as f:
                content = f.readlines()
                content.pop(0)
                content.pop(0)
                content.pop(0)
                data = yaml.safe_load("".join(content))
        except Exception as e:
            raise RuntimeError(f"Failed to read TagManager.asset: {e}")

        if not data or "TagManager" not in data:
            raise RuntimeError("TagManager.asset is missing 'TagManager' section.")

        tag_manager = data["TagManager"]
        if "m_SortingLayers" not in tag_manager:
            raise RuntimeError("TagManager.asset is missing 'm_SortingLayers' section.")

        sorting_layers = tag_manager["m_SortingLayers"]
        for i in range(len(sorting_layers)):
            layer = sorting_layers[i]
            unique_id = layer["uniqueID"]
            signed_unique_id = ctypes.c_int32(unique_id).value
            tag_ids[i] = signed_unique_id

        return tag_ids

    @staticmethod
    def update_sprite_mask(
        tag_ids: dict[int, int],
        lines: list[str],
        new_values: dict[str, str],
        old_values: dict[str, str],
        front: bool,
    ) -> bool:
        key = "front" if front else "back"
        index_key = f"{key}_index"
        layerid_index_key = f"{key}_layerid_index"
        sorting_layer_key = f"m_{key.capitalize()}SortingLayer:"
        sorting_layerid_key = f"m_{key.capitalize()}SortingLayerID:"

        if new_values[key] == old_values[key]:
            return False

        modified = False

        index = int(new_values[index_key])
        line = lines[index]
        match = re.match(rf"^(\s*{sorting_layer_key}\s*)", line)
        if match:
            lines[index] = f"{match.group(1)}{old_values[key]}\n"
            modified = True

        index2 = int(new_values[layerid_index_key])
        line2 = lines[index2]
        match2 = re.match(rf"^(\s*{sorting_layerid_key}\s*)", line2)
        if match2:
            tag_id = tag_ids[int(old_values[key])]
            lines[index2] = f"{match2.group(1)}{tag_id}\n"
            modified = True

        return modified

    def process_file(
        self, context: PatcherContext, tag_ids: dict[int, int], file_path: str
    ):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                if "SpriteMask:" not in content:
                    return
        except Exception as e:
            raise RuntimeError(f"Failed to read '{file_path}': {e}")

        old_content = self.get_git_file_content(context, file_path)
        if not old_content:
            return

        old_lines = old_content.splitlines()
        old_masks = self.parse_sprite_masks(old_lines)
        if not old_masks:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                new_lines = f.readlines()
        except Exception as e:
            raise RuntimeError(f"Failed to read '{file_path}': {e}")

        new_masks = self.parse_sprite_masks(new_lines)
        modified = False

        for anchor_id, old_values in old_masks.items():
            if anchor_id not in new_masks:
                continue

            new_values = new_masks[anchor_id]

            modified |= self.update_sprite_mask(
                tag_ids, new_lines, new_values, old_values, True
            )
            modified |= self.update_sprite_mask(
                tag_ids, new_lines, new_values, old_values, False
            )

        if modified:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.writelines(new_lines)
                logging.info("Recovered SpriteMask layers in '%s'.", file_path)
            except Exception as e:
                raise RuntimeError(f"Failed to write '{file_path}': {e}")

    def execute(self, context: PatcherContext):
        tag_ids = self.get_tag_ids(context)

        for root, _, files in os.walk(os.path.join(context.workspace_dir, "Assets")):
            if ".git" in root:
                continue

            for file in files:
                if any(file.endswith(ext) for ext in self.file_extensions):
                    file_path = os.path.join(root, file)
                    self.process_file(context, tag_ids, file_path)
