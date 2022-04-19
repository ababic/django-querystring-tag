import re
from typing import Iterable, List, Tuple

from django import template
from django.template.base import FilterExpression

from ..expressions import PARAM_MODIFIER_EXPRESSIONS, Operator
from ..nodes import QuerystringNode

register = template.Library()


# Regex pattern for recognising keyword arguments with '-=' and '+='
# operators in addition to the usual '='
KWARG_PATTERN = re.compile(r"(?P<key>\S+)(?P<operator>\-=|\+=|=)(?P<value>\S+)")


def extract_param_names(parser, bits: List[str]) -> List[FilterExpression]:
    """
    Return a list of ``FilterExpression`` objects that represent the
    'param name' values following and 'only' or 'remove' opening
    keyword.
    """
    param_names = []
    for bit in bits:
        if bit == "as":
            return param_names
        for operator in Operator.values():
            if operator in bit:
                return param_names
        param_names.append(parser.compile_filter(bit))
    return param_names


def expand_bits(bits: List[str]) -> List[str]:
    """
    Further splits keyword arguments strings returned by `token.split_contents()`
    into separate key, operator and value components.
    """
    bits_expanded = []
    for bit in bits:
        if match := KWARG_PATTERN.match(bit):
            bits_expanded.extend(
                [match.group("key"), match.group("operator"), match.group("value")]
            )
        else:
            bits_expanded.append(bit)
    return bits_expanded


def extract_kwarg_groups(
    parser, bits
) -> Iterable[Tuple[FilterExpression, str, FilterExpression]]:
    """
    Returns tuples representing each of the key/operator/value
    triples used by developers in a {% querystring %} tag.
    """
    current_group = []
    for bit in expand_bits(bits):
        if bit == "as":
            if current_group:
                yield tuple(current_group)
            break
        if bit in Operator.values():
            key = current_group.pop()
            if current_group:
                yield tuple(current_group)
            current_group = [key, bit]
        else:
            current_group.append(parser.compile_filter(bit))
    if current_group:
        yield tuple(current_group)


@register.tag()
def querystring(parser, token):
    """
    Renders a URL and IRI encoded querystring (e.g. "q=Hello%20World&amp;category=1") that is safe to include in links.
    The querystring for the current request (``request.GET``) is used as a base by default, or an alternative
    ``QueryDict``, ``dict`` or querystring value can be provided as the first argument. The base value can be modified
    by providing any number of additional key/value pairs. ``None`` values are discounted automatically, and blank
    values can be optionally discounted by specifying ``remove_blank=True``.

    When specifying key/value pairs, any keys that do not already exist in the base value will be added, and those
    that do will have their value replaced. Specifying a value of ``None`` for an existing item will result in it being
    discounted. For example, if the querystring for the current request were "foo=ORIGINALFOOVAL&bar=ORIGINALBARVAL",
    but you wanted to:

    * Change the value of "foo" to "NEWFOOVAL"
    * Remove "bar"
    * Add a new "baz" item with the value `1`

    You could do so using the following:

    .. code::
        {% load querystring_tag %}
        {% querystring foo="NEWFOOVAL" bar=None baz=1 %}```

    The output of the above would be "?foo=NEWFOOVAL&amp;baz=1".

    Values can be strings, booleans, integers, dates, datetimes, model
    instances, and both values AND keys can be template variables.

    For example, if the tag was being used to generate pagination links, and
    ``page_param_name`` and ``page_num`` were variables available in the
    template, you could use them both like so:

    .. code::
        {% load querystring_tag %}
        {% querystring page_param_name=page_num %}

    You can specify more than one value for a key by providing an iterable as a value. For example, if the context
    contained a variable ``tag_list``, which was list of 'tag' values (```['tag1', 'tag2', 'tag3']```), you include all
    of those values by referencing the list value. For example:

    .. code::
        {% load querystring_tag %}
        {% querystring tags=tag_list %}

    The output of the above would be "?tags=tag1&amp;tags=tag2&amp;tags=tag3" (plus whatever other values were in the
    base value).

    And finally, if you want to modify the existing parameter value(s) instead of replacing
    them completely, you can use the '+=' operator to add values, or '-=' to
    remove them.

    For example, if the querystring was "tags=tag1&amp;tags=tag2&amp;tags=tag3", and you wanted to remove 'tag2', you
    could do:

    .. core::
        {% load querystring_tag %}
        {% querystring tags-='tag2' %}

    Which would output: "?tags=tag1&amp;tags=tag3"

    Or, if you wanted to add a new 'tagNew' value to that same parameter, you could do:

    .. code::
        {% load querystring_tag %}
        {% querystring tags+='tagNew' %}

    Which would output: "?tags=tag1&amp;tags=tag2&amp;tags=tag3&amp;tags=tagNew"

    You can add as many modifiers to the same tag as you need to, with any
    combination of modifiers at once. For example, the following is perfectly valid:

    .. code::
        {% load querystring_tag %}
        {% querystring page=None tags+="newTag" tags-="oldTag" %}

    Modifiers always fail gracefully if the value you're trying to add is already
    present, or a value you're trying to remove is not, or the named parameter isn't
    present at all.
    """

    bits = token.split_contents()
    only = None
    remove = None

    if bits[1] in ("only", "remove"):
        params = extract_param_names(parser, bits[2:])
        if bits[1] == "only":
            only = params
        else:
            remove = params
        bits = bits[len(params) + 2 :]

    target_var = None
    if len(bits >= 2) and bits[-2] == "as":
        target_var = bits[-1]
        bits = bits[:-2]

    remove_blank = True
    remove_utm = True
    source_data = None
    param_modifiers = []

    for group in extract_kwarg_groups(parser, bits):
        if group[0] == "remove_blank":
            remove_blank = group[2]
        elif group[0] == "remove_utm":
            remove_utm = group[2]
        elif group[0] == "source_data":
            source_data = group[2]
        else:
            klass = PARAM_MODIFIER_EXPRESSIONS.get(group[1])
            param_modifiers.append(klass(group[0], group[2]))

    return QuerystringNode(
        source_data=source_data,
        only=only,
        remove=remove,
        remove_blank=remove_blank,
        remove_utm=remove_utm,
        param_modifiers=param_modifiers,
        target_var=target_var,
    )
