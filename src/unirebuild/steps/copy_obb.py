import logging
import os.path
import shutil
import zipfile
from argparse import ArgumentParser

from unirebuild.context import PatcherContext
from unirebuild.steps import PatcherStep


class CopyObb(PatcherStep):
    def __init__(self, obb_path_arg: str = "obb"):
        self.obb_path_arg = obb_path_arg

    def register_arguments(self, parser: ArgumentParser):
        parser.add_argument(self.obb_path_arg, help="Path to the OBB file")

    def execute(self, context: PatcherContext):
        obb_src = getattr(context.args, self.obb_path_arg)
        app_target_path = os.path.join(context.get_extracted_path(), "app")

        if not os.path.exists(obb_src):
            raise FileNotFoundError(f"OBB file '{obb_src}' does not exist.")

        if not os.path.exists(app_target_path):
            raise FileNotFoundError(
                "App target path does not exist. The app must be extracted before copying the OBB file."
            )

        if os.path.isdir(obb_src):
            logging.info(
                "Copying OBB directory from '%s' to '%s'...", obb_src, app_target_path
            )
            shutil.copytree(obb_src, app_target_path)
        else:
            logging.info(
                "Extracting OBB file '%s' to '%s'...", obb_src, app_target_path
            )
            with zipfile.ZipFile(obb_src, "r") as zip_ref:
                zip_ref.extractall(app_target_path)
