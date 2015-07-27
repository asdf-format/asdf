# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import six

if six.PY2:
    from UserDict import UserDict
    from UserList import UserList
    from UserString import UserString
elif six.PY3:
    from .user_collections_py3.UserDict import UserDict
    from .user_collections_py3.UserList import UserList
    from .user_collections_py3.UserString import UserString

if six.PY2:
    from .functools_backport import lru_cache
elif six.PY3:
    try:
        from functools import lru_cache
    except ImportError:
        from .functools_backport import lru_cache
