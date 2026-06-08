import logging
import os
import shutil

from unirebuild.context import PatcherContext
from unirebuild.steps import PatcherStep


class SwapFiles(PatcherStep):
    def __init__(self, swap_dict: dict[str, str]):
        self.swap_dict = swap_dict

    def execute(self, context: PatcherContext):
        for src, dst in self.swap_dict.items():
            src_path = os.path.join(context.workspace_dir, src)
            dst_path = os.path.join(context.workspace_dir, dst)

            if os.path.isfile(src_path) and os.path.isfile(dst_path):
                logging.info("Swapping '%s' and '%s'...", src, dst)
                temp_path = dst + ".temp"
                shutil.move(src_path, temp_path)
                shutil.move(dst_path, src_path)
                shutil.move(temp_path, dst_path)
            else:
                logging.warning(
                    "Cannot swap '%s' and '%s' because one or both files do not exist.",
                    src,
                    dst,
                )
