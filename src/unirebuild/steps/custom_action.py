import logging
from typing import Callable

from unirebuild.context import PatcherContext
from unirebuild.steps import PatcherStep


class CustomAction(PatcherStep):
    """A patcher step for executing a custom user-defined action."""

    def __init__(self, action_func: Callable[[PatcherContext], None]):
        self.action_func = action_func

    def execute(self, context: PatcherContext):
        logging.info("Running custom action '%s'...", self.action_func.__name__)
        self.action_func(context)
