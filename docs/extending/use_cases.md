# Common use cases

This section is intended as a kind of index to the rest of the
"Extending ASDF" documentation. Here we list common use cases and link
to the relevant documentation sections that are needed to get the job
done.

## Validate an ASDF tree against a schema

The [`asdf`][asdf] library already validates
individual tagged objects within the tree, but what if we want to
validate the structure of the tree itself? Such "document schemas" can
be associated with an [`AsdfFile`][asdf.AsdfFile]
using the `custom_schema` argument, but this argument accepts a URI and
the asdf library needs to know how to access the schema content
associated with that URI.

1.  Designate a URI for the schema. See
    `extending_uris_entities_schemas` for recommendations on schema URI
    structure.
2.  Write the schema. See `extending_schemas` if you're new to authoring
    schemas.
3.  Install the schema as an [`asdf`][asdf] library
    resource. See `extending_resources` for an overview of resources in
    [`asdf`][asdf] and options for installing them.

## Serialize a new type

This section summarizes the steps needed to serialize a new type to an
ASDF file. We'll describe three options, starting with the most
expedient and growing progressively more formal.

### Quick and dirty, for personal use

In this scenario, we want to serialize a new Python type to an ASDF
file, but we're not planning on widely sharing the file, so we want to
cut as many corners as possible. Here are the minimal steps needed to
get instances of that type into the file and back again:

1.  Identify the Python type to serialize. We'll need to know the
    fully-qualified name of the type (module path + class name).
2.  Select a tag URI that will signify the type in YAML. See
    `extending_uris_entities_tags` for recommendations on tag URI
    structure.
3.  Implement a [`Converter`][asdf.extension.Converter]
    class that converts the type to YAML-serializable objects and back
    again. See `extending_converters` for a discussion of the Converter
    interface.
4.  Implement an
    [`Extension`][asdf.extension.Extension] class which
    is the vehicle for plugging our converter into the asdf library. See
    `extending_extensions` for a discussion of the Extension interface.
5.  Install the extension. There are multiple ways to do this, but the
    path of least resistance is to install the extension at runtime
    using [`AsdfConfig`][asdf.config.AsdfConfig]. See
    `extending_extensions_installing_asdf_config`.

Now instances of our type can be added to an
[`AsdfFile`][asdf.AsdfFile]'s tree and serialized to
an ASDF file.

### For sharing with other Python users

Now say our files are getting out into the world and into the hands of
other Python users. We'll want to build an installable package around
our code and use the [`asdf`][asdf] library's entry
points to make our extension more convenient to use. We should also
think about adding a schema that validates our tagged objects, so if
someone manually edits a file and makes a mistake, we get a clear error
when [`asdf`][asdf] opens the file.

1.  Identify the Python type to serialize. We'll need to know the
    fully-qualified name of the type (module path + class name).
2.  Select a tag URI that will signify the type in YAML. See
    `extending_uris_entities_tags` for recommendations on tag URI
    structure.
3.  Designate a URI for the schema. See
    `extending_uris_entities_schemas` for recommendations on schema URI
    structure.
4.  Write the schema that will validate the tagged object. See
    `extending_schemas` if you're new to authoring schemas.
5.  Make the schema installable as an
    [`asdf`][asdf] library resource. See
    `extending_resources` for an overview of resources in
    [`asdf`][asdf] and
    `extending_resources_entry_points` for information on installing
    resources via an entry point.
6.  Implement a [`Converter`][asdf.extension.Converter]
    class that converts the type to YAML-serializable objects and back
    again. See `extending_converters` for a discussion of the Converter
    interface. Refer to the schema to ensure that the Converter is
    writing YAML objects correctly.
7.  Implement an
    [`Extension`][asdf.extension.Extension] class which
    is the vehicle for plugging our converter into the
    [`asdf`][asdf] library. See
    `extending_extensions` for a discussion of the Extension interface.
    We'll need to associate the schema URI with the tag URI in our tag's
    [`TagDefinition`][asdf.extension.TagDefinition] object.
