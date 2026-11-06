"""Macro that generates links to external projects.

# Configuration
Add an `external_links` key under `extra` in `properdocs.yml`.
For each external project, add a new key/value pair, e.g.:

```yaml
extra:
  external_links:
    myproj: https://myproject.org/latest/
    other_project: https://other-project.com/latest/
```

This will register new macros called `myproj` and `other_project`.

## Path Suffixes
You can specify a path suffix or file extension to be added to the end of generated URLs:

```yaml
extra:
  external_links:
    myproj:
      url: https://myproject.org/latest/
      suffix: ".html"
```

## Link Validation
If `check` is `true` then the macro will emit a warning if a generated link can't be resolved:

```yaml
extra:
  external_links:
    check: true
    myproj: https://myproject.org/latest/
```

# Usage

Generated macros are invoked as `<project>('<title>', '<path>')`.
With the configuration described above, a macro invocation such as:

```md
This is a {{ myproj('link', 'path/to#anchor') }}.
```

Will be transformed into a standard markdown link:

```md
This is a [link](https://myproject.org/latest/path/to.html#anchor)
```

Any path suffix such as `.html` can be omitted (as long as `suffix` is set in the project config).
HTML fragments can be used at the end of the path as normal.
HTML query parameters are not supported.

"""

from __future__ import annotations

import logging
import textwrap
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import TYPE_CHECKING, Any
from urllib.parse import urldefrag, urljoin

import requests

if TYPE_CHECKING:
    from mkdocs_macros.plugin import MacrosPlugin

log = logging.getLogger("properdocs.plugins.towncrier")


def register(env: MacrosPlugin):
    """Parses the `external_links` configuration and registers a new macro definition
    for each entry in the configuration.
    """
    cfg = env.variables["external_links"]
    check = cfg.pop("check", False)
    link_classes = cfg.pop("link_classes", ["external"])

    for key, cfg in env.variables["external_links"].items():
        if isinstance(cfg, str):
            url = cfg
            suffix = None
        else:
            url = cfg["url"]
            suffix = cfg.get("suffix")

        if not url.endswith("/"):
            # URL without a trailing slash produces unintuitive behavior with `urljoin`
            url += "/"

        proj = ExtProject(key, url, check, link_classes, suffix, env)
        env.macro(proj.link, key)


@dataclass
class ExtProject:
    key: str
    base: str
    check: bool
    link_classes: list[str]
    suffix: str | None
    env: MacrosPlugin

    def link(self, title: str, path: str) -> str:
        url = urljoin(self.base, path)
        if self.suffix:
            url, frag = urldefrag(url)
            url += self.suffix
            if frag:
                url = f"{url}#{frag}"

        if self.check:
            try:
                _check_link(url)
            except Exception as error:
                indent = "    "
                page = self.env.page.file.src_uri
                source = f"{self.key}('{title}', '{path}')"
                log.warning(
                    f"{page}: failed to resolve external link\n"
                    f"{textwrap.indent(url, indent)}\n"
                    f"Error:\n{textwrap.indent(str(error), indent)}\n"
                    f"Source:\n{textwrap.indent(source, indent)}\n"
                )

        if self.link_classes:
            classes = "".join([f".{cls}" for cls in self.link_classes])
            attrs = f"{{ {classes} }}"
        else:
            attrs = ""

        return f"[{title}]({url}){attrs}"


def _check_link(url: str) -> None:
    _, anchor = urldefrag(url)

    method = "GET" if anchor else "HEAD"
    resp = requests.request(method, url, timeout=1, stream=True)
    resp.raise_for_status()

    if not anchor:
        return

    finder = _AnchorFinder(anchor)
    for chunk in resp.iter_content(chunk_size=4096, decode_unicode=True):
        if finder.check(chunk):
            return

    raise AnchorError(anchor)


class AnchorError(Exception):
    def __init__(self, anchor: str):
        super().__init__(f"Anchor not found: {anchor}")


class _AnchorFinder(HTMLParser):
    def __init__(self, anchor: str):
        super().__init__()

        self.anchor = anchor
        self.found = False

    def check(self, chunk: str) -> bool:
        self.feed(chunk)
        return self.found

    def handle_starttag(self, tag: Any, attrs: Any) -> None:
        for key, value in attrs:
            if key in {"id", "name"} and value == self.anchor:
                self.found = True
                break
