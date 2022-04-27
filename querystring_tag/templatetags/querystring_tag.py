import re
from typing import Iterable, List, Tuple

from django import template
from django.template.base import FilterExpression

from ..expressions import PARAM_MODIFIER_EXPRESSIONS, Operator
from ..nodes import QuerystringNode

register = template.Library()


# Regex pattern for recognising keyword arguments with '-=' and '+='
# operators in addition to the usual '='
KWARG_PATTERN = re.compile(
    r"(?P<key>[^-+=\s]+)\s*(?P<operator>\-=|\+=|=)\s*(?P<value>\S+)"
)


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
        for operator in Operator.values:
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
        if bit in Operator.values:
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
    bits = token.split_contents()
    only = None
    discard = None

    # the `querystring` string isn't needed for anything
    bits.pop(0)

    if bits[0] in ("only", "discard"):
        params = extract_param_names(parser, bits[1:])
        if bits[0] == "only":
            only = params
        else:
            discard = params
        start_index = len(params) + 1
        bits = bits[start_index:]

    target_var = None
    if len(bits) >= 2 and bits[-2] == "as":
        target_var = bits[-1]
        bits = bits[:-2]

    remove_blank = True
    remove_utm = True
    source_data = None
    model_value_field = "pk"
    param_modifiers = []

    for group in extract_kwarg_groups(parser, bits):
        if group[0] == "remove_blank":
            remove_blank = group[2]
        elif group[0] == "remove_utm":
            remove_utm = group[2]
        elif group[0] == "source_data":
            source_data = group[2]
        elif group[0] == "model_value_field":
            model_value_field = group[2]
        else:
            # Identify class based on the operator ('=' | '-=' | '+=')
            klass = PARAM_MODIFIER_EXPRESSIONS.get(group[1])
            # Initialize ParamModifierExpression object
            obj = klass(group[0], group[2], model_value_field)
            param_modifiers.append(obj)

    return QuerystringNode(
        source_data=source_data,
        only=only,
        discard=discard,
        remove_blank=remove_blank,
        remove_utm=remove_utm,
        param_modifiers=param_modifiers,
        target_var=target_var,
    )
