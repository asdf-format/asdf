import warnings

# The standard library importlib.metadata returns duplicate entrypoints
# for all python versions up to and including 3.11
# https://github.com/python/importlib_metadata/issues/410#issuecomment-1304258228
# see PR https://github.com/asdf-format/asdf/pull/1260
# see issue https://github.com/asdf-format/asdf/issues/1254
from importlib_metadata import entry_points

from .exceptions import AsdfDeprecationWarning, AsdfWarning
from .extension import ExtensionProxy
from .resource import ResourceMappingProxy

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
                f"{group} plugin from package {package_name}=={package_version} failed to load:\n\n"  # noqa: B023
                f"{e.__class__.__name__}: {e}",
                AsdfWarning,
            )

        # Catch errors loading entry points and warn instead of raising
        try:
            with warnings.catch_warnings():
                if entry_point.group == LEGACY_EXTENSIONS_GROUP:
                    if entry_point.name in ("astropy", "astropy-asdf"):
                        # Filter out the legacy `CustomType` deprecation warnings from the
                        # deprecated astropy.io.misc.asdf
                        # Testing will turn these into errors
                        # Most of the astropy.io.misc.asdf deprecation warnings fall under this category
                        warnings.filterwarnings(
                            "ignore",
                            category=AsdfDeprecationWarning,
                            message=r".*from astropy.io.misc.asdf.* subclasses the deprecated CustomType .*",
                        )
                        warnings.filterwarnings(
                            "ignore",
                            category=AsdfDeprecationWarning,
                            message="asdf.types is deprecated",
                        )
                        warnings.filterwarnings(
                            "ignore",
                            category=AsdfDeprecationWarning,
                            message="AsdfExtension is deprecated",
                        )
                        warnings.filterwarnings(
                            "ignore",
                            category=AsdfDeprecationWarning,
                            message="BuiltinExtension is deprecated",
                        )
                        warnings.filterwarnings(
                            "ignore",
                            category=AsdfDeprecationWarning,
                            message="asdf.tests.helpers is deprecated",
                        )
                    elif entry_point.name != "builtin":
                        warnings.warn(
                            f"{package_name} uses the deprecated entry point {LEGACY_EXTENSIONS_GROUP}. "
                            f"Please use the new extension api and entry point {EXTENSIONS_GROUP}: "
                            "https://asdf.readthedocs.io/en/stable/asdf/extending/extensions.html",
                            AsdfDeprecationWarning,
                        )
                elements = entry_point.load()()

        except Exception as e:  # noqa: BLE001
            _handle_error(e)
            continue

        # Process the elements returned by the entry point
        if not isinstance(elements, list):
            elements = [elements]

        for element in elements:
            # Catch errors instantiating the proxy class and warn instead of raising
            try:
                results.append(proxy_class(element, package_name=package_name, package_version=package_version))
            except Exception as e:  # noqa: BLE001
                _handle_error(e)

    return results
