from argparse import ArgumentParser

from unirebuild.context import PatcherContext


class PatcherStep:
    """Base class for all patcher steps."""

    def register_arguments(self, parser: ArgumentParser):
        """Registers command-line arguments for this step."""
        pass

    def get_dependencies(self) -> list[str]:
        """Returns a list of tool dependencies required by this step."""
        return []

    def execute(self, context: PatcherContext):
        """Executes the step using the provided context."""
        raise NotImplementedError()
