"""Macro that generates pending changelog updates using towncrier.

# Usage

```md
# Changelog

{{ towncrier() }}

## 1.0.0
<!-- Existing changelog entries -->
```

Example output:

```md
# Changelog

## 1.0.0.dev109+g000107ac9
### Bugfix
- Fixed the thing

## 1.0.0
<!-- Existing changelog entries -->
```
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess

log = logging.getLogger("properdocs.plugins.towncrier")

_NO_CHANGE_RE = re.compile(r"^No significant changes.\s+\Z", flags=re.MULTILINE)


def macro() -> str:
    if (cmd := shutil.which("towncrier")) is None:
        log.warning("'towncrier' command not found, skipping changelog update")
        return ""

    res = subprocess.run([cmd, "build", "--draft"], check=True, capture_output=True, text=True)  # noqa: S603
    out = res.stdout

    if _NO_CHANGE_RE.search(out):
        log.info("Changelog already up to date")
        return ""

    log.info("Changelog updated")
    return out
