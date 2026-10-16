"""Mkdocs hook that removes doctest flags (e.g. `# doctest: +SKIP`) from code blocks"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from properdocs.config.defaults import ProperDocsConfig
    from properdocs.structure.files import Files
    from properdocs.structure.pages import Page


# Pattern matching any fenced code block with group capturing content between the first and last lines
PYCON_BLOCK_RE = re.compile(r"```.*$\n>>>(.*$\n)+?```", flags=re.MULTILINE)
# Pattern matching doctest flags with format: `# doctest: +\-FLAG`
DOCTEST_RE = re.compile(r"(?<=\s)#[ ]*doctest:([ ]*(\+|-)[A-Z_]+)+(?=\s)")


def on_page_markdown(markdown: str, page: Page, config: ProperDocsConfig, files: Files) -> str:
    def sub_block(m: re.Match) -> str:
        return DOCTEST_RE.sub("", m[0])

    return PYCON_BLOCK_RE.sub(sub_block, markdown)
