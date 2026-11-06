"""Mkdocs hook that reads a list of sphinx-style labels from a file and adds them to the docs' `objects.inv`.

File to load labels from is determined by setting `extra.legacy_labels_path` in the config.
Labels are added to the inventory as `std:label` objects.

Raises a warning if the URL for a label doesn't exist in the docs.
"""

from __future__ import annotations

import csv
import logging
import typing
from dataclasses import dataclass, fields
from pathlib import Path

if typing.TYPE_CHECKING:
    from collections.abc import Iterator

    from jinja2 import Environment
    from mkdocstrings import MkdocstringsPlugin
    from properdocs.config.defaults import ProperDocsConfig
    from properdocs.structure.files import Files
    from properdocs.structure.pages import Page

log = logging.getLogger("properdocs.plugins.export_legacy_labels")

CONFIG_KEY = "legacy_labels_path"
ANCHORS = set()


# This event is the latest point before mkdocstrings finalizes the inventory
def on_env(env: Environment, /, *, config: ProperDocsConfig, files: Files) -> Environment | None:
    """Inject legacy labels into the mkdocstrings inventory as `std:label` objects."""

    mkdocstrings = typing.cast("MkdocstringsPlugin", config.plugins["mkdocstrings"])
    inventory = mkdocstrings.handlers.inventory

    for label in LegacyLabel.load(config):
        inventory.register(label.anchor, "std", "label", label.url, dispname=label.title)


def on_post_page(output: str, /, *, page: Page, config: ProperDocsConfig):
    """Collect page anchors to check against legacy labels."""
    ANCHORS.add(page.url)
    ANCHORS.add(f"{page.url}#")
    for anchor in page.present_anchor_ids or []:
        ANCHORS.add(f"{page.url}#{anchor}")


def on_post_build(config: ProperDocsConfig) -> None:
    """Verify that all legacy label URLs exist."""
    for label in LegacyLabel.load(config):
        if label.url not in ANCHORS:
            log.warning(f"URL for legacy label '{label.anchor}' does not exist: {label.url}")


@dataclass(frozen=True, slots=True)
class LegacyLabel:
    anchor: str
    title: str | None
    url: str

    @classmethod
    def load(cls, config: ProperDocsConfig) -> Iterator[LegacyLabel]:
        path = Path(config.extra[CONFIG_KEY])
        with path.open(newline="") as file:
            reader = csv.DictReader(file, [f.name for f in fields(cls)])
            for row in reader:
                yield cls(**row)
