import logging
import os.path
import shutil

from unirebuild.context import PatcherContext
from unirebuild.steps import PatcherStep


class CopyOverrides(PatcherStep):
    def __init__(self, overrides_dir: str):
        self.overrides_dir = overrides_dir

    def execute(self, context: PatcherContext):
        if not os.path.exists(self.overrides_dir):
            raise FileNotFoundError(
                f"Overrides directory '{self.overrides_dir}' does not exist."
            )

        logging.info(f"Copying overrides from '{self.overrides_dir}'...")
        shutil.copytree(self.overrides_dir, context.workspace_dir, dirs_exist_ok=True)
