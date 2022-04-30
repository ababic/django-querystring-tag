import re
from typing import Iterable, List, Tuple

from django.template.base import FilterExpression

from .constants import QueryParamOperator

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
        if bit in QueryParamOperator.values:
            return_value.append(bit)
            continue

        match = KWARG_PATTERN.match(bit)
        if match:
            return_value.extend(
                [match.group("key"), match.group("operator"), match.group("value")]
            )
            continue

        separated_from_operator = False
        for operator in QueryParamOperator.values:
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


def extract_param_names(parser, bits: List[str]) -> Iterable[FilterExpression]:
    """
    Return ``FilterExpression`` objects that represent the 'parameter names'
    that following the opening 'only' or 'remove' keywords.
    """
    for i, bit in enumerate(bits):
        try:
            next_bit = bits[i + 1]
            if next_bit in QueryParamOperator.values:
                # param names are exhausted
                break
        except IndexError:
            pass

        yield parser.compile_filter(bit)


def extract_kwarg_groups(
    parser, bits: List[str]
) -> Iterable[Tuple[FilterExpression, str, FilterExpression]]:
    """
    Returns tuples representing each of the key/operator/value
    triples used by developers in a {% querystring %} tag.
    """
    current_group = []
    for i, bit in enumerate(bits):
        try:
            next_bit = bits[i + 1]
            if next_bit in QueryParamOperator.values:
                # this bit should be a new 'param name', so return
                # the current group and start a new one
                if current_group:
                    yield tuple(current_group)
                current_group.clear()
        except IndexError:
            pass

        if bit in QueryParamOperator.values:
            current_group.append(bit)
        else:
            current_group.append(parser.compile_filter(bit))

    if current_group:
        yield tuple(current_group)