8.  Install the extension via an entry point. See
    `extending_extensions_installing_entry_points`.

Now anyone who installs the package containing the entry points will be
able to read, write, and validate ASDF files containing our new tag!

### For sharing with users of other languages

Finally, let's consider the case where we want to serialize instances of
our type to an ASDF file that will be read using ASDF libraries written
in other languages. The problem with our previous efforts is that the
extension definition exists only as Python code, so here we'll want to
create an additional YAML document called an extension manifest that
defines the extension in a language-independent way.

1.  Identify the Python type to serialize. We'll need to know the
    fully-qualified name of the type (module path + class name).
2.  Select a tag URI that will signify the type in YAML. See
    `extending_uris_entities_tags` for recommendations on tag URI
    structure.
3.  Designate a URI for the schema. See
    `extending_uris_entities_schemas` for recommendations on schema URI
    structure.
4.  Write the schema that will validate the tagged object. See
    `extending_schemas` if you're new to authoring schemas.
5.  Write an extension manifest document that describes the tag and
    schema that we're including in our extension. See
    `extending_manifests` for information on the manifest format.
6.  Make the schema and manifest installable as
    [`asdf`][asdf] library resources. See
    `extending_resources` for an overview of resources in
    [`asdf`][asdf] and
    `extending_resources_entry_points` for information on installing
    resources via an entry point.
7.  Implement a [`Converter`][asdf.extension.Converter]
    class that converts the type to YAML-serializable objects and back
    again. See `extending_converters` for a discussion of the Converter
    interface. Refer to the schema to ensure that the Converter is
    writing YAML objects correctly.
8.  Use
    [`asdf.extension.ManifestExtension.from_uri`][asdf.extension.ManifestExtension.from_uri]
    to populate an extension with the Converter and information from the
    manifest document. See `extending_extensions_manifest` for
    instructions on using ManifestExtension.
9.  Install the extension via an entry point. See
    `extending_extensions_installing_entry_points`.

That's it! Python users should experience the same convenience, but now
the manifest document is available as a reference for developers who
wish to implement support for reading our tagged objects in their
language of choice.

## Support a new block compressor

In order to support a new compression algorithm for ASDF binary blocks,
we need to implement the
[`Compressor`][asdf.extension.Compressor] interface and
install that in an extension.

1.  Select a 4-byte compression code that will signify the compression
    algorithm.
2.  Implement a
    [`Compressor`][asdf.extension.Compressor] class that
    associates the 4-byte code with compression and decompression
    methods. See `extending_compressors` for a discussion of the
    Compressor interface.
3.  Implement an
    [`Extension`][asdf.extension.Extension] class which
    is the vehicle for plugging our compressor into the
    [`asdf`][asdf] library. See
    `extending_extensions` for a discussion of the Extension interface.
4.  Install the extension via one of the two available methods. See
    `extending_extensions_installing` for instructions.

Now the compression algorithm will be available for both reading and
writing ASDF files. Users writing files will simply need to specify the
new 4-byte compression code when making calls to
[`asdf.AsdfFile.set_array_compression`][asdf.AsdfFile.set_array_compression].

## Support a new schema property

In order to support custom validation behavior that is triggered by a
new schema property, we need to implement the
[`Validator`][asdf.extension.Validator] interface and
install that in an extension.

1.  Determine the tag or tags that this property will apply to.
2.  Select a schema property for the validator. The property need not be
    globally unique, but it should be unique among the validators that
    apply to the tag(s), and must not collide with any of the built-in
    JSON schema properties (type, additionalProperties, etc).
3.  Implement a [`Validator`][asdf.extension.Validator]
    class that associates the schema property and tag(s) with a
    `validate` method that does the work of checking an ADSF node
    against the schema.
4.  Implement an
    [`Extension`][asdf.extension.Extension] class which
    is the vehicle for plugging our validator into the
    [`asdf`][asdf] library. See
    `extending_extensions` for a discussion of the Extension interface.
5.  Install the extension via one of the two available methods. See
    `extending_extensions_installing` for instructions.

Now the new schema property will have an effect when validating ASDF
files.
