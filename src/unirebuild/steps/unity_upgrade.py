import logging
import os

from unirebuild.context import PatcherContext
from unirebuild.steps import PatcherStep


class UnityUpgrade(PatcherStep):
    def __init__(self, unity_version: str, execute_method: str):
        self.unity_version = unity_version
        self.execute_method = execute_method

    def get_dependencies(self) -> list[str]:
        return [f"unity:{self.unity_version}"]

    def execute(self, context: PatcherContext):
        unity_cmd = context.find_unity(self.unity_version)
        unity_log = context.get_temp_path("unity_upgrade.log")
        unity_args = [
            "-quit",
            "-batchmode",
            "-nographics",
            "-projectPath",
            context.workspace_dir,
            "-executeMethod",
            self.execute_method,
        ]

        if "CI" in os.environ:
            unity_log = "/dev/stdout"
            unity_args += [
                "-serial",
                os.environ.get("UNITY_SERIAL"),
                "-username",
                os.environ.get("UNITY_EMAIL"),
                "-password",
                os.environ.get("UNITY_PASSWORD"),
            ]

        unity_args += ["-logFile", unity_log]
        logging.info(
            "Running Unity Editor %s, this may take several minutes...",
            self.unity_version,
        )
        context.run_cmd(unity_cmd + unity_args)
