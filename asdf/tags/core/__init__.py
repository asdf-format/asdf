# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

from ...asdftypes import AsdfType


class ValidateDictMixin(dict):
    def __init__(self, *args, **kwargs):
        self._validator = kwargs.get('validator')
        if self._validator:
            kwargs.pop('validator')
        super(ValidateDictMixin, self).__init__(*args, **kwargs)

    def __setitem__(self, key, value):
        if self._validator:
            asdf_object = AsdfObject(self)
            asdf_object[key] = value
            self._validator(asdf_object)
        super(ValidateDictMixin, self).__setitem__(key, value)


class AsdfObject(ValidateDictMixin, AsdfType):
    name = 'core/asdf'


class Software(ValidateDictMixin, AsdfType):
    name = 'core/software'


class HistoryEntry(ValidateDictMixin, AsdfType):
    name = 'core/history_entry'


from .constant import ConstantType
from .ndarray import NDArrayType
from .complex import ComplexType
from .table import TableType, ColumnType
