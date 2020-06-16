import inspect
import threading

import asdf
from asdf.config import get_config


def test_parameter_agreement():
    """
    This test is intended to help developers remember to add new config
    options everywhere they are needed.  If it proves unhelpful, it should
    be freely modified or removed.
    """
    sig = inspect.signature(asdf.configure)
    for param in sig.parameters.values():
        message = "asdf.configure parameter '{}' default should be NotSet".format(param.name)
        assert param.default is asdf.util.NotSet, message
    configure_keywords = set(sig.parameters.keys())

    sig = inspect.signature(asdf.configure_context)
    for param in sig.parameters.values():
        message = "asdf.configure_context parameter '{}' default should be NotSet".format(param.name)
        assert param.default is asdf.util.NotSet, message
    configure_context_keywords = set(sig.parameters.keys())

    sig = inspect.signature(asdf.config.AsdfConfig)
    for param in sig.parameters.values():
        message = "asdf.config parameter '{}' default should *not* be NotSet".format(param.name)
        assert param.default is not asdf.util.NotSet, message
    config_keywords = set(sig.parameters.keys())

    missing = configure_context_keywords - configure_keywords
    if len(missing) > 0:
        missing_str = ", ".join(list(missing))
        assert len(missing) == 0, "asdf.configure is missing keyword arguments: {}".format(missing_str)

    missing = configure_keywords - configure_context_keywords
    if len(missing) > 0:
        missing_str = ", ".join(list(missing))
        assert len(missing) == 0, "asdf.configure_context is missing keyword arguments: {}".format(missing_str)

    missing = configure_keywords - config_keywords
    if len(missing) > 0:
        missing_str = ", ".join(list(missing))
        assert len(missing) == 0, "AsdfConfig is missing initializer arguments: {}".format(missing_str)

    config = asdf.config.get_config()
    for keyword in configure_keywords:
        assert hasattr(config, keyword), "AsdfConfig is missing accessor for keyword: {}".format(keyword)


def test_configure():
    assert get_config().validate_on_read is True
    asdf.configure()
    assert get_config().validate_on_read is True
    asdf.configure(validate_on_read=False)
    assert get_config().validate_on_read is False
    asdf.configure()
    assert get_config().validate_on_read is False
    asdf.configure(validate_on_read=True)
    assert get_config().validate_on_read is True


def test_configure_threaded():
    asdf.configure(validate_on_read=False)

    thread_value = None
    def worker():
        nonlocal thread_value
        thread_value = get_config().validate_on_read
        asdf.configure(validate_on_read=True)

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()

    assert thread_value is False
    assert get_config().validate_on_read is True


def test_configure_context():
    assert get_config().validate_on_read is True

    with asdf.configure_context(validate_on_read=False):
        assert get_config().validate_on_read is False

    assert get_config().validate_on_read is True


def test_configure_context_nested():
    assert get_config().validate_on_read is True

    with asdf.configure_context(validate_on_read=False):
        with asdf.configure_context(validate_on_read=True):
            with asdf.configure_context(validate_on_read=False):
                assert get_config().validate_on_read is False

    assert get_config().validate_on_read is True


def test_configure_context_threaded():
    assert get_config().validate_on_read is True

    thread_value = None
    def worker():
        nonlocal thread_value
        thread_value = get_config().validate_on_read
        with asdf.configure_context(validate_on_read=False):
            pass

    with asdf.configure_context(validate_on_read=False):
        thread = threading.Thread(target=worker)
        thread.start()
        thread.join()

    assert thread_value is True
    assert get_config().validate_on_read is True
