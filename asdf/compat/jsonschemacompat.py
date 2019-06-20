from ..util import minversion


__all__ = ['JSONSCHEMA_LT_3']


JSONSCHEMA_LT_3 = not minversion('jsonschema', '3.0.0')
