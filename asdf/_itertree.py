"""
For modification, order is important
for a tree

    a
  /  \
b     c
     / \
    d   e

when walking breadth-first down the tree, modify:
- a first
- b, c (any order)
- then d, e (any order)

this means that a might get modified changing
where b and c come from

when walking depth-first down the tree, modify:
- a first
- b or c
- if b, then c
- if c then d, e (any order)

when walking leaf-first up the tree, modify:
- d, e (any order)
- c, b (any order)
- a
(note that this is the inverse of depth-first)
"""
import collections


class _Edge:
    __slots__ = ["parent", "key", "node"]

    def __init__(self, parent, key, node):
        self.parent = parent
        self.key = key  # can be used to make path
        self.node = node  # can be used to get things like 'json_id', duplicate of obj in callback


class _RemoveNode:
    """
    Class of the RemoveNode singleton instance.  This instance is used
    as a signal for `asdf.treeutil.walk_and_modify` to remove the
    node received by the callback.
    """

    def __repr__(self):
        return "RemoveNode"


RemoveNode = _RemoveNode()


def edge_to_keys(edge):
    keys = []
    while edge.key is not None:
        keys.append(edge.key)
        edge = edge.parent
    return tuple(keys[::-1])


class _ShowValue:
    __slots__ = ["obj", "obj_id"]

    def __init__(self, obj, obj_id):
        self.obj = obj
        self.obj_id = obj_id


def _default_get_children(obj):
    if isinstance(obj, dict):
        return obj.items()
    elif isinstance(obj, (list, tuple)):
        return enumerate(obj)
    else:
        return None


def breadth_first(d, get_children=None):
    get_children = get_children or _default_get_children
    seen = set()
    dq = collections.deque()
    dq.append(_Edge(None, None, d))
    while dq:
        edge = dq.popleft()
        obj = edge.node
        obj_id = id(obj)
        if obj_id in seen:
            continue
        yield obj, edge
        children = get_children(obj)
        if children:
            seen.add(obj_id)
            for key, value in children:
                dq.append(_Edge(edge, key, value))


def depth_first(d, get_children=None):
    get_children = get_children or _default_get_children
    seen = set()
    dq = collections.deque()
    dq.append(_Edge(None, None, d))
    while dq:
        edge = dq.pop()
        obj = edge.node
        obj_id = id(obj)
        if obj_id in seen:
            continue
        yield obj, edge
        children = get_children(obj)
        if children:
            seen.add(obj_id)
            for key, value in children:
                dq.append(_Edge(edge, key, value))


def leaf_first(d, get_children=None):
    get_children = get_children or _default_get_children
    seen = set()
    dq = collections.deque()
    dq.append(_Edge(None, None, d))
    while dq:
        edge = dq.pop()
        if isinstance(edge, _ShowValue):
            edge = edge.obj
            obj = edge.node
            yield obj, edge
            continue
        obj = edge.node
        obj_id = id(obj)
        if obj_id in seen:
            continue
        children = get_children(obj)
        if children:
            seen.add(obj_id)
            dq.append(_ShowValue(edge, obj_id))
            for key, value in children:
                dq.append(_Edge(edge, key, value))
            continue
        yield obj, edge


def _default_setitem(obj, key, value):
    obj.__setitem__(key, value)


def _default_delitem(obj, key):
    obj.__delitem__(key)


def _delete_items(edges, delitem):
    # index all deletions by the parent node id
    by_parent_id = {}
    for edge in edges:
        parent_id = id(edge.parent.node)
        if parent_id not in by_parent_id:
            by_parent_id[parent_id] = []
        by_parent_id[parent_id].append(edge)
    for parent_id in by_parent_id:
        # delete with highest/last key first
        for edge in sorted(by_parent_id[parent_id], key=lambda edge: edge.key, reverse=True):
            delitem(edge.parent.node, edge.key)


