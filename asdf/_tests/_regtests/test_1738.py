import asdf


def test_info_on_non_tagged_asdf_traverse_object():
    """
    Calling info with a tree containing an object that implements
    __asdf_traverse__ but does not have a _tag results in an
    error

    https://github.com/asdf-format/asdf/issues/1738
    """

    class MyContainer:
        def __init__(self, data):
            self.data = data

        def __asdf_traverse__(self):
            return self.data

    c = MyContainer([1, 2, 3])
    af = asdf.AsdfFile()
    af["c"] = c

    # info should not error out
    af.info()

    # and search should work with the container
    assert af.search(type_=int).paths == ["root['c'][0]", "root['c'][1]", "root['c'][2]"]

    # this should work even if _tag exists (and is not a tag)
    c._tag = {}
    af.info()
    assert af.search(type_=int).paths == ["root['c'][0]", "root['c'][1]", "root['c'][2]"]
    c._tag = "a"
    af.info()
    assert af.search(type_=int).paths == ["root['c'][0]", "root['c'][1]", "root['c'][2]"]
