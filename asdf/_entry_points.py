import sys
import warnings

from .exceptions import AsdfWarning
from .extension import ExtensionProxy
from .resource import ResourceMappingProxy

# The standard library importlib.metadata returns duplicate entrypoints
# for all python versions up to and including 3.11
# https://github.com/python/importlib_metadata/issues/410#issuecomment-1304258228
# see PR https://github.com/asdf-format/asdf/pull/1260
# see issue https://github.com/asdf-format/asdf/issues/1254
if sys.version_info >= (3, 12):
    from importlib.metadata import entry_points
else:
    from importlib_metadata import entry_points


RESOURCE_MAPPINGS_GROUP = "asdf.resource_mappings"
EXTENSIONS_GROUP = "asdf.extensions"


def get_resource_mappings():
    return _list_entry_points(RESOURCE_MAPPINGS_GROUP, ResourceMappingProxy)


def get_extensions():
    extensions = _list_entry_points(EXTENSIONS_GROUP, ExtensionProxy)
    return extensions


def _list_entry_points(group, proxy_class):
    results = []

    points = entry_points(group=group)

    # The order of plugins may be significant, since in the case of
    # duplicate functionality the first plugin in the list takes
    # precedence.  It's not clear if entry points are ordered
    # in a consistent way across systems so we explicitly sort
    # by package name.  Plugins from this package are placed
    # at the end so that other packages can override them.
    asdf_entry_points = [e for e in points if e.dist.name == "asdf"]
    other_entry_points = sorted((e for e in points if e.dist.name != "asdf"), key=lambda e: e.dist.name)

    for entry_point in other_entry_points + asdf_entry_points:
        package_name = entry_point.dist.name
        package_version = entry_point.dist.version

        def _handle_error(e):
            warnings.warn(
                f"{group} plugin from package {package_name}=={package_version} failed to load:\n\n"
                f"{e.__class__.__name__}: {e}",
                AsdfWarning,
            )

        # Catch errors loading entry points and warn instead of raising
        try:
            with warnings.catch_warnings():
                elements = entry_point.load()()

        except Exception as e:
            _handle_error(e)
            continue

        # Process the elements returned by the entry point
        if not isinstance(elements, list):
            elements = [elements]

        for element in elements:
            # Catch errors instantiating the proxy class and warn instead of raising
            try:
                results.append(proxy_class(element, package_name=package_name, package_version=package_version))
            except Exception as e:
                _handle_error(e)

    return results
