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
            full_path = os.path.join(context.workspace_dir, asset)
            if not os.path.exists(full_path):
                raise FileNotFoundError(
                    f"Asset '{asset}' not found at path '{full_path}'."
                )

            logging.info("Deleting asset: %s", asset)

            if os.path.isdir(full_path):
                shutil.rmtree(full_path)
            else:
                os.remove(full_path)

            meta_path = full_path + ".meta"
            if os.path.exists(meta_path):
                os.remove(meta_path)
