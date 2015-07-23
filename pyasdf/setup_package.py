# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function


from distutils.core import Extension

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
    root = os.path.join(ASDF_STANDARD_ROOT, "reference_files", "0.1.0")
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


def get_extensions():
    root = os.path.dirname(__file__)

    return [
        Extension(str('pyasdf.fastyaml'),
                  [os.path.join(root, str('src'), str('fastyaml.c'))],
                  libraries=[str('yaml')])
    ]


def requires_2to3():  # pragma: no cover
    return False
