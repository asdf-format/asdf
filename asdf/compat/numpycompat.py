from ..util import minversion


__all__ = ['NUMPY_LT_1_7']


NUMPY_LT_1_7 = not minversion('numpy', '1.7.0')
