import glob
import logging
import os

from unirebuild.context import PatcherContext
from unirebuild.steps import PatcherStep, GitCommit, ApplyPatches


class ReapplyPatches(PatcherStep):
    def get_dependencies(self) -> list[str]:
        return ["git"]

    def execute(self, context: PatcherContext):
        git_path = context.find_executable("git")

        segments = []
        last_seen_tag = None

        for index, step in enumerate(context.setup_steps):
            if isinstance(step, GitCommit) and step.tag:
                last_seen_tag = step.tag

            if isinstance(step, ApplyPatches):
                if not last_seen_tag:
                    continue

                next_tag = None
                for lookahead_step in context.setup_steps[index + 1 :]:
                    if isinstance(lookahead_step, GitCommit) and lookahead_step.tag:
                        next_tag = lookahead_step.tag
                        break

                segments.append((last_seen_tag, next_tag, step.patches_dir))

        if not segments:
            logging.warning("No patch segments identified for reapplication.")
            return

        is_dirty = (
            context.run_cmd(
                [git_path, "diff-index", "--quiet", "HEAD", "--"],
                cwd=context.workspace_dir,
                ignore_errors=True,
            )
            != 0
        )

        if is_dirty:
            logging.warning(
                "Workspace contains uncommitted changes. Commit or stash them before reapplying patches."
            )
            return

        logging.info("Reapplying patches...")

        for start_tag, end_tag, patches_dir in segments:
            logging.info(
                "Resetting workspace to tag '%s' for patches in '%s'...",
                start_tag,
                patches_dir,
            )

            context.run_cmd(
                [git_path, "reset", "--hard", start_tag], cwd=context.workspace_dir
            )

            context.run_cmd([git_path, "clean", "-fd"], cwd=context.workspace_dir)

            patches = sorted(
                glob.glob(os.path.abspath(os.path.join(patches_dir, "*.patch")))
            )
            if patches:
                logging.info("Applying %d patches...", len(patches))
                context.run_cmd(
                    [
                        git_path,
                        "-c",
                        "user.name=UniRebuild",
                        "-c",
                        "user.email=auto@mated.null",
                        "am",
                        "--3way",
                        "--ignore-whitespace",
                    ]
                    + patches,
                    cwd=context.workspace_dir,
                )
            else:
                logging.info("No patches found to apply in '%s'.", patches_dir)

            if end_tag:
                logging.info("Updating milestone tag '%s' to current HEAD...", end_tag)
                context.run_cmd(
                    [git_path, "tag", "-f", end_tag], cwd=context.workspace_dir
                )
