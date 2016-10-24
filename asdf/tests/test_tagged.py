import io
import six
import datetime
from astropy.time import Time
from collections import OrderedDict

from .. import tagged
from .. import yamlutil
from .. import AsdfFile
from .. import schema as asdf_schema
from jsonschema import ValidationError

def walk_schema(schema, callback, ctx={}):
    def recurse(schema, path, combiner, ctx):
        if callback(schema, path, combiner, ctx, recurse):
            return

        for c in ['allOf', 'not']:
            for sub in schema.get(c, []):
                recurse(sub, path, c, ctx)

        for c in ['anyOf', 'oneOf']:
            for i, sub in enumerate(schema.get(c, [])):
                recurse(sub, path + [i], c, ctx)

        if schema.get('type') == 'object':
            for key, val in six.iteritems(schema.get('properties', {})):
                recurse(val, path + [key], combiner, ctx)

        if schema.get('type') == 'array':
            items = schema.get('items', {})
            if isinstance(items, list):
                for i, item in enumerate(items):
                    recurse(item, path + [i], combiner, ctx)
            elif len(items):
                recurse(items, path + ['items'], combiner, ctx)

    recurse(schema, [], None, ctx)


def flatten_combiners(schema):
    newschema = OrderedDict()

    def add_entry(path, schema, combiner):
        # TODO: Simplify?
        cursor = newschema
        for i in range(len(path)):
            part = path[i]
            if isinstance(part, int):
                cursor = cursor.setdefault('items', [])
                while len(cursor) <= part:
                    cursor.append({})
                cursor = cursor[part]
            elif part == 'items':
                cursor = cursor.setdefault('items', OrderedDict())
            else:
                cursor = cursor.setdefault('properties', OrderedDict())
                if i < len(path) - 1 and isinstance(path[i+1], int):
                    cursor = cursor.setdefault(part, [])
                else:
                    cursor = cursor.setdefault(part, OrderedDict())

        cursor.update(schema)

    def callback(schema, path, combiner, ctx, recurse):
        type = schema.get('type')
        schema = OrderedDict(schema)
        if type == 'object':
            del schema['properties']
        elif type == 'array':
            del schema['items']
        if 'allOf' in schema:
            del schema['allOf']
        if 'anyOf' in schema:
            del schema['anyOf']

        add_entry(path, schema, combiner)

    walk_schema(schema, callback)

    return newschema


def test_time_tag():
    schema = asdf_schema.load_schema('http://stsci.edu/schemas/asdf/time/time-1.0.0',
                                     resolve_references=True)
    schema = flatten_combiners(schema)

    date = Time(datetime.datetime.now())
    tree = {'date': date}
    asdf = AsdfFile(tree=tree)
    instance = yamlutil.custom_tree_to_tagged_tree(tree, asdf)
    
    try:
        asdf_schema.validate(instance, schema=schema)
    except ValidationError:
        fail = True
    else:
        fail = False
        
    assert fail, True
    
    tag = 'tag:stsci.edu:asdf/time/time-1.0.0'
    date = tagged.tag_object(tag, date)
    tree = {'date': date}
    instance = yamlutil.custom_tree_to_tagged_tree(tree, asdf)
    
    try:
        asdf_schema.validate(instance, schema=schema)
    except ValidationError:
        fail = True
    else:
        fail = False

    assert fail, False

if __name__ == "__main__":
    import pdb
    pdb.set_trace()
    test_time_tag()