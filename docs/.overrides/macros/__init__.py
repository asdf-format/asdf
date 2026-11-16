"""Environment configuration for the mkdocs-macros plugin."""

from . import towncrier


def define_env(env):
    env.macro(towncrier.macro, "towncrier")
