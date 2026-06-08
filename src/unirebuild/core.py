import argparse
import logging
import os
import shutil
import sys

from .steps import PatcherStep
from .context import PatcherContext


class UniRebuild:
    def __init__(self, game_name: str, workspace_dir: str, temp_dir: str = "Temp"):
        self.context = PatcherContext(game_name, workspace_dir, temp_dir)
        self.setup_steps = []
        self.rebuild_steps = []

    def add_setup_steps(self, steps: list):
        self.setup_steps.extend(steps)

    def add_rebuild_steps(self, steps: list):
        self.rebuild_steps.extend(steps)

    def execute(self):
        parser = argparse.ArgumentParser(
            description=f"UniRebuild - {self.context.game_name} Patcher"
        )
        subparsers = parser.add_subparsers(dest="command", required=True)

        parser_setup = subparsers.add_parser("setup", help="Set up the workspace")
        parser_rebuild = subparsers.add_parser("rebuild", help="Rebuild all patches")

        for step in self.setup_steps:
            step.register_arguments(parser_setup)

        for step in self.rebuild_steps:
            step.register_arguments(parser_rebuild)

        args = parser.parse_args()
        self.context.args = args

        if args.command == "setup":
            self.run_pipeline(self.setup_steps, True)
        elif args.command == "rebuild":
            self.run_pipeline(self.rebuild_steps, False)

    def run_pipeline(self, steps: list[PatcherStep], cleanup_temp: bool):
        dependencies = set()
        for step in steps:
            for dependency in step.get_dependencies():
                dependencies.add(dependency)

        missing_tools = []
        for dependency in dependencies:
            if dependency.startswith("unity:"):
                version = dependency.split(":")[1]
                if not self.context.find_unity(version):
                    missing_tools.append(f"Unity {version}")
            else:
                if not self.context.find_executable(dependency):
                    missing_tools.append(dependency)

        if missing_tools:
            logging.error("The following required tools were not found:")
            for tool in missing_tools:
                logging.error(" - %s", tool)

            sys.exit(1)

        if cleanup_temp:
            shutil.rmtree(self.context.temp_dir, ignore_errors=True)
            os.makedirs(self.context.temp_dir, exist_ok=True)

        try:
            for step in steps:
                step.execute(self.context)
        except Exception as e:
            logging.error("Patching failed!")
            logging.exception(e)
            sys.exit(1)
        finally:
            if cleanup_temp:
                logging.info("Cleaning up temporary files...")
                shutil.rmtree(self.context.temp_dir, ignore_errors=True)
                # TODO: move this somewhere else
                # AssetRipper
                shutil.rmtree("temp", ignore_errors=True)
