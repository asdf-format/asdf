import sys
from pathlib import Path

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib

# The standard library importlib.metadata returns duplicate entrypoints
# for all python versions up to and including 3.11
# https://github.com/python/importlib_metadata/issues/410#issuecomment-1304258228
# see PR https://github.com/asdf-format/asdf/pull/1260
# see issue https://github.com/asdf-format/asdf/issues/1254
from importlib_metadata import distribution
from sphinx_asdf.conf import *  # noqa: F403

# Get configuration information from `pyproject.toml`
with open(Path(__file__).parent.parent / "pyproject.toml", "rb") as configuration_file:
    conf = tomllib.load(configuration_file)

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

# ignore a few pyyaml docs links since they don't appear to support intersphinx
nitpick_ignore = [
    ("py:class", "yaml.representer.RepresenterError"),
    ("py:class", "yaml.error.YAMLError"),
]

# Add intersphinx mappings
intersphinx_mapping["semantic_version"] = ("https://python-semanticversion.readthedocs.io/en/latest/", None)
intersphinx_mapping["jsonschema"] = ("https://python-jsonschema.readthedocs.io/en/stable/", None)
intersphinx_mapping["stdatamodels"] = ("https://stdatamodels.readthedocs.io/en/latest/", None)
intersphinx_mapping["pytest"] = ("https://docs.pytest.org/en/latest/", None)

extensions += ["sphinx_inline_tabs"]
