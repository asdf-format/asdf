"""Environment configuration for the mkdocs-macros plugin."""

from . import extlink, towncrier


def define_env(env):
    env.macro(towncrier.macro, "towncrier")
    extlink.register(env)
