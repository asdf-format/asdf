import datetime
import sys
from pathlib import Path

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib

from sphinx_asdf.conf import *  # noqa: F403

# The standard library importlib.metadata returns duplicate entrypoints
# for all python versions up to and including 3.11
# https://github.com/python/importlib_metadata/issues/410#issuecomment-1304258228
# see PR https://github.com/asdf-format/asdf/pull/1260
# see issue https://github.com/asdf-format/asdf/issues/1254
if sys.version_info >= (3, 12):
    from importlib.metadata import distribution
else:
    from importlib_metadata import distribution


# Get configuration information from `pyproject.toml`
with open(Path(__file__).parent.parent / "pyproject.toml", "rb") as configuration_file:
    conf = tomllib.load(configuration_file)

configuration = conf["project"]

# -- Project information ------------------------------------------------------
project = configuration["name"]
author = f"{configuration['authors'][0]['name']} <{configuration['authors'][0]['email']}>"
copyright = f"{datetime.datetime.now().year}, {author}"

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

# Docs are hosted as a "subproject" under the main project's domain: https://www.asdf-format.org/projects
# This requires including links to main project (asdf-website) and the other asdf subprojects
# See https://docs.readthedocs.io/en/stable/guides/intersphinx.html#using-intersphinx
subprojects = {
    # main project
    "asdf-website": ("https://www.asdf-format.org/en/latest", None),
    # other subprojects
    "asdf-standard": ("https://www.asdf-format.org/projects/asdf-standard/en/latest/", None),
    "asdf-coordinates-schemas": ("https://www.asdf-format.org/projects/asdf-coordinates-schemas/en/latest/", None),
    "asdf-transform-schemas": ("https://www.asdf-format.org/projects/asdf-transform-schemas/en/latest/", None),
    "asdf-wcs-schemas": ("https://www.asdf-format.org/projects/asdf-wcs-schemas/en/latest/", None),
}

intersphinx_mapping.update(subprojects)  # noqa: F405

extensions += ["sphinx_inline_tabs", "sphinx.ext.intersphinx", "sphinx.ext.extlinks"]  # noqa: F405

html_theme = "furo"
html_static_path = ["_static"]
# Override default settings from sphinx_asdf / sphinx_astropy (incompatible with furo)
html_sidebars = {}
# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
html_favicon = "_static/images/favicon.ico"
html_logo = ""

globalnavlinks = {
    "ASDF Projects": "https://www.asdf-format.org",
    "Tutorials": "https://www.asdf-format.org/en/latest/tutorials/index.html",
    "Community": "https://www.asdf-format.org/en/latest/community/index.html",
}

topbanner = ""
for text, link in globalnavlinks.items():
    topbanner += f"<a href={link}>{text}</a>"

html_theme_options = {
    "light_logo": "images/logo-light-mode.png",
    "dark_logo": "images/logo-dark-mode.png",
    "announcement": topbanner,
}

pygments_style = "monokai"
# NB Dark style pygments is furo-specific at this time
pygments_dark_style = "monokai"
# Render inheritance diagrams in SVG
graphviz_output_format = "svg"

graphviz_dot_args = [
    "-Nfontsize=10",
    "-Nfontname=Helvetica Neue, Helvetica, Arial, sans-serif",
    "-Efontsize=10",
    "-Efontname=Helvetica Neue, Helvetica, Arial, sans-serif",
    "-Gbgcolor=white",
    "-Gfontsize=10",
    "-Gfontname=Helvetica Neue, Helvetica, Arial, sans-serif",
]

# -- Options for LaTeX output --------------------------------------------------

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [("index", project + ".tex", project + " Documentation", author, "manual")]

latex_logo = "_static/images/logo-light-mode.png"


def setup(app):
    app.add_css_file("css/globalnav.css")
