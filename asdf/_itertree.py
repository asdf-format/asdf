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


def breadth_first(d, get_children=None, skip_ids=None):
    get_children = get_children or _default_get_children
    skip_ids = skip_ids or set()
    dq = collections.deque()
    dq.append(_Edge(None, None, d))
    while dq:
        edge = dq.popleft()
        obj = edge.node
        if id(obj) in skip_ids:
            continue
        yield obj, edge
        children = get_children(obj)
        if children:
            skip_ids.add(id(obj))
            for key, value in children:
                dq.append(_Edge(edge, key, value))


def depth_first(d, get_children=None, skip_ids=None):
    get_children = get_children or _default_get_children
    skip_ids = skip_ids or set()
    dq = collections.deque()
    dq.append(_Edge(None, None, d))
    while dq:
        edge = dq.pop()
        obj = edge.node
        obj_id = id(obj)
        if obj_id in skip_ids:
            continue
        yield obj, edge
        children = get_children(obj)
        if children:
            skip_ids.add(obj_id)
            for key, value in children:
                dq.append(_Edge(edge, key, value))


def leaf_first(d, get_children=None, skip_ids=None):
    get_children = get_children or _default_get_children
    skip_ids = skip_ids or set()
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
        if obj_id in skip_ids:
            continue
        children = get_children(obj)
        if children:
            skip_ids.add(obj_id)
            dq.append(_ShowValue(edge, obj_id))
            for key, value in children:
                dq.append(_Edge(edge, key, value))
            continue
        yield obj, edge


def _default_setitem(obj, key, value):
    obj.__setitem__(key, value)


def _default_delitem(obj, key):
    if key in obj:
        obj.__delitem__(key)


def breadth_first_modify(d, callback, get_children=None, setitem=None, delitem=None, skip_ids=None):
    get_children = get_children or _default_get_children
    skip_ids = skip_ids or set()
    cache = {}  # TODO fix
    setitem = setitem or _default_setitem
    delitem = delitem or _default_delitem
    dq = collections.deque()
    dq.append(_Edge(None, None, d))
    while dq:
        edge = dq.popleft()
        obj = edge.node
        obj_id = id(obj)
        if obj_id in skip_ids:
            continue
        if obj_id not in cache:
            cache[obj_id] = callback(obj, edge)
        obj = cache[obj_id]
        if edge.parent is not None:
            if obj is RemoveNode:
                delitem(edge.parent.node, edge.key)
                continue
            setitem(edge.parent.node, edge.key, obj)
        children = get_children(obj)
        if children:
            skip_ids.add(obj_id)
            for key, value in children:
                dq.append(_Edge(edge, key, value))


def depth_first_modify(d, callback, get_children=None, setitem=None, delitem=None, skip_ids=None):
    get_children = get_children or _default_get_children
    skip_ids = skip_ids or set()
    cache = {}  # TODO fix
    setitem = setitem or _default_setitem
    delitem = delitem or _default_delitem
    dq = collections.deque()
    dq.append(_Edge(None, None, d))
    while dq:
        edge = dq.pop()
        obj = edge.node
        obj_id = id(obj)
        if obj_id in skip_ids:
            continue
        if obj_id not in cache:
            cache[obj_id] = callback(obj, edge)
        obj = cache[obj_id]
        if edge.parent is not None:
            if obj is RemoveNode:
                delitem(edge.parent.node, edge.key)
                continue
            setitem(edge.parent.node, edge.key, obj)
        children = get_children(obj)
        if children:
            skip_ids.add(obj_id)
            for key, value in children:
                dq.append(_Edge(edge, key, value))


def leaf_first_modify(d, callback, get_children=None, setitem=None, delitem=None, skip_ids=None):
    get_children = get_children or _default_get_children
    skip_ids = skip_ids or set()
    cache = {}  # TODO fix
    setitem = setitem or _default_setitem
    delitem = delitem or _default_delitem
    dq = collections.deque()
    dq.append(_Edge(None, None, d))
    while dq:
        edge = dq.pop()
        if isinstance(edge, _ShowValue):
            edge = edge.obj
            obj = edge.node
            obj_id = id(obj)
            if obj_id not in cache:
                cache[obj_id] = callback(obj, edge)
            obj = cache[obj_id]
            if edge.parent is not None:
                if obj is RemoveNode:
                    delitem(edge.parent.node, edge.key)
                else:
                    setitem(edge.parent.node, edge.key, obj)
            continue
        obj = edge.node
        obj_id = id(obj)
        if obj_id in skip_ids:
            continue
        children = get_children(obj)
        if children:
            skip_ids.add(obj_id)
            dq.append(_ShowValue(edge, obj_id))
            for key, value in children:
                dq.append(_Edge(edge, key, value))
            continue

        if obj_id not in cache:
            cache[obj_id] = callback(obj, edge)
        obj = cache[obj_id]
        if edge.parent is not None:
            if obj is RemoveNode:
                delitem(edge.parent.node, edge.key)
            else:
                setitem(edge.parent.node, edge.key, obj)


