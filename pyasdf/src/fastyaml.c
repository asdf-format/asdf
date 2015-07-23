#include <math.h>
#include <yaml.h>
#include <Python.h>


#if PY_MAJOR_VERSION >= 3
#define IS_PY3K 1

#define PyInt_FromString PyLong_FromString
#define PyInt_FromLong PyLong_FromLong
#endif


static PyObject *tag_object_method;
static PyObject *ordered_dict;


#define IS_DIGIT(c) (((c) >= '0') && ((c) <= '9'))


static int
memo_anchor(PyObject *anchors, char *anchor_name, PyObject *obj)
{
    if (anchor_name != NULL && anchor_name[0] != 0 && obj != NULL) {
        return PyDict_SetItemString(anchors, anchor_name, obj);
    }
    return 0;
}


static PyObject*
tag_object(char *tag, PyObject *instance)
{
    PyObject *tagged;

    if (instance != NULL && tag != NULL && tag[0] != 0) {
        tagged = PyObject_CallFunction(tag_object_method, "sO", tag, instance);
        Py_DECREF(instance);
        return tagged;
    }

    return instance;
}


static PyObject*
parse_node(PyObject *anchors, yaml_parser_t *parser, yaml_event_t *event);


static PyObject*
parse_mapping(PyObject *anchors, yaml_parser_t *parser, yaml_event_t *event);


static PyObject*
make_alias(PyObject *anchors, yaml_event_t *event)
{
    PyObject *result;
    result = PyDict_GetItemString(anchors, (char *)event->data.alias.anchor);
    if (result == NULL) {
        return NULL;
    }
    Py_INCREF(result);
    return result;
}


static PyObject*
_make_scalar(yaml_event_t *event)
{
    char c;
    int length;
    char *value;
    char *numstart;
    char *end;
    char *expected_end;
    PyObject *result;
    double d;

    // TODO: Comma separators
    // TODO: Sexigesimal
    // TODO: Time/date stamps

    numstart = value = (char *)event->data.scalar.value;
    length = event->data.scalar.length;
    end = expected_end = (char *)event->data.scalar.value + event->data.scalar.length;

    if (event->data.scalar.length == 0 ||
        event->data.scalar.style == YAML_SINGLE_QUOTED_SCALAR_STYLE ||
        event->data.scalar.style == YAML_DOUBLE_QUOTED_SCALAR_STYLE) {
        return PyUnicode_DecodeUTF8(value, event->data.scalar.length, NULL);
    }

    switch(value[0]) {
    case '.':
        if (strncmp(value + 1, "NaN", 4) == 0) {
            return PyFloat_FromDouble(NAN);
        } else if (strncmp(value + 1, "nan", 4) == 0) {
            return PyFloat_FromDouble(NAN);
        } else if (strncmp(value + 1, "Inf", 4) == 0) {
            return PyFloat_FromDouble(INFINITY);
        } else if (strncmp(value + 1, "inf", 4) == 0) {
            return PyFloat_FromDouble(INFINITY);
        }
        break;

    case '0':
        if (value[1] == 'x') {
            // Hexadecimal
            end = expected_end;
            result = PyInt_FromString(value + 2, &end, 16);
            if (result == NULL) {
                PyErr_Clear();
            } else if (end != expected_end) {
                Py_DECREF(result);
            } else {
                return result;
            }
        } else if (value[1] >= '0' && value[1] <= '8') {
            // Octal
            end = expected_end;
            result = PyInt_FromString(value + 1, &end, 8);
            if (result == NULL) {
                PyErr_Clear();
            } else if (end != expected_end) {
                Py_DECREF(result);
            } else {
                return result;
            }
        } else if (length == 1) {
            return PyInt_FromLong(0);
        }
        break;

    case '-':
        if (value[1] == '.') {
            if (strncmp(value + 2, "Inf", 4) == 0) {
                return PyFloat_FromDouble(-INFINITY);
            } else if (strncmp(value + 2, "inf", 4) == 0) {
                return PyFloat_FromDouble(-INFINITY);
            }
        }
        numstart = value + 1;
        break;

    case '+':
        if (value[1] == '.') {
            if (strncmp(value + 2, "Inf", 4) == 0) {
                return PyFloat_FromDouble(INFINITY);
            } else if (strncmp(value + 2, "inf", 4) == 0) {
                return PyFloat_FromDouble(INFINITY);
            }
        }
        numstart = value + 1;
        break;

    case 'n':
        if (strncmp(value + 1, "ull", 4) == 0) {
            Py_RETURN_NONE;
        }
        goto treat_as_string;

    case 't':
        if (strncmp(value + 1, "rue", 4) == 0) {
            Py_RETURN_TRUE;
        }
        goto treat_as_string;

    case 'f':
        if (strncmp(value + 1, "alse", 5) == 0) {
            Py_RETURN_FALSE;
        }
        goto treat_as_string;
    }

    c = numstart[0];
    if (IS_DIGIT(c) || c == '.') {
        end = expected_end;
        result = PyInt_FromString(value, &end, 10);
        if (result == NULL) {
            PyErr_Clear();
        } else if (end != expected_end) {
            Py_DECREF(result);
        } else {
            return result;
        }

        end = expected_end;
        d = PyOS_string_to_double(
            value, (char **)&end, PyExc_OverflowError);
        if (end == expected_end) {
            return PyFloat_FromDouble(d);
        } else if (PyErr_Occurred()) {
            PyErr_Clear();
        }
    }

 treat_as_string:

    return PyUnicode_DecodeUTF8(value, event->data.scalar.length, NULL);
}


