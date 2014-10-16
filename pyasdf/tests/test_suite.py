# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import io
import os

import yaml

from .. import open
from .. import yamlutil


def test_reference_files():
    def test_reference_file(filename):
        with open(filename) as asdf:
            asdf.resolve_and_inline()
            buff = io.BytesIO()
            with asdf.write_to(buff):
                pass

        buff.seek(0)
        my_yaml = yaml.load(buff.getvalue(), Loader=yamlutil.AsdfLoader)

        with io.open(filename[:-4] + "yaml", "rb") as fd:
            ref_yaml_content = fd.read()
        ref_yaml = yaml.load(ref_yaml_content, Loader=yamlutil.AsdfLoader)

        assert my_yaml == ref_yaml

    root = os.path.join(os.path.dirname(__file__), "../reference_files")
    for filename in os.listdir(root):
        if filename.endswith(".asdf"):
            filepath = os.path.join(root, filename)
            if os.path.exists(filepath[:-4] + "yaml"):
                yield test_reference_file, filepath
