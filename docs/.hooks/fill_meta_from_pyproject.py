"""Mkdocs hook that fills in missing config fields from the project's pyproject.toml.

Currently fills:
- `site_description`
- `site_author`
- `copyright`
- `repo_url`
- `repo_name`
"""

from __future__ import annotations

import logging
import tomllib
from pathlib import Path
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from properdocs.config.defaults import ProperDocsConfig


log = logging.getLogger(f"properdocs.plugins.{__name__}")
PYPROJECT = Path("pyproject.toml")


def on_config(config: ProperDocsConfig) -> ProperDocsConfig | None:
    if not PYPROJECT.exists():
        return None

    pyproj = tomllib.loads(PYPROJECT.read_text())
    if (proj := pyproj.get("project")) is None:
        return None

    updated = []
    authors = proj.get("authors", [])
    urls = proj.get("urls", {})

    if not config.site_description and (desc := proj.get("description")):
        # Get `site_description` from `project.description`
        config.site_description = desc
        updated.append("site_description")
    if not config.site_author and authors:
        # Get `site_author` from `project.authors`
        config.site_author = ", ".join(auth["name"] for auth in authors)
        updated.append("site_author")
    if not config.copyright and config.site_author:
        # Fill `copyright` using `site_author` and the current year
        config.copyright = f"Copyright &copy; {datetime.now().year}, {config.site_author}"
        updated.append("copyright")
    if not config.repo_url and (repo := urls.get("repository")):
        # Get `repo_url` from `project.urls.repository`
        config.repo_url = repo
        updated.append("repo_url")
    if not config.repo_name and config.repo_url:
        # Get `repo_name` from final two segments of `repo_url`
        parts = config.repo_url.split("/")
        config.repo_name = "/".join(parts[-2:])
        updated.append("repo_name")

    if updated:
        fields = ", ".join(updated)
        log.info(f"Filled missing fields from pyproject.toml: {fields}")

    return config