static PyObject*
make_scalar(PyObject *anchors, yaml_event_t *event)
{
    PyObject *scalar;

    scalar = _make_scalar(event);

    scalar = tag_object((char *)event->data.scalar.tag, scalar);

    if (memo_anchor(anchors, (char *)event->data.scalar.anchor, scalar)) {
        Py_DECREF(scalar);
        return NULL;
    }

    return scalar;
}


static PyObject*
parse_ordered_dict(PyObject *anchors, yaml_parser_t *parser, yaml_event_t *event)
{
    PyObject *result;
    PyObject *key;
    PyObject *value;

    result = PyObject_CallObject(ordered_dict, NULL);
    if (result == NULL) {
        return result;
    }

    if (memo_anchor(anchors, (char *)event->data.sequence_start.anchor, result)) {
        Py_DECREF(result);
        return NULL;
    }

    while (1) {
        if (!yaml_parser_parse(parser, event)) {
            PyErr_SetString(
                PyExc_ValueError,
                "Parsing error 1");
            Py_DECREF(result);
            return NULL;
        }

        if (event->type == YAML_SEQUENCE_END_EVENT) {
            break;
        } else if (event->type != YAML_MAPPING_START_EVENT) {
            PyErr_SetString(
                PyExc_ValueError,
                "Expected mapping start or sequence end event");
            Py_DECREF(result);
            return NULL;
        }

        key = parse_node(anchors, parser, event);
        if (key == NULL) {
            Py_DECREF(result);
            return NULL;
        }

        value = parse_node(anchors, parser, event);
        if (value == NULL) {
            Py_DECREF(key);
            Py_DECREF(result);
            return NULL;
        }

        if (PyObject_SetItem(result, key, value)) {
            Py_DECREF(key);
            Py_DECREF(value);
            Py_DECREF(result);
            return NULL;
        }

        Py_DECREF(key);
        Py_DECREF(value);

        if (!yaml_parser_parse(parser, event)) {
            PyErr_SetString(
                PyExc_ValueError,
                "Parsing error 2");
            Py_DECREF(result);
            return NULL;
        }

        if (event->type != YAML_MAPPING_END_EVENT) {
            PyErr_SetString(
                PyExc_ValueError,
                "Expected mapping end event");
            Py_DECREF(result);
            return NULL;
        }
    }

    return result;
}


