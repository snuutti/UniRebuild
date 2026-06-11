import glob
import logging
import os.path

from unirebuild.context import PatcherContext
from unirebuild.steps import PatcherStep


class ApplyPatches(PatcherStep):
    def __init__(self, patches_dir: str):
        self.patches_dir = patches_dir

    def get_dependencies(self) -> list[str]:
        return ["git"]

    def execute(self, context: PatcherContext):
        git_path = context.find_executable("git")
        patches = sorted(
            glob.glob(os.path.abspath(os.path.join(self.patches_dir, "*.patch")))
        )
        if patches:
            logging.info("Applying %d patches...", len(patches))
            context.run_cmd(
                [
                    git_path,
                    "-c",
                    "user.name=UniRebuild",
                    "-c",
                    "user.email=auto@mated.null",
                    "am",
                    "--3way",
                    "--ignore-whitespace",
                ]
                + patches,
                cwd=context.workspace_dir,
            )
        else:
            logging.info("No patches found to apply.")
