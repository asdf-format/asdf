from pathlib import Path

import toml
from pkg_resources import get_distribution
from sphinx_asdf.conf import *  # noqa

# Get configuration information from `pyproject.toml`
with open(Path(__file__).parent.parent / "pyproject.toml") as configuration_file:
    conf = toml.load(configuration_file)
configuration = conf["project"]

# -- Project information ------------------------------------------------------
project = configuration["name"]
author = f"{configuration['authors'][0]['name']} <{configuration['authors'][0]['email']}>"
copyright = f"{datetime.datetime.now().year}, {configuration['authors'][0]}"

release = get_distribution(configuration["name"]).version
# for example take major/minor
version = ".".join(release.split(".")[:2])

# -- Options for HTML output ---------------------------------------------------
html_static_path = ["_static"]
html_title = "{0} v{1}".format(project, release)

# Output file base name for HTML help builder.
htmlhelp_basename = project + "doc"

# -- Options for LaTeX output --------------------------------------------------
latex_documents = [("index", project + ".tex", project + " Documentation", author, "manual")]

# -- Options for manual page output --------------------------------------------
man_pages = [("index", project.lower(), project + " Documentation", [author], 1)]