def breadth_first_modify(d, callback, get_children=None, setitem=None, delitem=None):
    get_children = get_children or _default_get_children
    cache = {}
    to_delete = collections.deque()
    setitem = setitem or _default_setitem
    delitem = delitem or _default_delitem
    dq = collections.deque()
    dq.append(_Edge(None, None, d))
    while dq:
        edge = dq.popleft()
        obj = edge.node
        obj_id = id(obj)
        if obj_id in cache:
            new_obj = cache[obj_id][1]
        else:
            new_obj = callback(obj, edge)
            cache[obj_id] = (obj, new_obj)
            children = get_children(new_obj)
            if children:
                for key, value in children:
                    dq.append(_Edge(edge, key, value))
        if edge.parent is not None:
            if new_obj is RemoveNode:
                to_delete.append(edge)
                continue
            setitem(edge.parent.node, edge.key, new_obj)
    _delete_items(to_delete, delitem)


def depth_first_modify(d, callback, get_children=None, setitem=None, delitem=None):
    get_children = get_children or _default_get_children
    cache = {}
    to_delete = collections.deque()
    setitem = setitem or _default_setitem
    delitem = delitem or _default_delitem
    dq = collections.deque()
    dq.append(_Edge(None, None, d))
    while dq:
        edge = dq.pop()
        obj = edge.node
        obj_id = id(obj)
        if obj_id in cache:
            new_obj = cache[obj_id][1]
        else:
            new_obj = callback(obj, edge)
            cache[obj_id] = (obj, new_obj)
            children = get_children(new_obj)
            if children:
                for key, value in children:
                    dq.append(_Edge(edge, key, value))
        if edge.parent is not None:
            if new_obj is RemoveNode:
                to_delete.append(edge)
                continue
            setitem(edge.parent.node, edge.key, new_obj)
    _delete_items(to_delete, delitem)


def leaf_first_modify(d, callback, get_children=None, setitem=None, delitem=None):
    get_children = get_children or _default_get_children
    cache = {}
    pending = {}
    to_delete = collections.deque()
    setitem = setitem or _default_setitem
    delitem = delitem or _default_delitem
    dq = collections.deque()
    dq.append(_Edge(None, None, d))
    while dq:
        edge = dq.pop()
        if isinstance(edge, _ShowValue):
            obj_id = edge.obj_id
            edge = edge.obj
            obj = edge.node
            if obj_id not in cache:
                cache[obj_id] = (obj, callback(obj, edge))
            obj = cache[obj_id][1]
            if edge.parent is not None:
                if obj is RemoveNode:
                    to_delete.append(edge)
                else:
                    setitem(edge.parent.node, edge.key, obj)
            if obj_id in pending:
                for edge in pending[obj_id]:
                    if obj is RemoveNode:
                        to_delete.append(edge)
                    else:
                        setitem(edge.parent.node, edge.key, obj)
                del pending[obj_id]
            continue
        obj = edge.node
        obj_id = id(obj)
        if obj_id not in pending:
            pending[obj_id] = []
        children = get_children(obj)
        dq.append(_ShowValue(edge, obj_id))
        if children:
            for key, value in children:
                if id(value) in pending:
                    pending[id(value)].append(_Edge(edge, key, value))
                else:
                    dq.append(_Edge(edge, key, value))
            continue
    _delete_items(to_delete, delitem)


def _default_container_factory(obj):
    if isinstance(obj, dict):
        # init with keys to retain order
        return {k: None for k in obj}
    elif isinstance(obj, (list, tuple)):
        return [None] * len(obj)
    raise NotImplementedError()


