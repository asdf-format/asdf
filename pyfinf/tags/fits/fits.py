# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

from astropy.io import fits
import numpy as np

from ...finftypes import FinfType


class FitsType(FinfType):
    name = 'fits/fits'
    types = [fits.HDUList]

    @classmethod
    def from_tree(cls, data, ctx):
        hdus = []
        first = True
        for hdu_entry in data:
            header = fits.Header([fits.Card(*x) for x in hdu_entry['header']])
            data = hdu_entry.get('data')
            if data is not None:
                data = np.asarray(data)
            if first:
                hdu = fits.PrimaryHDU(data=data, header=header)
                first = False
            else:
                hdu = fits.ImageHDU(data=data, header=header)
            hdus.append(hdu)
        hdulist = fits.HDUList(hdus)
        return hdulist

    @classmethod
    def to_tree(cls, hdulist, ctx):
        units = []
        for hdu in hdulist:
            header_list = []
            for card in hdu.header.cards:
                if card.comment:
                    new_card = [card.keyword, card.value, card.comment]
                else:
                    if card.value:
                        new_card = [card.keyword, card.value]
                    else:
                        if card.keyword:
                            new_card = [card.keyword]
                        else:
                            new_card = []
                header_list.append(new_card)

            hdu_dict = {}
            hdu_dict['header'] = header_list
            if hdu.data is not None:
                hdu_dict['data'] = hdu.data

            units.append(hdu_dict)

        return ctx.to_tree(units)

    @classmethod
    def assert_equal(cls, old, new):
        from numpy.testing import assert_array_equal

        for hdua, hdub in zip(old, new):
            assert_array_equal(hdua.data, hdub.data)
            for carda, cardb in zip(hdua.header.cards, hdub.header.cards):
                assert tuple(carda) == tuple(cardb)
