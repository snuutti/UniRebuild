import glob
import logging
import os

from unirebuild.context import PatcherContext
from unirebuild.steps import PatcherStep, GitCommit, ApplyPatches


class RebuildPatches(PatcherStep):
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

                start_commit = last_seen_tag
                end_commit = f"{next_tag}^" if next_tag else "HEAD"

                segments.append((start_commit, end_commit, step.patches_dir))

        if not segments:
            logging.warning("No patch segments identified for export.")
            return

        logging.info("Rebuilding patches...")

        for _, _, out_dir in segments:
            abs_out = os.path.abspath(out_dir)
            os.makedirs(abs_out, exist_ok=True)
            for patch in glob.glob(os.path.join(abs_out, "*.patch")):
                os.remove(patch)

        export_flags = [
            "--zero-commit",
            "--no-numbered",
            "--no-stat",
            "--no-signature",
            "--unified=1",
            "--minimal",
            "--ignore-cr-at-eol",
        ]

        def ref_exists(ref: str) -> bool:
            result = context.run_cmd(
                [git_path, "rev-parse", "--verify", ref],
                cwd=context.workspace_dir,
                ignore_errors=True,
            )

            return result == 0

        for start, end, out_dir in segments:
            abs_out_dir = os.path.abspath(out_dir)

            if not ref_exists(start):
                logging.warning(
                    "Start milestone '%s' missing. Skipping segment.", start
                )
                continue

            if ref_exists(end):
                logging.info(
                    "Exporting patches for segment: %s -> %s into '%s'...",
                    start,
                    end,
                    out_dir,
                )

                context.run_cmd(
                    [git_path, "format-patch", f"{start}..{end}", "-o", abs_out_dir]
                    + export_flags,
                    cwd=context.workspace_dir,
                )
            else:
                logging.info(
                    "Milestone '%s' missing, exporting fallback sequence: %s -> HEAD into '%s'...",
                    end,
                    start,
                    out_dir,
                )

                context.run_cmd(
                    [git_path, "format-patch", f"{start}..HEAD", "-o", abs_out_dir]
                    + export_flags,
                    cwd=context.workspace_dir,
                )
                break
