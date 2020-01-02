High level overview of the basic ASDF library
=============================================

This document is an attempt to make it easier to understand the design and
workings of the python asdf library for those unfamiliar with it. This is
expected to grow organically so at the moment it should not be considered
complete or comprehensive.

Understanding the design is complicated by the fact that the library 
effectively inserts custom methods or classes into the objects that
the pyyaml and jsonschema libraries use. Understanding what is going on
thus means having some understanding of the relevant parts of the 
internals of both of those libraries. This overview will try to provide 
a small amount of context for these package to illuminate how the code 
in asdf interacts with them.

There are at least two ways of outlining the design. One is to give high level
overviews of the various modules and how they interact with other modules. The
other is to illustrate how code is actually invoked in common operations, this
often being much more informative on a practical level (at least I find that to
be the case). This document will attempt to do both.

We will start with a high-level review of concepts and terms and point to where
these are handled in the asdf modules. 

Because of the complexity, this initial design overview will focus on issues of
validation and tree construction when reading.

Some terminology and definitions 
--------------------------------

**URI vs URL (Universal Resource Identifier)**. This is distinguished from URL
(Universal Resource Locator) primarily in that URI is a mechanism for a unique
name that follows a particular syntax, but itself may not indicate where the
resource is. Generally URLs are expected to be used on the web for the HTTP
protocol, though for asdf, this isn't necessarily the case as mentioned next.

**Resolver:** Tools to map URIs and tags into actual locations of schema files,
which may be local directories (the usual approach) or an actual URL for
retrieval over the network. This is more complicated that it may seem for
reasons explained later.

**Validation:** Tool to confirm that the YAML conforms to the schemas that
apply. A lot goes on in this area and it is pretty complex in the
implementation.

**Tree building:** The YAML content is built into a tree in two stages. The YAML
parser converts the raw YAML into a custom Python structure. It is that
structure that is validated. Then if no errors are found, the tree is
converted into a tree where tagged nodes get converted into special Python
objects (usually), e.g., WCS object or numpy arrays (well, not quite that
simply for numpy arrays).

The above is a simplified view of what happens when an ASDF file is read.

Most of resolver tools and code is in ``resolver.py`` (but not all)

Most of the validation code is in ``schema.py``

The code that builds the trees is spread in many places: ``tagged.py``,
``treeutil.py``, ``types.py`` as well as all the extension code that supplies
code to handle the tags within (and often the the associated schemas).

A note on the location of schemas and tag code; there is a bit of schizophrenic
aspect to this since schema should be language agnostic and in that view, not
bundled with specific language library code. But currently nearly all of the
implementation is in Python so while the long-term goal is to keep them
separate, it is more convenient to keep them together for now. You will see
cases where they are separate and some where they are bundled].

Actions that happen when ASDF is imported
-----------------------------------------

