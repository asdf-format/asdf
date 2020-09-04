from pkg_resources import iter_entry_points
import warnings

from .exceptions import AsdfWarning
from .resource import ResourceMappingProxy
from .extension import ExtensionProxy


RESOURCE_MAPPINGS_GROUP = "asdf.resource_mappings"
EXTENSIONS_GROUP = "asdf.extensions"
LEGACY_EXTENSIONS_GROUP = "asdf_extensions"


def get_resource_mappings():
    return _list_entry_points(RESOURCE_MAPPINGS_GROUP, ResourceMappingProxy)


def get_extensions():
    extensions = _list_entry_points(EXTENSIONS_GROUP, ExtensionProxy)
    legacy_extensions = _list_entry_points(LEGACY_EXTENSIONS_GROUP, ExtensionProxy)

    return extensions + legacy_extensions


def _list_entry_points(group, proxy_class):
    results = []

    entry_points = list(iter_entry_points(group=group))

    # The order of plugins may be significant, since in the case of
    # duplicate functionality the first plugin in the list takes
    # precedence.  It's not clear if entry points are ordered
    # in a consistent way across systems so we explicitly sort
    # by package name.  Plugins from this package are placed
    # at the end so that other packages can override them.
    asdf_entry_points = [e for e in entry_points if e.dist.project_name == "asdf"]
    other_entry_points = sorted([e for e in entry_points if e.dist.project_name != "asdf"], key=lambda e: e.dist.project_name)

    for entry_point in other_entry_points + asdf_entry_points:
        package_name = entry_point.dist.project_name
        package_version = entry_point.dist.version

        def _handle_error(e):
            warnings.warn(
                "{} plugin from package {}=={} failed to load:\n\n"
                "{}: {}".format(
                    group,
                    package_name,
                    package_version,
                    e.__class__.__name__,
                    e,
                ),
                AsdfWarning
            )

        try:
            elements = entry_point.load()()

            if not isinstance(elements, list):
                elements = [elements]

            for element in elements:
                try:
                    results.append(proxy_class(element, package_name=package_name, package_version=package_version))
                except Exception as e:
                    _handle_error(e)
        except Exception as e:
            _handle_error(e)
    return results