static PyObject*
parse_sequence(PyObject *anchors, yaml_parser_t *parser, yaml_event_t *event)
{
    PyObject *result;
    PyObject *subresult;

    if (event->data.sequence_start.tag &&
        strncmp((char *)event->data.sequence_start.tag, "tag:yaml.org,2002:omap", 23) == 0) {
        return parse_ordered_dict(anchors, parser, event);
    }

    result = PyList_New(0);
    if (result == NULL) {
        return result;
    }

    result = tag_object((char *)event->data.sequence_start.tag, result);

    if (memo_anchor(anchors, (char *)event->data.sequence_start.anchor, result)) {
        Py_DECREF(result);
        return NULL;
    }

    while ((subresult = parse_node(anchors, parser, event))) {
        if (PyObject_CallMethod(result, "append", "O", subresult) == NULL) {
            Py_DECREF(subresult);
            Py_DECREF(result);
            return NULL;
        }
        Py_DECREF(subresult);
    }

    if (event->type != YAML_SEQUENCE_END_EVENT) {
        PyErr_SetString(PyExc_ValueError, "Expected sequence end event");
        Py_DECREF(result);
        return NULL;
    }

    return result;
}


static PyObject*
parse_mapping(PyObject *anchors, yaml_parser_t *parser, yaml_event_t *event)
{
    PyObject *result;
    PyObject *key;
    PyObject *value;

    result = PyDict_New();
    if (result == NULL) {
        return result;
    }

    result = tag_object((char *)event->data.mapping_start.tag, result);

    if (memo_anchor(anchors, (char *)event->data.mapping_start.anchor, result)) {
        Py_DECREF(result);
        return NULL;
    }

    while ((key = parse_node(anchors, parser, event))) {
        value = parse_node(anchors, parser, event);
        if (value == NULL) {
            Py_DECREF(key);
            Py_DECREF(result);
            return NULL;
        }
        if (PyObject_SetItem(result, key, value)) {
            Py_DECREF(key);
            Py_DECREF(value);
            Py_DECREF(result);
            return NULL;
        }
        Py_DECREF(key);
        Py_DECREF(value);
    }

    if (event->type != YAML_MAPPING_END_EVENT) {
        PyErr_SetString(PyExc_ValueError, "Expected mapping end event");
        Py_DECREF(result);
        return NULL;
    }

    return result;
}


static PyObject*
parse_node(PyObject *anchors, yaml_parser_t *parser, yaml_event_t *event)
{
    PyObject *result = NULL;

    if (!yaml_parser_parse(parser, event)) {
        PyErr_SetString(
            PyExc_ValueError, "Parsing error 3");
        return NULL;
    }

    switch(event->type) {
    case YAML_ALIAS_EVENT:
        result = make_alias(anchors, event);
        break;
    case YAML_SCALAR_EVENT:
        result = make_scalar(anchors, event);
        break;
    case YAML_SEQUENCE_START_EVENT:
        result = parse_sequence(anchors, parser, event);
        break;
    case YAML_MAPPING_START_EVENT:
        result = parse_mapping(anchors, parser, event);
        break;
    default:
        return NULL;
    }

    return result;
}


static PyObject*
parse_document(yaml_parser_t *parser, yaml_event_t *event)
{
    PyObject *result = NULL;
    PyObject *anchors = NULL;

    anchors = PyDict_New();
    if (anchors == NULL) {
        return NULL;
    }

    if (!yaml_parser_parse(parser, event)) {
        PyErr_SetString(
            PyExc_ValueError,
            "Parsing error 4");
        Py_DECREF(anchors);
        return NULL;
    }

    if (event->type == YAML_DOCUMENT_START_EVENT) {
        result = parse_node(anchors, parser, event);
        if (result == NULL) {
            Py_DECREF(anchors);
            return NULL;
        }
    } else {
        PyErr_SetString(
            PyExc_ValueError,
            "Expected document start event");
        Py_DECREF(anchors);
        return NULL;
    }

    if (!yaml_parser_parse(parser, event)) {
        PyErr_SetString(
            PyExc_ValueError,
            "Parsing error 5");
        Py_DECREF(anchors);
        Py_DECREF(result);
        return NULL;
    }

    if (event->type == YAML_DOCUMENT_END_EVENT) {
        Py_DECREF(anchors);
        return result;
    } else {
        PyErr_SetString(
            PyExc_ValueError,
            "Expected document end event");
        Py_DECREF(anchors);
        Py_DECREF(result);
        return NULL;
    }
}


