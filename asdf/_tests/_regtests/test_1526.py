import os

import numpy as np

import asdf


def test_rewrite_file_with_unaccessed_external_blocks_fails(tmp_path):
    """
    Rewriting a file with external blocks fails if arrays are not first accessed

    https://github.com/asdf-format/asdf/issues/1526
    """
    arrs = [np.arange(3) + i for i in range(3)]
    af = asdf.AsdfFile({"arrs": arrs})
    [af.set_array_storage(a, "external") for a in arrs]

    dns = []
    for i in range(2):
        dn = tmp_path / f"d{i}"
        if not os.path.exists(dn):
            os.makedirs(dn)
        dns.append(dn)
    fns = [dn / "test.asdf" for dn in dns]

    # write to d0
    af.write_to(fns[0])

    with asdf.open(fns[0]) as af2:
        af2["arrs"][0] = 42
        # write to d1
        af2.write_to(fns[1])

    assert len(os.listdir(dns[0])) == 4
    assert len(os.listdir(dns[1])) == 3
