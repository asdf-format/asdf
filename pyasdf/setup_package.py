# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import os


def get_package_data():  # pragma: no cover
    schemas = []
    root = "asdf-standard/schemas"
    for node, dirs, files in os.walk(root):
        for fname in files:
            if fname.endswith('.yaml'):
                schemas.append(
                    os.path.relpath(
                        os.path.join(node, fname),
                        root))

    reference_files = []
    root = "asdf-standard/reference_files/0.1.0"
    for node, dirs, files in os.walk(root):
        for fname in files:
            if fname.endswith('.yaml') or fname.endswith('.asdf'):
                reference_files.append(
                    os.path.relpath(
                        os.path.join(node, fname),
                        root))

    return {
        str('pyasdf.schemas'): schemas,
        str('pyasdf.reference_files'): reference_files
    }


def requires_2to3():  # pragma: no cover
    return False
