import logging
import os.path
import shutil
from argparse import ArgumentParser

from unirebuild.context import PatcherContext
from unirebuild.steps import PatcherStep


class CopyBundles(PatcherStep):
    def __init__(
        self, bundles_path_arg: str = "bundles", delete_existing: bool = False
    ):
        self.bundles_path_arg = bundles_path_arg
        self.delete_existing = delete_existing

    def register_arguments(self, parser: ArgumentParser):
        parser.add_argument(
            self.bundles_path_arg,
            help="Path to a folder containing the game asset bundles",
        )

    def execute(self, context: PatcherContext):
        bundles_src = getattr(context.args, self.bundles_path_arg)
        bundles_dst = os.path.join(context.get_extracted_path(), "bundles")

        if not os.path.exists(bundles_src):
            raise FileNotFoundError(
                f"Bundles directory '{bundles_src}' does not exist."
            )

        logging.info("Copying bundles from '%s' to '%s'...", bundles_src, bundles_dst)
        shutil.copytree(bundles_src, bundles_dst)

        if not self.delete_existing:
            return

        bundles = set()
        for root, dirs, files in os.walk(bundles_dst):
            for file in files:
                bundles.add(file)

        app_path = os.path.join(context.get_extracted_path(), "app")
        for root, dirs, files in os.walk(app_path):
            for file in files:
                if file in bundles:
                    file_path = os.path.join(root, file)
                    logging.info("Deleting existing bundle '%s'...", file_path)
                    os.remove(file_path)
