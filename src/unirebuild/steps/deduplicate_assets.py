import collections
import hashlib
import logging
import os
import re

from unirebuild.context import PatcherContext
from unirebuild.steps import PatcherStep


class DeduplicateAssets(PatcherStep):
    def get_file_hash(self, file_path: str) -> str:
        hasher = hashlib.md5()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)

        return hasher.hexdigest()

    def get_meta_filtered(self, file_path: str) -> str:
        if not os.path.exists(file_path):
            return ""

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            filtered_liens = [line for line in lines if not line.startswith("guid: ")]
            return "".join(filtered_liens)
        except Exception as e:
            logging.error("Failed to read and filter '%s': %s", file_path, e)
            return ""

    def deduplicate_assets(self, context: PatcherContext) -> int:
        logging.info("Scanning for duplicate assets...")

        asset_map = collections.defaultdict(list)
        duplicate_pattern = re.compile(r"^(.*?)(?:_(\d+))?(\.[^.]+)$")
        guid_map = {}

        for root, _, files in os.walk(os.path.join(context.workspace_dir, "Assets")):
            if ".git" in root:
                continue

            for file in files:
                if file.endswith(".meta"):
                    continue

                match = duplicate_pattern.match(file)
                if match:
                    base_name = match.group(1)
                    extension = match.group(3)
                    asset_map[(root, base_name, extension)].append(
                        os.path.join(root, file)
                    )

        count = 0
        for (_, _, _), paths in asset_map.items():
            if len(paths) < 2:
                continue

            paths.sort(key=lambda x: (len(x), x))
            kept_variants = []

            for asset_path in paths:
                try:
                    current_hash = self.get_file_hash(asset_path)
                    current_meta = asset_path + ".meta"
                    current_meta_content = self.get_meta_filtered(current_meta)

                    with open(
                        current_meta, "r", encoding="utf-8", errors="ignore"
                    ) as f:
                        guid_match = re.search(r"guid: ([a-f0-9]{32})", f.read())
                        if not guid_match:
                            continue
                        current_guid = guid_match.group(1)

                    matching_guid = None
                    for m_hash, m_meta, m_guid in kept_variants:
                        if current_hash == m_hash and current_meta_content == m_meta:
                            matching_guid = m_guid
                            break

                    if matching_guid:
                        logging.info("Removing duplicate asset '%s'...", asset_path)
                        os.remove(asset_path)
                        if os.path.isfile(current_meta):
                            guid_map[current_guid] = matching_guid
                            os.remove(current_meta)
                        count += 1
                    else:
                        kept_variants.append(
                            (current_hash, current_meta_content, current_guid)
                        )

                except Exception as e:
                    logging.error("Failed to process '%s': %s", asset_path, e)
                    continue

        if count > 0:
            logging.info("Removed %d duplicate assets.", count)
        else:
            logging.info("No duplicate assets found.")
            return 0

        if not guid_map:
            logging.info("No GUIDs need to be updated after deduplication.")
            return 0

        logging.info("Updating references to %d deduplicated assets...", len(guid_map))

        guid_pattern = re.compile(r"\b([a-f0-9]{32})\b")

        def guid_replacer(guid_match: re.Match) -> str:
            found_guid = guid_match.group(1)
            return guid_map.get(found_guid, found_guid)

        for root, dirs, files in os.walk(context.workspace_dir):
            if ".git" in root:
                continue

            for file in files:
                # todo: don't process binary files

                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        old_text = f.read()

                    new_text = guid_pattern.sub(guid_replacer, old_text)

                    if new_text != old_text:
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(new_text)
                except Exception as e:
                    raise RuntimeError(
                        f"Failed to update references in '{file_path}': {e}"
                    )

        logging.info("Deduplication reference update finished.")
        return count

    def execute(self, context: PatcherContext):
        while True:
            removed = self.deduplicate_assets(context)
            if removed == 0:
                break
