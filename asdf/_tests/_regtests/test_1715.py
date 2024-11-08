import asdf


def test_id_in_tree_breaks_ref(tmp_path):
    """
    a dict containing id will break contained References

    https://github.com/asdf-format/asdf/issues/1715
    """
    external_fn = tmp_path / "external.asdf"

    external_tree = {"thing": 42}

    asdf.AsdfFile(external_tree).write_to(external_fn)

    main_fn = tmp_path / "main.asdf"

    af = asdf.AsdfFile({})
    af["id"] = "bogus"
    af["myref"] = {"$ref": "external.asdf#/thing"}
    af.write_to(main_fn)

    with asdf.open(main_fn) as af:
        af.resolve_references()
        assert af["myref"] == 42
