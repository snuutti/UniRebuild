import hashlib
import logging
import os
import re
import subprocess

from unirebuild.context import PatcherContext
from unirebuild.steps import PatcherStep


class GenerateDeterministicGuids(PatcherStep):
    def __init__(self, new_assets_only: bool = False):
        self.new_assets_only = new_assets_only

    def get_dependencies(self) -> list[str]:
        if self.new_assets_only:
            return ["git"]
        else:
            return super().get_dependencies()

    def execute(self, context: PatcherContext):
        file_list = []

        if self.new_assets_only:
            logging.info("Identifying new .meta files...")

            git_path = context.find_executable("git")

            try:
                untracked_cmd = [git_path, "ls-files", "--others", "--exclude-standard"]
                untracked_files = subprocess.check_output(
                    untracked_cmd, cwd=context.workspace_dir, text=True
                ).splitlines()

                file_list = [f for f in untracked_files if f.endswith(".meta")]
            except subprocess.CalledProcessError:
                raise RuntimeError("Failed to get untracked files from Git.")

            if not file_list:
                logging.info("No new .meta files found.")
                return
        else:
            logging.info("Scanning for all .meta files...")
            for root, dirs, files in os.walk(context.workspace_dir):
                if ".git" in root:
                    continue

                for file in files:
                    if file.endswith(".meta"):
                        relative_path = os.path.relpath(
                            os.path.join(root, file), context.workspace_dir
                        )
                        file_list.append(relative_path)

        logging.info("Calculating deterministic GUIDs for %d files...", len(file_list))
        guid_map = {}

        for meta_path in file_list:
            full_path = os.path.join(context.workspace_dir, meta_path)
            if not os.path.exists(full_path):
                logging.warning(".meta file '%s' does not exist. Skipping.", meta_path)
                continue

            seed_path = meta_path.replace(os.path.sep, "/")
            new_guid = hashlib.md5(seed_path.encode()).hexdigest()

            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                match = re.search(r"guid: ([a-f0-9]{32})", content)
                if not match:
                    logging.warning("No GUID found in '%s'. Skipping.", meta_path)
                    continue

                old_guid = match.group(1)
                if old_guid == new_guid:
                    logging.info(
                        "GUID for '%s' is already deterministic. Skipping.", meta_path
                    )
                    continue

                guid_map[old_guid] = new_guid
                new_content = content.replace(f"guid: {old_guid}", f"guid: {new_guid}")
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
            except Exception as e:
                raise RuntimeError(f"Failed to process '{meta_path}': {e}")

        if not guid_map:
            logging.info("No GUIDs need to be updated.")
            return

        logging.info("Updating references to %d assets...", len(guid_map))

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

        logging.info("GUID regeneration finished.")
