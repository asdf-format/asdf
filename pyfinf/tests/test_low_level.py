# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

from astropy.tests.helper import pytest

from .. import finf

from . import helpers


def test_no_yaml_end_marker():
    yaml = """
%YAML 1.2
%TAG ! tag:stsci.edu,2014:finf/0.1.0/
--- !finf
foo: bar
    """

    buff = helpers.yaml_to_finf(yaml, yaml_headers=False)
    with pytest.raises(IOError):
        finf.FinfFile.read(buff)
