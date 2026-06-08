import logging
import zipfile
from argparse import ArgumentParser

from unirebuild.context import PatcherContext
from unirebuild.steps import PatcherStep


class ExtractApp(PatcherStep):
    def __init__(self, app_path_arg: str = "app", target_dir: str = "extracted_app"):
        self.app_path_arg = app_path_arg
        self.target_dir = target_dir

    def register_arguments(self, parser: ArgumentParser):
        parser.add_argument(
            self.app_path_arg, help="Path to the app package file (e.g., .apk, .ipa)"
        )

    def execute(self, context: PatcherContext):
        app_path = getattr(context.args, self.app_path_arg)
        target_path = context.get_temp_path(self.target_dir)

        logging.info("Extracting app '%s' to '%s'...", app_path, target_path)
        with zipfile.ZipFile(app_path, "r") as zip_ref:
            zip_ref.extractall(target_path)
