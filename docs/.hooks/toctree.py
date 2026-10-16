"""Mkdocs hook that implements a version of the Sphinx toctree directive.

To use, add a `[toctree <path>]` directive to a markdown file, where `<path>`
is the relative path to another markdown file from the current file.
This hook will then insert the table of contents for that page as a bulleted list.

The directive also supports an optional `depth=<number>` argument which limits the
maximum header depth that will be extracted from the target page.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import partial
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from markdown import Markdown  # pyrefly: ignore [untyped-import]
from properdocs.structure.toc import get_toc

if TYPE_CHECKING:
    from collections.abc import Iterable

    from properdocs.config.defaults import ProperDocsConfig
    from properdocs.structure.files import Files
    from properdocs.structure.pages import Page
    from properdocs.structure.toc import AnchorLink


def on_page_markdown(markdown: str, page: Page, config: ProperDocsConfig, files: Files) -> str:
    return TOC_RE.sub(partial(_sub_toctree, page, files), markdown)


# Regex matching the toctree directive with all arguments in one group
TOC_RE = re.compile(r"\[\s*toctree(\s[^]]+)?\]")


def _sub_toctree(page: Page, files: Files, m: re.Match) -> str:
    args = TocTreeArgs.parse(m[1])

    # Get "absolute" path relative to docs root
    root = PurePosixPath(page.file.src_uri).parent
    path = str(root / args.relpath)

    if (file := files.get_file_from_path(path)) is None:
        msg = f"File {path} not found"
        raise RuntimeError(msg)

    # Have to parse the file this way instead of using `page.render()`
    # Using the default list of markdown extensions creates duplicate header permalinks
    md = Markdown(extensions=["toc", "fenced_code", "attr_list"])
    # Call to `convert` required to populate TOC
    _ = md.convert(file.content_string)
    toc = get_toc(getattr(md, "toc_tokens", []))

    def render_links(links: Iterable[AnchorLink], depth: int | None):
        """Recursively render anchors in `links` and their children up to the given `depth`."""
        if depth is not None:
            if depth <= 0:
                return

            depth -= 1

        for link in links:
            indent = "    " * (link.level - 1)
            bullet = f"- [{link.title}]({args.relpath}{link.url})\n"
            yield indent + bullet
            yield from render_links(link.children, depth)

    return "".join(render_links(toc, args.depth))


@dataclass(frozen=True, slots=True)
class TocTreeArgs:
    relpath: str
    depth: int | None

    @classmethod
    def parse(cls, raw_args: str) -> TocTreeArgs:
        """Expected format: `<path> <key>==<value>`"""
        args = raw_args.strip().split()
        if not args:
            msg = "toctree directive missing required <page> argument"
            raise RuntimeError(msg)

        relpath = args.pop(0)
        kwargs = {}
        for arg in args:
            k, _, v = arg.partition("=")
            if not v:
                msg = f"Expected key=value argument pairs, got '{arg}'"
                raise RuntimeError(msg)

            kwargs[k.strip()] = v.strip()

        depth: int | None = None

        if "depth" in kwargs:
            depth = int(kwargs["depth"])

        return cls(relpath, depth)