def breadth_first_modify_and_copy(d, callback, get_children=None, setitem=None, delitem=None, container_factory=None):
    get_children = get_children or _default_get_children
    cache = {}
    to_delete = collections.deque()
    setitem = setitem or _default_setitem
    delitem = delitem or _default_delitem
    container_factory = container_factory or _default_container_factory
    result = None
    dq = collections.deque()
    dq.append(_Edge(None, None, d))
    while dq:
        edge = dq.popleft()
        obj = edge.node
        obj_id = id(obj)
        if obj_id in cache:
            obj = cache[obj_id][1]
        else:
            cobj = callback(obj, edge)
            if edge.parent is not None and cobj is RemoveNode:
                to_delete.append(edge)
                continue
            children = get_children(cobj)
            if children:
                container = container_factory(cobj)
                edge.node = container
                for key, value in children:
                    dq.append(_Edge(edge, key, value))
                cobj = container
            cache[obj_id] = (obj, cobj)
            obj = cobj
        if result is None:
            result = obj
        if edge.parent is not None:
            setitem(edge.parent.node, edge.key, obj)
    _delete_items(to_delete, delitem)
    return result


def depth_first_modify_and_copy(d, callback, get_children=None, setitem=None, delitem=None, container_factory=None):
    get_children = get_children or _default_get_children
    cache = {}
    to_delete = collections.deque()
    setitem = setitem or _default_setitem
    delitem = delitem or _default_delitem
    container_factory = container_factory or _default_container_factory
    result = None
    dq = collections.deque()
    dq.append(_Edge(None, None, d))
    while dq:
        edge = dq.pop()
        obj = edge.node
        obj_id = id(obj)
        if obj_id in cache:
            new_obj = cache[obj_id][1]
        else:
            new_obj = callback(obj, edge)
            if edge.parent is not None and new_obj is RemoveNode:
                to_delete.append(edge)
                continue
            children = get_children(new_obj)
            if children:
                container = container_factory(new_obj)
                edge.node = container
                for key, value in children:
                    dq.append(_Edge(edge, key, value))
                new_obj = container
            cache[obj_id] = (obj, new_obj)
        if result is None:
            result = new_obj
        if edge.parent is not None:
            setitem(edge.parent.node, edge.key, new_obj)
    _delete_items(to_delete, delitem)
    return result


def leaf_first_modify_and_copy(d, callback, get_children=None, setitem=None, delitem=None, container_factory=None):
    get_children = get_children or _default_get_children
    pending = {}
    cache = {}
    to_delete = collections.deque()
    setitem = setitem or _default_setitem
    delitem = delitem or _default_delitem
    container_factory = container_factory or _default_container_factory
    result = None
    dq = collections.deque()
    dq.append(_Edge(None, None, d))
    while dq:
        edge = dq.pop()
        if isinstance(edge, _ShowValue):
            obj_id = edge.obj_id
            edge = edge.obj
            obj = edge.node
            if obj is result:
                result = None
            if obj_id not in cache:
                new_obj = callback(obj, edge)
                cache[obj_id] = (obj, new_obj)
            else:
                new_obj = cache[obj_id][1]
            if result is None:
                result = new_obj
            if edge.parent is not None:
                if new_obj is RemoveNode:
                    to_delete.append(edge)
                else:
                    setitem(edge.parent.node, edge.key, new_obj)
            if obj_id in pending:
                for edge in pending[obj_id]:
                    if new_obj is RemoveNode:
                        to_delete.append(edge)
                    else:
                        setitem(edge.parent.node, edge.key, new_obj)
                del pending[obj_id]
            continue
        obj = edge.node
        obj_id = id(obj)
        if obj_id in cache:
            new_obj = cache[obj_id][1]
        else:
            children = get_children(obj)
            if children:
                container = container_factory(obj)
                pending[obj_id] = []
                if result is None:
                    result = container
                edge.node = container
                dq.append(_ShowValue(edge, obj_id))
                for key, value in children:
                    if id(value) in pending:
                        pending[id(value)].append(_Edge(edge, key, value))
                    else:
                        dq.append(_Edge(edge, key, value))
                continue
            new_obj = callback(obj, edge)
            cache[obj_id] = (obj, new_obj)
        if result is None:
            result = new_obj
        if edge.parent is not None:
            if new_obj is RemoveNode:
                to_delete.append(edge)
            else:
                setitem(edge.parent.node, edge.key, new_obj)
    _delete_items(to_delete, delitem)
    return result
