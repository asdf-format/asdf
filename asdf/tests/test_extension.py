from asdf.extension import BuiltinExtension

from asdf.tests.helpers import assert_extension_correctness

def test_builtin_extension():
    extension = BuiltinExtension()
    assert_extension_correctness(extension)
