import pytest

@pytest.fixture(autouse=True)
def _docdir(request):
    """
    Make sure that doctests run in a temporary directory so that any files that
    are created as part of the test get removed automatically.
    """
    # Trigger ONLY for doctestplus.
    try:
        doctest_plugin = request.config.pluginmanager.getplugin("doctestplus")
        if isinstance(request.node.parent, doctest_plugin._doctest_textfile_item_cls):
            tmpdir = request.getfixturevalue('tmpdir')
            with tmpdir.as_cwd():
                yield
        else:
            yield
    # Handle case where doctestplus is not available
    except AttributeError:
        yield
