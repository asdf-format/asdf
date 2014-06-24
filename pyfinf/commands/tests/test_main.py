# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

from .. import main


def test_help():
    # Just a smoke test, really
    main.main_from_args(['help'])
