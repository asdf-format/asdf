import datetime
import sys
from pathlib import Path
import functools
import importlib
import inspect
from collections import defaultdict

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib

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
author = configuration["authors"][0]["name"]
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

suppress_warnings = ["config.cache"]
# ignore a few pyyaml docs links since they don't appear to support intersphinx
nitpick_ignore = [
    ("py:class", "yaml.representer.RepresenterError"),
    ("py:class", "yaml.error.YAMLError"),
    # Ignore since they're not part of the public API
    ("py:class", "BlockManager"),
    ("py:class", "BlockKey"),
    ("py:class", "asdf._block.key.Key"),
    ("py:class", "asdf.extension._manager.ValidatorManager"),
    # Needed because sphinx breaks trying to process `asdf.typing.NDArray` for some reason
    ("py:class", "ByteArray1D"),
    ("py:obj", "ByteArray1D"),
    ("py:class", "numpy.uint8"),
    # Needed because `dict_keys` isn't documented
    ("py:class", "dict_keys"),
]

# Add intersphinx mappings
intersphinx_mapping = {
    "numpy": ("https://numpy.org/doc/stable/", None),
    "packaging": ("https://packaging.pypa.io/en/stable/", None),
    "pytest": ("https://docs.pytest.org/en/latest/", None),
    "python": ("https://docs.python.org/3/", None),
    "semantic_version": ("https://python-semanticversion.readthedocs.io/en/latest/", None),
    "stdatamodels": ("https://stdatamodels.readthedocs.io/en/latest/", None),
}


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


intersphinx_mapping.update(subprojects)

extensions = [
    # TODO clean these up, do we need them all?
    "sphinx_inline_tabs",
    "sphinx.ext.coverage",
    "sphinx.ext.mathjax",
    "sphinx.ext.todo",
    "sphinx.ext.viewcode",
    "sphinx.ext.extlinks",

    "sphinx.ext.intersphinx",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "numpydoc",
]


# Don't show summaries of the members in each class along with the
# class' docstring
numpydoc_show_class_members = False
autosummary_ignore_module_all = False
# Class documentation should contain *both* the class docstring and
# the __init__ docstring
autoclass_content = "both"
# autosummary custom templates
templates_path = ["_templates"]


# Skip these items when generating documentation
AUTODOC_SKIP = [
    # Exported elsewhere
    "asdf.tags.core.ExternalArrayReference",
    "asdf.tags.core.IntegerType",
    "asdf.ValidationError",
    "asdf.Stream",

    # Breaks sphinx autodoc
    "asdf.typing.ByteArray1D",
]
# Document inherited methods and attributes for classes in these modules
# For all other classes, only document items defined in the class itself
AUTODOC_SHOW_INHERITED = ["asdf", "asdf.extension"]
# Mapping of item paths to correct public API paths
# Needed because autodoc can't always determine the correct public path for base classes
AUTODOC_REMAP_BASES = {
    "semantic_version.base.Version": "semantic_version.Version",
}

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ["_build"]

# The suffix of source filenames.
source_suffix = ".rst"

# The master toctree document.
master_doc = "index"

# The reST default role (used for this markup: `text`) to use for all
# documents. Set to the "smart" one.
default_role = "obj"

html_theme = "furo"
html_static_path = ["_static"]
html_sidebars = {}
# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
html_favicon = "_static/images/favicon.ico"
html_logo = ""
html_last_updated_fmt = "%d %b %Y"

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

# -- Options for LaTeX output --------------------------------------------------

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [("index", project + ".tex", project + " Documentation", author, "manual")]

latex_logo = "_static/images/logo-light-mode.png"

def autodoc_remap_bases(app, name, obj, _unused, bases):
    """Check if any of the object's base classes are in AUTODOC_REMAP_BASES and remap them.

    Needed because autodoc can't always determine the correct public path for base classes.
    """
    for i, base in enumerate(bases):
        qualname = f"{base.__module__}.{base.__name__}"
        if qualname in AUTODOC_REMAP_BASES:
            module, _, name = AUTODOC_REMAP_BASES[qualname].rpartition(".")
            bases[i].__module__ = module
            bases[i].__name__ = name
            bases[i].__qualname__ = name


def filter_private_symbols(app, domain, node):
    """Ignore broken references to items starting with an underscore.

    These items are assumed to not be public so we don't want them documented anyway.
    """
    target: str = node.get("reftarget", "")
    mod, _, name = target.rpartition(".")

    if name.startswith("_"):
        # Ignore broken references to private symbols
        return True


def filter_inherited(qualname: str, members: list[str], inherited_members: list[str]):
    """Filter list of class members to remove inherited members unless parent module is in SHOW_INHERITED."""
    @functools.cache
    def show_inherited(qualname: str):
        module, _, cls = qualname.rpartition(".")
        return any(module == m for m in AUTODOC_SHOW_INHERITED)

    if show_inherited(qualname):
        return members

    return [m for m in members if m not in inherited_members]


def filter_ignored(qualname: str, members: list[str]):
    """Filter list of module members to remove any present in AUTODOC_SKIP."""
    @functools.cache
    def ignore_map():
        ignore = defaultdict(set)
        for item in AUTODOC_SKIP:
            path, _, name = item.rpartition(".")
            ignore[path].add(name)

        return ignore

    ignored = ignore_map()[qualname]
    return [mem for mem in members if mem not in ignored]

def is_property(modname, qualname, attr):
    """Used by the autosummary class template to pick autoproperty vs autoattribute."""
    obj = importlib.import_module(modname)
    for part in qualname.split("."):
        obj = getattr(obj, part)
    try:
        member = inspect.getattr_static(obj, attr)
    except AttributeError:
        return False
    return isinstance(member, property)

# Helper functions used in autosummary Jinja templates
autosummary_context = {
    "filter_inherited": filter_inherited,
    "filter_ignored": filter_ignored,
    "is_property": is_property,
}


def setup(app):
    app.add_css_file("css/globalnav.css")
    app.connect("warn-missing-reference", filter_private_symbols)
    app.connect("autodoc-process-bases", autodoc_remap_bases)
