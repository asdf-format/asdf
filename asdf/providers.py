import warnings

from pkg_resources import iter_entry_points

from asdf.exceptions import AsdfWarning


CONVERTER_PROVIDERS_GROUP = "asdf.converter_providers"


class AsdfConverterProvider:
    """
    Base class for plugins that provide additional `asdf.AsdfConverter`
    subclasses for serializing custom types.

    Implementations must define the `converter_classes` property, which
    returns a list of `asdf.AsdfConverter` subclasses.
    """
    @property
    def converter_classes(self):
        """
        Fetch the list of `asdf.AsdfConverter` subclasses provided by
        this plugin.

        Returns
        -------
        list
            List of `asdf.AsdfConverter` subclasses.
        """
        return []


def get_registered_converter_providers():
    providers = []
    for entry_point in iter_entry_points(group=CONVERTER_PROVIDERS_GROUP):
        provider_class = entry_point.load()
        if not issubclass(provider_class, AsdfConverterProvider):
            full_name = ".".join([provider_class.__module__, provider_class.__qualname__])
            warnings.warn("{} is not a subclass of AsdfConverterProvider.  It will be ignored.".format(full_name),
                          AsdfWarning)
        else:
            providers.append(provider_class())
    return providers


def create_converters(converter_providers):
    converters = []
    for provider in converter_providers:
        for converter_class in provider.converter_classes:
            converters.extend(converter_class.create_converters())
    return converters