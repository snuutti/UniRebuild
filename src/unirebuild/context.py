import logging
import os
import shutil
import subprocess
import sys


class PatcherContext:
    def __init__(self, game_name: str, workspace_dir: str, temp_dir: str):
        self.game_name = game_name
        self.workspace_dir = os.path.abspath(workspace_dir)
        self.temp_dir = os.path.abspath(temp_dir)
        self.platform = sys.platform
        self.is_ci = "CI" in os.environ
        self.args = None
        self.__executable_cache = {}

    def get_temp_path(self, *paths: str) -> str:
        """Resolves a path within the temporary directory."""
        return os.path.join(self.temp_dir, *paths)

    def find_executable(self, name: str) -> str | None:
        """Finds the path of an executable on the system path or in the current directory."""
        if name in self.__executable_cache:
            return self.__executable_cache[name]

        search_name = name
        if self.platform == "win32":
            search_name += ".exe"

        local_path = os.path.abspath(os.path.join(os.getcwd(), search_name))
        if os.path.isfile(local_path) and os.access(local_path, os.X_OK):
            self.__executable_cache[name] = local_path
            return local_path

        system_path = shutil.which(search_name)
        if system_path:
            abs_system_path = os.path.abspath(system_path)
            self.__executable_cache[name] = abs_system_path
            return abs_system_path

        return None

    def find_unity(self, version: str) -> list[str] | None:
        """Finds the Unity executable for a given version."""
        cache_key = f"unity_{version}"
        if cache_key in self.__executable_cache:
            return self.__executable_cache[cache_key]

        if self.is_ci:
            docker_cmd = [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{os.getcwd()}:{os.getcwd()}",
                "-w",
                os.getcwd(),
                f"unityci/editor:ubuntu-{version}-linux-il2cpp-3",
                "unity-editor",
            ]
            self.__executable_cache[cache_key] = docker_cmd
            return docker_cmd

        unity_path = ""
        if self.platform == "linux":
            unity_path = os.path.expanduser(
                f"~/Unity/Hub/Editor/{version}/Editor/Unity"
            )
        elif self.platform == "darwin":
            unity_path = f"/Applications/Unity/Hub/Editor/{version}/Unity.app/Contents/MacOS/Unity"
        elif self.platform == "win32":
            unity_path = f"C:/Program Files/Unity/Hub/Editor/{version}/Editor/Unity.exe"

        if unity_path and os.path.isfile(unity_path):
            cmd = [unity_path]
            self.__executable_cache[cache_key] = cmd
            return cmd

        return None

    def run_cmd(
        self, cmd: list[str], cwd: str | None = None, ignore_errors: bool = False
    ) -> int:
        """Runs a command and returns the exit code."""
        logging.info("Running command: %s", " ".join(cmd))
        result = subprocess.run(cmd, cwd=cwd)
        if result.returncode != 0 and not ignore_errors:
            raise RuntimeError(f"Command failed with exit code {result.returncode}")

        return result.returncode
