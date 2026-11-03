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

import logging
from dataclasses import dataclass
from urllib.parse import urldefrag, urljoin

import requests

log = logging.getLogger("properdocs.plugins.towncrier")


def register(env):
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

        proj = ExtProject(url, check, link_classes, suffix)
        env.macro(proj.link, key)


@dataclass
class ExtProject:
    base: str
    check: bool
    link_classes: list[str]
    suffix: str | None

    def link(self, title: str, path: str) -> str:
        url = urljoin(self.base, path)
        if self.suffix:
            url, frag = urldefrag(url)
            url += self.suffix
            if frag:
                url = f"{url}#{frag}"

        if self.check:
            try:
                requests.get(url, timeout=1).raise_for_status()
            except requests.RequestException as error:
                log.warning(f"Failed to resolve external link: {url}\n{error}")

        if self.link_classes:
            classes = "".join([f".{cls}" for cls in self.link_classes])
            attrs = f"{{ {classes} }}"
        else:
            attrs = ""

        return f"[{title}]({url}){attrs}"
