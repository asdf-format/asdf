from pkg_resources import iter_entry_points
import warnings
from collections.abc import Mapping

from .exceptions import AsdfWarning
from .extension import AsdfExtension, ExtensionProxy
from .resource import ResourceMappingProxy


RESOURCE_MAPPINGS_GROUP = "asdf.resource_mappings"
EXTENSIONS_GROUP = "asdf.extensions"
LEGACY_EXTENSIONS_GROUP = "asdf_extensions"


def get_resource_mappings():
    return [
        ResourceMappingProxy(mapping, package_name=package_name, package_version=package_version)
        for mapping, package_name, package_version in _iterate_entry_point(RESOURCE_MAPPINGS_GROUP, Mapping)
    ]


def get_extensions():
    extensions = [
        ExtensionProxy(extension, package_name=package_name, package_version=package_version)
        for extension, package_name, package_version in _iterate_entry_point(EXTENSIONS_GROUP, AsdfExtension)
    ]

    legacy_extensions = [
        ExtensionProxy(extension, package_name=package_name, package_version=package_version, legacy=True)
        for extension, package_name, package_version in _iterate_entry_point(LEGACY_EXTENSIONS_GROUP, AsdfExtension)
    ]

    return extensions + legacy_extensions


def _iterate_entry_point(group, element_class):
    for entry_point in iter_entry_points(group=group):
        elements = entry_point.load()()
        if isinstance(elements, element_class):
            elements = [elements]
        package_name = entry_point.dist.project_name
        package_version = entry_point.dist.version
        for element in elements:
            if not isinstance(element, element_class):
                warnings.warn(
                    "{!r} registered with entry point '{}' is not an instance of {}.  It will be ignored.".format(
                        element,
                        group,
                        element_class.__name__
                    ),
                    AsdfWarning
                )
            else:
                yield element, package_name, package_version
