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


def on_page_markdown(markdown: str, page: Page, config: ProperDocsConfig, files: Files) -> str | None:
    src_uri = config.extra.get("changelog", {}).get("src_uri", None)

    if src_uri is None or page.file.src_uri != src_uri:
        return None

    if (cmd := shutil.which("towncrier")) is None:
        log.warning("'towncrier' command not found, skipping changelog update")
        return None

    py = tomllib.loads(Path("pyproject.toml").read_text())
    cfg = py["tool"]["towncrier"]
    changes_dir = Path(cfg["directory"])
    start_string = cfg["start_string"]

    if not any(changes_dir.iterdir()):
        log.info(f"Changelog already up to date: {src_uri}")
        return None

    res = subprocess.run([cmd, "build", "--draft"], check=True, capture_output=True, text=True)
    text, count = re.subn(start_string, res.stdout, markdown, count=1)
    if count:
        log.info(f"Changelog updated: {src_uri}")
    else:
        log.info(f"Changelog already up to date: {src_uri}")

    return text
