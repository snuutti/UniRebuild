import glob
import logging
import os.path
import shutil

from unirebuild.context import PatcherContext
from unirebuild.steps import PatcherStep


class DeleteAssets(PatcherStep):
    def __init__(self, assets: list[str]):
        self.assets = assets

    def execute(self, context: PatcherContext):
        for asset in self.assets:
            pattern = os.path.join(context.workspace_dir, asset)
            matched_paths = glob.glob(pattern, recursive=True)

            if not matched_paths:
                raise FileNotFoundError(
                    f"Asset or pattern '{asset}' did not match any files at '{pattern}'."
                )

            for full_path in matched_paths:
                if not os.path.exists(full_path):
                    continue

                rel_path = os.path.relpath(full_path, context.workspace_dir)
                logging.info("Deleting asset: %s", rel_path)

                if os.path.isdir(full_path):
                    shutil.rmtree(full_path)
                else:
                    os.remove(full_path)

                meta_path = full_path + ".meta"
                if os.path.exists(meta_path):
                    os.remove(meta_path)
