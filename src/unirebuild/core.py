import argparse
import logging
import os
import shutil
import sys

import colorlog

from . import steps
from .steps import PatcherStep
from .context import PatcherContext


class UniRebuild:
    def __init__(self, game_name: str, workspace_dir: str, temp_dir: str = "Temp"):
        self.context = PatcherContext(game_name, workspace_dir, temp_dir)
        self.setup_steps = []
        self.rebuild_steps = []
        self.reapply_steps = []

    def add_setup_steps(self, steps: list):
        self.setup_steps.extend(steps)

    def add_rebuild_steps(self, steps: list):
        self.rebuild_steps.extend(steps)

    def add_reapply_steps(self, steps: list):
        self.reapply_steps.extend(steps)

    def execute(self):
        colorlog.basicConfig(
            level=logging.INFO, format="%(log_color)s%(levelname)s: %(message)s"
        )

        sys.stdout.reconfigure(line_buffering=True)

        if not self.rebuild_steps:
            self.rebuild_steps.append(steps.RebuildPatches())

        if not self.reapply_steps:
            self.reapply_steps.append(steps.ReapplyPatches())

        parser = argparse.ArgumentParser(
            description=f"UniRebuild - {self.context.game_name} Patcher"
        )
        subparsers = parser.add_subparsers(dest="command", required=True)

        parser_setup = subparsers.add_parser("setup", help="Set up the workspace")
        parser_rebuild = subparsers.add_parser("rebuild", help="Rebuild all patches")
        parser_reapply = subparsers.add_parser("reapply", help="Reapply all patches")

        for step in self.setup_steps:
            step.register_arguments(parser_setup)

        for step in self.rebuild_steps:
            step.register_arguments(parser_rebuild)

        for step in self.reapply_steps:
            step.register_arguments(parser_reapply)

        args = parser.parse_args()
        self.context.args = args

        self.context.setup_steps = self.setup_steps
        self.context.rebuild_steps = self.rebuild_steps
        self.context.reapply_steps = self.reapply_steps

        if args.command == "setup":
            if os.path.exists(self.context.workspace_dir):
                logging.error(
                    "Workspace directory '%s' already exists. Please remove it before running setup.",
                    self.context.workspace_dir,
                )
                sys.exit(1)

            if os.path.exists(self.context.temp_dir):
                shutil.rmtree(self.context.temp_dir)

            self.run_pipeline(self.setup_steps, True)

            logging.info(
                "Setup completed successfully! You can now open '%s' in Unity.",
                self.context.workspace_dir,
            )
        elif args.command == "rebuild":
            if not os.path.exists(self.context.workspace_dir):
                logging.error(
                    "Workspace directory '%s' does not exist. Please run 'setup' first.",
                    self.context.workspace_dir,
                )
                sys.exit(1)

            self.run_pipeline(self.rebuild_steps, False)
        elif args.command == "reapply":
            if not os.path.exists(self.context.workspace_dir):
                logging.error(
                    "Workspace directory '%s' does not exist. Please run 'setup' first.",
                    self.context.workspace_dir,
                )
                sys.exit(1)

            self.run_pipeline(self.reapply_steps, False)

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
