"""Mkdocs hook that injects Sphinx 'std' domain objects into the mkdocstrings intersphinx inventory.

What object types are injected is determined by the `roles` config field.
Supported types are `label` and `doc`.

# Labels
If the `label` role is enabled then a list of labels will be loaded from the file path in `labels`
and exported as `std:label` objects.

Label URLs in the CSV file should be in non-directory_url format, meaning paths should
end with `.html` and directories should end with `/index.html`.
The hook will automatically convert the URLs if `use_directory_urls` is set.

Raises a warning if the URL for a label doesn't exist in the docs.

# Docs
If the `doc` role is enabled then each docs page will be exported as an `std:doc` object.

If `include_redirects` is `true` (the default) and the `mkdocs-redirects` plugin is enabled
then each redirect mapping will be exported as an additional `std:doc` object.

The optional `remap_doc_names` field is a dictionary mapping regex source patterns to regex
substitution templates. These can be used to modify the names of exported `std:doc` objects.
"""

from __future__ import annotations

import csv
import logging
import re
import typing
from collections import defaultdict
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Literal
from urllib.parse import urldefrag

import properdocs.config.config_options as opt
from properdocs.config.base import Config
from properdocs.plugins import BasePlugin
from properdocs.structure.files import File, InclusionLevel

if typing.TYPE_CHECKING:
    from collections.abc import Iterator

    from jinja2 import Environment
    from mkdocs_redirects.plugin import RedirectPlugin
    from mkdocstrings import Inventory, MkdocstringsPlugin
    from properdocs.config.defaults import ProperDocsConfig
    from properdocs.structure.files import Files
    from properdocs.structure.pages import Page

log = logging.getLogger("properdocs.plugins.intersphinx_compat")


def on_config(config: ProperDocsConfig) -> None:
    config.plugins[LegacyLabelsPlugin.KEY] = LegacyLabelsPlugin()


class LegacyLabelsConfig(Config):
    roles: list[Literal["label", "doc"]] = opt.ListOfItems(opt.Choice(["label", "doc"]))  # type: ignore[bad-assignment]
    labels: str | None = opt.Optional(opt.File(exists=True))  # type: ignore[bad-assignment]
    include_redirects: bool = opt.Type(bool, default=True)  # type: ignore[bad-assignment]
    remap_doc_names: dict[str, str] = opt.DictOfItems(opt.Type(str), default={})  # type: ignore[bad-assignment]


class LegacyLabelsPlugin(BasePlugin[LegacyLabelsConfig]):
    KEY = "intersphinx_compat"

    def __init__(self):
        super().__init__()

        self.labels: list[LegacyLabel] = []
        self._anchors: set[str] = set()
        self._redirects: RedirectPlugin | None = None

    def on_config(self, config: ProperDocsConfig) -> None:
        self.load_config(config.extra.get(self.KEY, {}))

        self._redirects = config.plugins.get("redirects")
        if "label" in self.config.roles:
            if self.config.labels:
                self.labels = list(LegacyLabel.load(Path(self.config.labels), config.use_directory_urls))
                log.info(f"Loaded {len(self.labels)} intersphinx labels")
            else:
                log.warning("'label' role enabled but no labels source specified")

    # This event is the latest point before mkdocstrings finalizes the inventory
    def on_env(self, env: Environment, /, *, config: ProperDocsConfig, files: Files) -> Environment | None:
        """Inject 'std' domain objects into the mkdocstrings inventory."""

        mkdocstrings = typing.cast("MkdocstringsPlugin", config.plugins["mkdocstrings"])
        inventory = mkdocstrings.handlers.inventory

        if "doc" in self.config.roles:
            self._register_docs(files, inventory)

        if "label" in self.config.roles:
            self._register_labels(inventory)

    def on_post_page(self, output: str, /, *, page: Page, config: ProperDocsConfig):
        """Collect page anchors to check against imported labels."""
        self._anchors.add(page.url)
        self._anchors.add(f"{page.url}#")
        for anchor in page.present_anchor_ids or []:
            self._anchors.add(f"{page.url}#{anchor}")

    def on_post_build(self, config: ProperDocsConfig) -> None:
        """Verify that all intersphinx label URLs exist."""
        for label in self.labels:
            if label.url not in self._anchors:
                log.warning(f"URL for intersphinx label '{label.anchor}' does not exist: {label.url}")

    def _register_labels(self, inventory: Inventory) -> None:
        for label in self.labels:
            inventory.register(label.anchor, "std", "label", label.url, dispname=label.title)

        log.info(f"Registered {len(self.labels)} 'std:label' objects to intersphinx inventory")

    def _register_docs(self, files: Files, inventory: Inventory) -> None:
        redirects = defaultdict(list)
        initial_len = len(inventory)

        if self._redirects:
            for old, new in self._redirects.redirects.items():
                redirects[new].append(old)

        for file in files:
            if not file.is_documentation_page() or file.inclusion == InclusionLevel.EXCLUDED:
                continue

            names = [
                str(Path(file.dest_uri).with_suffix("")),
                *[str(Path(r).with_suffix("")) for r in redirects.get(file.src_uri, ())],
            ]
            self._register_file(names, file, inventory)

        log.info(f"Registered {len(inventory) - initial_len} 'std:doc' objects to intersphinx inventory")

    def _register_file(self, names: list[str], file: File, inventory: Inventory) -> None:
        dispname = typing.cast("str | None", file.page.title if file.page else None)
        for name in names:
            for pattern, sub in self.config.remap_doc_names.items():
                if m := re.fullmatch(pattern, name):
                    name = m.expand(sub)
            inventory.register(name, "std", "doc", file.url, dispname=dispname)


@dataclass(frozen=True, slots=True)
class LegacyLabel:
    anchor: str
    title: str | None
    url: str

    @classmethod
    def load(cls, path: Path, use_directory_urls: bool) -> Iterator[LegacyLabel]:
        with path.open(newline="") as file:
            reader = csv.DictReader(file, [f.name for f in fields(cls)])
            for row in reader:
                row["url"] = cls._make_url(row["url"], use_directory_urls)
                yield cls(**row)

    @staticmethod
    def _make_url(url: str, use_directory_urls: bool) -> str:
        if use_directory_urls:
            # Convert URL to directory_url format, assuming URL in source ends with .html
            base, frag = urldefrag(url)
            without_file, _, filename = base.rpartition("/")
            # Remove `index.html` from directories
            if filename == "index.html":
                base = without_file

            # Remove `.html` suffix
            url = base.removesuffix(".html")
            # Add trailing slash assuming non-empty URL
            if url:
                url += "/"
            if frag:
                url += f"#{frag}"

        return url
