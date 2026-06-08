import logging

from unirebuild.context import PatcherContext
from unirebuild.steps import PatcherStep


class GitCommit(PatcherStep):
    def __init__(self, message: str, tag: str | None = None):
        self.message = message
        self.tag = tag

    def get_dependencies(self) -> list[str]:
        return ["git"]

    def execute(self, context: PatcherContext):
        git_path = context.find_executable("git")
        logging.info("Committing changes...")
        context.run_cmd([git_path, "add", "."], cwd=context.workspace_dir)
        context.run_cmd(
            [
                git_path,
                "-c",
                "user.name=UniRebuild",
                "-c",
                "user.email=auto@mated.null",
                "commit",
                "-m",
                self.message,
                "--author",
                "UniRebuild <auto@mated.null>",
            ],
            cwd=context.workspace_dir,
        )

        if self.tag:
            context.run_cmd([git_path, "tag", self.tag], cwd=context.workspace_dir)
