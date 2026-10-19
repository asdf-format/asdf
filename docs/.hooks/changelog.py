"""Mkdocs hook that updates a changelog using towncrier.

Expects configuration under `extra` in `properdocs.yml`:

```yaml
extra:
  changelog:
    src_uri: <changelog path>
```
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import re
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from properdocs.config.defaults import ProperDocsConfig
    from properdocs.structure.files import Files
    from properdocs.structure.pages import Page


log = logging.getLogger(f"properdocs.plugins.{__name__}")

_NO_CHANGE_RE = re.compile(r"^No significant changes.\s+\Z", flags=re.MULTILINE)

def on_page_markdown(markdown: str, page: Page, config: ProperDocsConfig, files: Files) -> str | None:
    src_uri = config.extra.get("changelog", {}).get("src_uri", None)

    if src_uri is None or page.file.src_uri != src_uri:
        return None

    if (cmd := shutil.which("towncrier")) is None:
        log.warning("'towncrier' command not found, skipping changelog update")
        return None

    py = tomllib.loads(Path("pyproject.toml").read_text())
    cfg = py["tool"]["towncrier"]
    start_string = cfg["start_string"]

    res = subprocess.run([cmd, "build", "--draft"], check=True, capture_output=True, text=True)
    out = res.stdout

    if _NO_CHANGE_RE.search(out):
        log.info(f"Changelog already up to date: {src_uri}")
        return None

    text, count = re.subn(start_string, out, markdown, count=1)
    if count:
        log.info(f"Changelog updated: {src_uri}")
    else:
        log.warning(f"No towncrier marker found in changelog file {src_uri}, skipping update")

    return text