The entry points for all asdf extensions are obtained in ``extension.py`` (by
the class ``_DefaultExtensions``) which is instantiated at the end of the module
as ``default_extensions``, but the entry points are only found when 
default_extensions.extensions is accessed (it's a property)

The effect of this is to load all the specified entry point classes for  all the
extensions that have registered through the entry point mechanism. (see
[https://packaging.python.org/specifications/entry-points/]) The list of classes
so loaded is what ``default_extensions.extensions`` returns along with all the
built-in extensions part of ASDF.

When an ``AsdfFile`` class is instantiated, one thing that happens on the
``__init__`` is that ``self._process_extensions()`` is called with an empty
list. That results in ``default_extensions.extension_list`` being accessed,
which then results in ``extension.AsdfExtensionList`` being instantiated with
the created extensions property.

This class populates the ``tag_mapping``, ``url_mapping`` lists and the
validators  dictionary, as well as populating the ``_type_index`` attribute with
the ``AsdfTypes`` subclasses defined in the extensions.

As a last step, the ``tag_mapping`` and ``url_mapping`` methods are generated
from  ``resolver.Resolver`` with the initial lists. These lists consist of
2-tuples. In the first case it is a mechanism to map the tag string to a url
string, typically with an expected prefix or suffix to the tag (suffix is
typical)  so that given a full tag, it generates a url that includes the suffix
This permits one mapping to cover many tag variants. (The details of mapping
machinery with examples are given in a later section since understanding this is
essential to defining new tags and corresponding schemas.)

The URL mapping works in a similar way, except that it consists of 2-tuples
where the first element is the common elements of the url, and the second  part
maps it to an actual location (url or file path). Again the second part may
include a place holder for the suffix or prefix, and code to generate the path
to the schema file.

The use of the resolver object turns these lists into functions so that 
supplied the appropriate input that matches something in the list, it gives the
corresponding output.

Outline of how an ASDF file is opened and read into the corresponding Python
object.
------------------------------------------------------------------------------------

The starting point can be found in ``asdf.py`` essentially through the following
chain (many calls and steps left out to keep it simpler to follow)

When ``asdf.open("myasdffile.asdf")`` is called, it is aliased to
``asdf.open_asdf`` which first creates an instance of ``asdf.AsdfFile`` (let's
call the instance ``af``), then calls ``af._open_impl()`` and then
``af._open_asdf``. That invokes a call to ``generic_io.get_file()``.

``generic.py`` basically contains code to handle all the variants of I/O
possible (files, streaming, http access, etc). In this case it returns a
``RealFile`` instance that wraps a  local file system file.

Next the file is examined to see if it is an ASDF file (first by examining the
first few lines in the header). If it passes those checks, the header (yaml)
section of the file is extracted through a proxy mechanism that signals an end
of file when the end of the yaml is reached, but otherwise looks like a file
object.

The yaml parsing phase described below normally returns a "tagged_tree". That is
(somewhat simplified), it returns the data structure that yaml would normally
return without any object conversion (i.e., all nodes are either dicts, lists,
or scalar values), except that they are objects that now sport a tag attribute
that indicates if a tag was associated with that node and what the tag was.

This reader object is passed to the yaml parser by calling
``yamlutil.load_tree``. A simple explanation for what goes on here is necessary
to understand how this all works. Yaml supports various kinds of loaders. For
security reasons, the "safe" loader is used (note that both C and python
versions are supported through an indirection of the ``_yaml_base_loader``
defined at the beginning of that module that determines whether the C version is
available). The loaders are recursive mechanisms that build the tree structure. 
Note that ``yamlutil.load_tree`` creates a temporary subclass of ``AsdfLoader``
and attaches a reference to the AsdfFile instance as the ``.ctx`` attribute of
that temporary subclass.

One of the hooks that pyyaml supplies is the ability to overload the method
``construct_object``. That's what the class ``yamlutil.AsdfLoader`` does. pyyaml
calls this method at each node in the tree to see if anything special should be
done. One could perform conversion to predefined objects here, but instead it
does the following: it sees if the node.tag attribute is handled by yaml itself
(examples?) it calls that constructor which returns the type yaml converts it
to. Otherwise:

 - it converts the node to the type indicated (dict, list, or scalar type) by
 - yaml for that node.  it obtains the appropriate tag class (an AsdfType
 - subclass) from the AsdfFile instance (using ``ctx.type_index.fix_yaml_tag``
 - to deal with version issues to match the most appropriate tag class).  it
 - wraps all the node alternatives in a special asdf ``Tagged`` class instance
 - variant where that object contains a ._tag attribute that is a reference to
 - the corresponding Tag class.

The loading process returnes a tree of these Tagged object instances. This
tagged_tree is then returned to the ``af`` instance (still running the
``_open_asdf()`` method) this tree is  passed to to the ``_validate()`` method
(This is the major reason that the tree isn't  directly converted to an object
tree since jsonschema would not be able to use the  final object tree for
validation, besides issues relate to the fact that things that don't validate
may not be converable to the designated object.) 

The validate machinery is a bit confusing since there are essentially two basic 
approaches to how validation is done. One type of validation is for validation
of schema files themselves, and the fundamental schemas for ...

The schema.py file is fairly involved and the details are covered elsewhere.
When the validator machinery is constructed, it uses the fundamental validation
files (schemas). But this doesn't handle the fact that the file being validated
is yaml, not json and that there are items in yaml not part of json so special
handling is needed. And the way it is handled is through a internal mechanism of
the jsonschema library. There is a method that jsonschema calls recursively for
a validator and it is called iter_errors. The subclass of the jsonschema
validator class is defined as schema.ASDFValidator and this method is overloaded
in this class. Despite its name, it's primary purpose is to validate the special
features that yaml has, namely applying schemas associated with tags (this is
not part of the normal jsonschema scheme [ahem]). It is in this method that it
looks for a tag for a node and if it exists and in the tag_index, loads the
appropriate schema and applies it to the node. (jsonschemas are normally only
associated with a whole json entity rather than specific nodes). While the
purpose of this  method is to iteratively handle errors that jsonschema detects,
it has essentially been repurposed as the means of interjecting handling tag
schemas.

In order to prevent repeated loading of the same schema, the lru caching scheme
is used (from functools in the standard library) where the last n cached schemas
are  saved (details of how this works were recently changed to prevent a serious
memory leak)

In any event, a lot is going on behind the scenes in validation and it deserves
its  own description elsewhere.

After validation, the tagged tree is then passed to
yamlutil.tagged_tree_to_custom_tree() where the nodes in the tree that have
special tag code convert the nodes into the  appropriate Python objects that the
base asdf and extensions are aware of. This is accomplished by that function
defining a walker "callback" function (defined within that function as to pick
up the af object intrinsically). The function then passes the callback walker to
treeutil.walk_and_modify() where the tree will be traversed recursively applying
the tag code associated with the tag to the more primative tree representation
replacing such nodes wtih Python objects. The tree travsersal starts from the
top, but the objects are created from the bottom up due to  recursion.

The result is what af.tree is set to, after doing another tree travseral looking
for special type hooks for each node. I haven't yet found any use of that
feature.

Not quite that simple
---------------------

Outline of schema.py
--------------------

This module is somewhat confusing due to the many functions and methods with
some variant of validate in their name. This will try to make clear what they do
(a renaming of these may be in order).

Here is a list of the functions/classes in ``schema.py`` and their purpose and
where  they sit in the order of things

default_ext_resolver

**_type_to_tag:** Handles mapping python types to yaml_tags, with the addition
of support for OrderedDicts.

The next 5 functions are put in the ``YAML_VALIDATORS`` dictionary to ultimately
be used by ``_create_validator`` to create the json validator object

------

**validate_tag:** Obtain the relevant tag for the supplied instance (either
built ins or custom objects) and check that it matches the tag supplied to the
function.

**validate_propertyOrder:** Not really a validator but rather as a trick to
indicate that properties should retain their order.

**validate_flowStyle:** Not really a validator but rather as a trick to store
what style to use to write the elements (for yaml objects and arrays)

**validate_style:** Not really a validator but rather as a trick to store info
on what style to use to write the string.

**validate_type:** Used to deal with date strings

(I'd suggest we rename the above to be more descriptive of the action than where
they  are stuck in the validation machinery; e.g., ``set_propertyOrder``)

**validate_fill_default:** Set the default values for all properties that have a
subschema  that defines a default. Called indirectly in ``fill_defaults``

**validate_remove_default:** does the opposite; remove all properties where
value equals  subschema default. Called indirectly in ``remove_defaults`` (For
this and the above, validate in the name mostly confuses although it is used by
the json validator.)

[these could be renamed as well since they do more than validate]


**_create_validator:** Creates an ``ASDFValidator`` class on the fly that uses
the  ``jsonchema.validators`` class created. This ``ASDFValidator`` class
overrides the ``iter_errors`` method that is used to handle yaml tag cases
(using the ``._tag`` attribute of the node to obtain the corresponding  schema
for that tag; e.g., it calls ``load_schema`` to obtain the right schema when
called for each node in the jsonschema machinery). What isn't clear to me is why
this is done on the fly and at least cached since it really only handles two
variants of calls (basically which JSONSCHEMA version is to be used). Otherwise
it doesn't appear to vary except for that. Admittedly, this is only created at
the top level. This is called by ``get_validator``.

**class OrderedLoader:** Hnherits from the ``_yaml_base_loader``, but otherwise
does nothing new in the definition. But the following code defines 
``construct_mapping``, and then adds it as a method.

**construct_mapping:** Defined outside the ``OrderedLoader`` class but to be
added to the  ``OrderedLoader`` class by use of the base class add_constructor
method. This function flattens the mapping and returns an ``OrderedDict`` of the
property attributes (This needs some deep understanding of how the yaml parser
actually works, which I don't have at the  moment. Apparently mappings can be
represented as nested trees as the yaml is originally parsed. Or something like
that.)

**_load_schema:** Loads json or yaml schemas (using the ``OrderedLoader``).

**_make_schema_loader:** Defines the function load_schema using the provided
resolver and _load_schema.

**_make_resolver:** Sets the schema loader for http, https, file, tag using a
dictionary where these access methods are the keys and the schema loader
returning only the schema (and not the uri). These all appear to use the same
schema loader.

**_load_draft4_metaschema:**

**load_custom_schema:** Deals with custom schemas.

**load_schema:** Loads a schema from the specified location (this is cached).
Called for every tag encountered (uses resolver machinery). Most of the
complexity is in resolving json references. Calls ``_make_schema_loader,
resolver, reference.resolve_fragment, load_schema``

**get_validator:** Calls ``_create_validator``. Is called by validate to return
the created validator.

**validate_large_literals:** Ensures tree has no large literals (raises error if
it does)

**validate:** Uses ``get_validator`` to get a validator object and then calls
its validate method, and validates any large literals using
``validate_large_literals``.

**fill_defaults:** Inserts attributes missing with the default value

**remove_defaults:** Where the tree has attributes with value equal to the
default, strip the attribute.

**check_schema:** Checks schema against the metaschema.

---------------

**Illustration of the where these are called:**

``af._open_asdf`` calls ``af.validate`` which calls ``af._validate`` which then
calls  ``schema.validate`` with the tagged tree as the first argument (it can be
called again if there is a custom schema).

**in sSchema.py**

``validate -> get_validator -> _create_validator`` (returns ``ASDFValidator``).
There are two levels of validation, those passed to the json_validation
machinery for the  schemas themselves, and those that the tag machinery triggers
whenthe jsonschema validator calls through ``iter_errors``. The first level
handles all the tricks at the top. the ``ASDFValidator`` uses ``load_schema``
which in turn calls ``_make_schema_loader``, then ``_load_schema``.
``_load_schema`` uses the ``OrderedLoader`` to load the schemas.

Got that?
