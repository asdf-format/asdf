from asdf.resource import JsonschemaResourceMapping


def get_extensions():
    """
    Get the extension instances for the core extensions.  This method is registered with the
    asdf.extensions entry point.

    Returns
    -------
    list of asdf.extension.Extension
    """
    from . import _extensions

    return _extensions.EXTENSIONS


def get_json_schema_resource_mappings():
    return [
        JsonschemaResourceMapping(),
    ]
