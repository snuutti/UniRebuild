import logging

from unirebuild.context import PatcherContext
from unirebuild.steps import PatcherStep


class GitInit(PatcherStep):
    def get_dependencies(self) -> list[str]:
        return ["git"]

    def execute(self, context: PatcherContext):
        git_path = context.find_executable("git")
        logging.info("Initializing Git repository...")
        context.run_cmd([git_path, "init"], cwd=context.workspace_dir)
        context.run_cmd(
            [git_path, "config", "core.autocrlf", "false"], cwd=context.workspace_dir
        )
        context.run_cmd([git_path, "add", "."], cwd=context.workspace_dir)
        context.run_cmd(
            [
                git_path,
                "commit",
                "-m",
                "Initial Commit",
                "--author",
                "UniRebuild <auto@mated.null>",
            ],
            cwd=context.workspace_dir,
        )
        context.run_cmd([git_path, "tag", "raw-project"], cwd=context.workspace_dir)
