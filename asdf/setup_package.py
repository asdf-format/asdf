# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-


import os


def get_package_data():  # pragma: no cover
    ASDF_STANDARD_ROOT = os.environ.get("ASDF_STANDARD_ROOT", "asdf-standard")

    schemas = []
    root = os.path.join(ASDF_STANDARD_ROOT, "schemas")
    for node, dirs, files in os.walk(root):
        for fname in files:
            if fname.endswith('.yaml'):
                schemas.append(
                    os.path.relpath(
                        os.path.join(node, fname),
                        root))

    reference_files = []
    root = os.path.join(ASDF_STANDARD_ROOT, "reference_files")
    for node, dirs, files in os.walk(root):
        for fname in files:
            if fname.endswith('.yaml') or fname.endswith('.asdf'):
                reference_files.append(
                    os.path.relpath(
                        os.path.join(node, fname),
                        root))

    return {
        str('asdf.schemas'): schemas,
        str('asdf.reference_files'): reference_files
    }


def requires_2to3():  # pragma: no cover
    return False
