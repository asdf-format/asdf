# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-


import io

from ... import AsdfFile
from .. import list_tags

def _get_tags(display_classes):
    iostream = io.StringIO()
    list_tags(display_classes=display_classes, iostream=iostream)
    iostream.seek(0)
    return [line.strip() for line in iostream.readlines()]

def _class_to_string(_class):
    return "{}.{}".format(_class.__module__, _class.__name__)

def test_list_schemas():
    obs_tags = _get_tags(False)

    af = AsdfFile()
    exp_tags = sorted(af._extensions._type_index._type_by_tag.keys())

    for exp, obs in zip(exp_tags, obs_tags):
        assert exp == obs

def test_list_schemas_and_tags():
    tag_lines = _get_tags(True)

    af = AsdfFile()
    type_by_tag = af._extensions._type_index._type_by_tag
    exp_tags = sorted(type_by_tag.keys())

    for exp_tag, line in zip(exp_tags, tag_lines):
        tag_name, tag_class = line.split(":  ")
        assert tag_name == exp_tag

        exp_class = _class_to_string(type_by_tag[exp_tag])
        assert tag_class == exp_class
