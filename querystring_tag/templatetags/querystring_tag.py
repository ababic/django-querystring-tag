import re
from typing import Iterable, List, Tuple

from django import template
from django.template import TemplateSyntaxError
from django.template.base import FilterExpression

from ..expressions import PARAM_MODIFIER_EXPRESSIONS, Operator
from ..nodes import QuerystringNode

register = template.Library()


# Regex pattern for recognising keyword arguments with '-=' and '+='
# operators in addition to the usual '='
KWARG_PATTERN = re.compile(
    r"(?P<key>[^-+=\s]+)\s*(?P<operator>\-=|\+=|=)\s*(?P<value>\S+)"
)


def normalize_bits(bits: List[str]) -> List[str]:
    """
    Further splits the list of strings returned by `token.split_contents()`
    into separate key, operator and value components without any surrounding
    white-space. This allows querystring_tag to better support varied spacing
    between option names and values. For example, these variations are all
    eqivalent to ["param", "+=", ""]:

    * param+=''
    * param += ''
    * param+= ''
    * param +=''
    """
    return_value = []

    for bit in bits:
        if bit in Operator.values:
            return_value.append(bit)
            continue

        match = KWARG_PATTERN.match(bit)
        if match:
            return_value.extend(
                [match.group("key"), match.group("operator"), match.group("value")]
            )
            continue

        separated_from_operator = False
        for operator in Operator.values:
            operator_length = len(operator)
            if bit.startswith(operator):
                return_value.extend((operator, bit[operator_length:]))
                separated_from_operator = True
                break
            elif bit.endswith(operator):
                return_value.extend((bit[:-operator_length], operator))
                separated_from_operator = True
                break

        if not separated_from_operator:
            return_value.append(bit)

    return return_value


def extract_param_names(parser, bits: List[str]) -> List[FilterExpression]:
    """
    Return a list of ``FilterExpression`` objects that represent the
    'param name' values following the 'only' or 'remove' opening keyword.
    """
    param_names = []
    for i, bit in enumerate(bits):

        if bit == "as" or bit in Operator.values:
            # param names have been exhausted
            return param_names

        try:
            next_bit = bits[i + 1]
            if next_bit in Operator.values:
                # param names have been exhausted
                return param_names
        except IndexError:
            pass

        param_names.append(parser.compile_filter(bit))

    return param_names


def extract_kwarg_groups(
    parser, bits
) -> Iterable[Tuple[FilterExpression, str, FilterExpression]]:
    """
    Returns tuples representing each of the key/operator/value
    triples used by developers in a {% querystring %} tag.
    """
    current_group = []
    for bit in bits:
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
    """
    The {% querystring %} template tag. The responsibility of this function is
    really just to parse the options values, and use them to create/return a
    `QuerystringNode` instance, which does all of the heavy lifting.
    """

    # defaults for QuerystringNode.__init__()
    only = None
    discard = None
    target_variable_name = None
    remove_blank = True
    remove_utm = True
    source_data = None
    param_modifiers = []

    # break token into individual key, operator and value strings
    bits = normalize_bits(token.split_contents())

    # drop the first "querystring" bit
    bits.pop(0)

    # if the "as" keyword has been used to parameterize the result,
    # capture the target variable name and remove the items from `bits`.
    if "as" in bits:
        if bits[-2] != "as":
            raise TemplateSyntaxError(
                "When using the 'as' option, it must be used at the end of tag, with "
                "a single 'variable name' value included after the 'as' keyword."
            )
        target_variable_name = bits[-1]
        bits = bits[:-2]

    # if the 'only' or 'discard' options are used, identify all of the
    # 'parameter name' arguments that follow it, and remove them from `bits`
    if bits[0] in ("only", "discard"):
        params = extract_param_names(parser, bits[1:])
        if bits[0] == "only":
            only = params
        else:
            discard = params
        start_index = len(params) + 1
        bits = bits[start_index:]

    # the remaining bits should be keyword arguments, so we group them
    # into (key, operator, value) tuples
    model_value_field = None
    param_modifier_groups = []
    for group in extract_kwarg_groups(parser, bits):
        # variabalize known option values
        if group[0].token == "remove_blank":
            remove_blank = group[2]
        elif group[0].token == "remove_utm":
            remove_utm = group[2]
        elif group[0].token == "source_data":
            source_data = group[2]
        elif group[0].token == "model_value_field":
            model_value_field = group[2]
        elif group[1] in PARAM_MODIFIER_EXPRESSIONS:
            # these will be dealt with below, once we have all option values
            param_modifier_groups.append(group)

    # convert special (key, operator, value) tuples to ParamModifierExpression
    # objects, which are capabile of modify the source QueryDict
    for group in param_modifier_groups:
        expression_class = PARAM_MODIFIER_EXPRESSIONS.get(group[1])
        param_modifiers.append(
            expression_class(
                param_name=group[0], value=group[2], model_value_field=model_value_field
            )
        )

    return QuerystringNode(
        source_data=source_data,
        only=only,
        discard=discard,
        remove_blank=remove_blank,
        remove_utm=remove_utm,
        param_modifiers=param_modifiers,
        target_variable_name=target_variable_name,
    )
