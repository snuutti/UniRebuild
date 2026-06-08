import logging
import os
import shutil

from unirebuild.context import PatcherContext
from unirebuild.steps import PatcherStep


class CopyGitignore(PatcherStep):
    def __init__(self, source: str):
        self.source = source

    def execute(self, context: PatcherContext):
        logging.info("Copy .gitignore...")
        gitignore_src = os.path.abspath(self.source)
        gitignore_dst = os.path.join(context.workspace_dir, ".gitignore")
        shutil.copyfile(gitignore_src, gitignore_dst)