def _default_container_factory(obj):
    if isinstance(obj, dict):
        return dict()
    elif isinstance(obj, (list, tuple)):
        return [None] * len(obj)
    raise NotImplementedError()


def breadth_first_modify_and_copy(
    d, callback, get_children=None, setitem=None, delitem=None, container_factory=None, skip_ids=None
):
    get_children = get_children or _default_get_children
    skip_ids = skip_ids or set()
    cache = {}  # TODO fix
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
        if obj_id in skip_ids:
            continue
        if False and obj_id in cache:
            obj = cache[obj_id]
        else:
            obj = callback(obj, edge)
            if edge.parent is not None and obj is RemoveNode:
                # TODO handle multiple list key deletion
                delitem(edge.parent.node, edge.key)
                continue
            children = get_children(obj)
            if children:
                obj = container_factory(obj)
                edge.node = obj
                skip_ids.add(obj_id)
                for key, value in children:
                    dq.append(_Edge(edge, key, value))
            # cache[obj_id] = obj
        if result is None:
            result = obj
        if edge.parent is not None:
            setitem(edge.parent.node, edge.key, obj)
    return result


def depth_first_modify_and_copy(
    d, callback, get_children=None, setitem=None, delitem=None, container_factory=None, skip_ids=None
):
    get_children = get_children or _default_get_children
    skip_ids = skip_ids or set()
    cache = {}
    setitem = setitem or _default_setitem
    delitem = delitem or _default_delitem
    container_factory = container_factory or _default_container_factory
    result = None
    dq = collections.deque()
    dq.append(_Edge(None, None, d))
    while dq:
        edge = dq.pop()
        obj = edge.node
        # print(obj)
        obj_id = id(obj)
        # if obj_id in skip_ids:
        #    #print(f"\tskip because of id {obj_id}")
        #    continue
        if obj_id in cache:
            # print("\tfrom cache")
            new_obj = cache[obj_id][1]
        else:
            # print("\tstepping in")
            new_obj = callback(obj, edge)
            if edge.parent is not None and new_obj is RemoveNode:
                # TODO handle multiple list key deletion
                delitem(edge.parent.node, edge.key)
                continue
            children = get_children(new_obj)
            if children:
                container = container_factory(new_obj)
                edge.node = container
                # print(f"\tadding id {obj_id} to skips")
                # skip_ids.add(obj_id)
                for key, value in children:
                    dq.append(_Edge(edge, key, value))
                new_obj = container
            cache[obj_id] = (obj, new_obj)
        if result is None:
            result = new_obj
        if edge.parent is not None:
            setitem(edge.parent.node, edge.key, new_obj)
        # print(result)
    return result


def leaf_first_modify_and_copy(
    d, callback, get_children=None, setitem=None, delitem=None, container_factory=None, skip_ids=None
):
    get_children = get_children or _default_get_children
    skip_ids = skip_ids or set()
    pending = {}
    cache = {}
    setitem = setitem or _default_setitem
    delitem = delitem or _default_delitem
    container_factory = container_factory or _default_container_factory
    result = None
    dq = collections.deque()
    # print(f"Input obj id: {id(d['obj'])}")
    # print(f"Input inverse id: {id(d['obj']['inverse'])}")
    dq.append(_Edge(None, None, d))
    while dq:
        edge = dq.pop()
        # print(f"Processing {edge}")
        # print(f"\tdq={dq}")
        # print(f"\tcache={cache}")
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
                    # TODO handle multiple list key deletion
                    delitem(edge.parent.node, edge.key)
                else:
                    setitem(edge.parent.node, edge.key, new_obj)
            if obj_id in pending:
                for edge in pending[obj_id]:
                    if new_obj is RemoveNode:
                        # TODO handle multiple list key deletion
                        delitem(edge.parent.node, edge.key)
                    else:
                        setitem(edge.parent.node, edge.key, new_obj)
                del pending[obj_id]
            continue
        # print(f"\tNode id {id(edge.node)} at {edge.key} of {edge.parent}")
        obj = edge.node
        obj_id = id(obj)
        # if obj_id in skip_ids:
        #    print("\tskipping")
        #    continue
        if obj_id in cache:
            # print("\tfrom cache")
            new_obj = cache[obj_id][1]
        else:
            children = get_children(obj)
            if children:
                skip_ids.add(obj_id)
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
                    # if id(value) not in pending:
                continue
            # cache[obj_id] = callback(obj, edge)
            # obj = cache[obj_id]
            new_obj = callback(obj, edge)
            cache[obj_id] = (obj, new_obj)
        if result is None:
            result = new_obj
        if edge.parent is not None:
            if new_obj is RemoveNode:
                # TODO handle multiple list key deletion
                delitem(edge.parent.node, edge.key)
            else:
                setitem(edge.parent.node, edge.key, new_obj)
    return result
