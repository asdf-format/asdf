{{ fullname | escape | underline}}
{%- set attributes = filter_ignored(fullname, attributes) %}
{%- set functions = filter_ignored(fullname, functions) %}
{%- set classes = filter_ignored(fullname, classes) %}
{%- set exceptions = filter_ignored(fullname, exceptions) %}
{%- set modules = filter_ignored(fullname, modules) %}

.. automodule:: {{ fullname }}

    {% block attributes %}
    {%- if attributes %}
    .. rubric:: {{ _('Module Attributes') }}

    .. autosummary::
        :toctree: ../api
    {% for item in attributes %}
        {{ item }}
    {%- endfor %}
    {% endif %}
    {%- endblock %}

    {%- block functions %}
    {%- if functions %}
    .. rubric:: {{ _('Functions') }}

    .. autosummary::
        :toctree: ../api
    {% for item in functions %}
        {{ item }}
    {%- endfor %}
    {% endif %}
    {%- endblock %}

    {%- block classes %}
    {%- if classes %}
    .. rubric:: {{ _('Classes') }}

    .. autosummary::
        :toctree: ../api
    {% for item in classes %}
        {{ item }}
    {%- endfor %}
    {% endif %}
    {%- endblock %}

    {%- block exceptions %}
    {%- if exceptions %}
    .. rubric:: {{ _('Exceptions') }}

    .. autosummary::
        :toctree: ../api
    {% for item in exceptions %}
        {{ item }}
    {%- endfor %}
    {% endif %}
    {%- endblock %}

{%- block modules %}
{%- if modules %}
.. rubric:: Modules

.. autosummary::
    :toctree:
    :recursive:
{% for item in modules %}
    {{ item }}
{%- endfor %}
{% endif %}
{%- endblock %}
