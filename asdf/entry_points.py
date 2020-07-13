from pkg_resources import iter_entry_points
import warnings
from collections.abc import Mapping

from .exceptions import AsdfWarning


RESOURCE_MAPPINGS_GROUP = "asdf.resource_mappings"


def get_resource_mappings():
    return _get_entry_point_elements(RESOURCE_MAPPINGS_GROUP, Mapping)


def _get_entry_point_elements(group, element_class):
    results = []
    for entry_point in iter_entry_points(group=group):
        elements = entry_point.load()()
        for element in elements:
            if not isinstance(element, element_class):
                warnings.warn(
                    "{} is not an instance of {}.  It will be ignored.".format(element, element_class.__name__),
                    AsdfWarning
                )
            else:
                results.append(element)
    return results
