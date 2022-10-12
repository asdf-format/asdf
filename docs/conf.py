from pathlib import Path

import tomli
from sphinx_asdf.conf import *  # noqa: F403

try:
    from importlib.metadata import distribution
except ImportError:
    from importlib_metadata import distribution


# Get configuration information from `pyproject.toml`
with open(Path(__file__).parent.parent / "pyproject.toml", "rb") as configuration_file:
    conf = tomli.load(configuration_file)
configuration = conf["project"]

# -- Project information ------------------------------------------------------
project = configuration["name"]
author = f"{configuration['authors'][0]['name']} <{configuration['authors'][0]['email']}>"
copyright = f"{datetime.datetime.now().year}, {configuration['authors'][0]['name']}"

release = distribution(configuration["name"]).version
# for example take major/minor
version = ".".join(release.split(".")[:2])

# -- Options for HTML output ---------------------------------------------------
html_title = f"{project} v{release}"

# Output file base name for HTML help builder.
htmlhelp_basename = project + "doc"

# -- Options for LaTeX output --------------------------------------------------
latex_documents = [("index", project + ".tex", project + " Documentation", author, "manual")]

# -- Options for manual page output --------------------------------------------
man_pages = [("index", project.lower(), project + " Documentation", [author], 1)]

# Enable nitpicky mode - which ensures that all references in the docs
# resolve.

nitpicky = True

# Add intersphinx mappings
intersphinx_mapping["semantic_version"] = ("https://python-semanticversion.readthedocs.io/en/latest/", None)
intersphinx_mapping["jsonschema"] = ("https://python-jsonschema.readthedocs.io/en/stable/", None)