static PyObject*
parse_stream(yaml_parser_t *parser, yaml_event_t *event)
{
    PyObject *result = NULL;

    if (!yaml_parser_parse(parser, event)) {
        PyErr_SetString(
            PyExc_ValueError,
            "Parsing error 6");
        return NULL;
    }

    if (event->type == YAML_STREAM_START_EVENT) {
        result = parse_document(parser, event);
        if (result == NULL) {
            return NULL;
        }
    } else {
        PyErr_SetString(
            PyExc_ValueError,
            "Expected stream start event");
        return NULL;
    }

    if (!yaml_parser_parse(parser, event)) {
        PyErr_SetString(
            PyExc_ValueError,
            "Parsing error 7");
        Py_DECREF(result);
        return NULL;
    }

    if (event->type == YAML_STREAM_END_EVENT) {
        return result;
    } else {
        PyErr_SetString(
            PyExc_ValueError,
            "Expected stream end event");
        Py_DECREF(result);
        return NULL;
    }
}


static int
read_handler(void *ext, unsigned char *buffer, size_t size, size_t *length) {
    PyObject *fd = (PyObject *)ext;
    PyObject *py_bytes;
    Py_ssize_t py_length;
    char *py_buffer;

    py_bytes = PyObject_CallMethod(fd, "read", "i", size);
    if (py_bytes == NULL) {
        return 0;
    }

    if (PyBytes_AsStringAndSize(py_bytes, &py_buffer, &py_length)) {
        return 0;
    }

    memcpy(buffer, py_buffer, py_length);
    *length = py_length;

    return 1;
}


static PyObject*
parse_yaml(PyObject* self, PyObject *args)
{
    yaml_parser_t parser;
    yaml_event_t event;
    PyObject *result = NULL;
    PyObject *fd = NULL;

    if (!PyArg_ParseTuple(args, "O", &fd)) {
        return NULL;
    }

    yaml_parser_initialize(&parser);

    yaml_parser_set_input(&parser, read_handler, (void *)fd);

    result = parse_stream(&parser, &event);
    if (result == NULL) {
        goto exit;
    }

 exit:

    yaml_parser_delete(&parser);

    if (result == NULL) {
        if (!PyErr_Occurred()) {
            PyErr_SetString(PyExc_ValueError, "Error parsing YAML");
        }
        return NULL;
    }

    if (PyErr_Occurred()) {
        Py_DECREF(result);
        return NULL;
    }

    return result;
}

/******************************************************************************
 * Module setup
 ******************************************************************************/

static PyMethodDef module_methods[] =
{
    {"parse_yaml", (PyCFunction)parse_yaml, METH_VARARGS,
     "Fast method to parse YAML"},
    {NULL}  /* Sentinel */
};

struct module_state {
    void* none;
};


#ifdef IS_PY3K
static int module_traverse(PyObject* m, visitproc visit, void* arg)
{
    return 0;
}

static int module_clear(PyObject* m)
{
    return 0;
}

static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT,
    "fastyaml",
    "Fast YAML parser",
    sizeof(struct module_state),
    module_methods,
    NULL,
    module_traverse,
    module_clear,
    NULL
};

#  define INITERROR return NULL

PyMODINIT_FUNC
PyInit_fastyaml(void)
#else /* Not PY3K */
#  define INITERROR return

#  ifndef PyMODINIT_FUNC  /* declarations for DLL import/export */
#    define PyMODINIT_FUNC void
#  endif

PyMODINIT_FUNC
initfastyaml(void)
#endif
{
    PyObject* m;
    PyObject* module;

#ifdef IS_PY3K
    m = PyModule_Create(&moduledef);
#else
    m = Py_InitModule3("fastyaml", module_methods, "Fast YAML parser");
#endif

    if ((module = PyImport_ImportModule("pyasdf.tagged")) == NULL) {
        INITERROR;
    }
    if ((tag_object_method = PyObject_GetAttrString(module, "tag_object")) == NULL) {
        Py_DECREF(module);
        INITERROR;
    }
    Py_DECREF(module);

    if ((module = PyImport_ImportModule("astropy.utils.compat.odict")) == NULL) {
        INITERROR;
    }
    if ((ordered_dict = PyObject_GetAttrString(module, "OrderedDict")) == NULL) {
        Py_DECREF(module);
        INITERROR;
    }
    Py_DECREF(module);

    if (m == NULL)
        INITERROR;

#ifdef IS_PY3K
    return m;
#endif
}
