from django import template

from ..nodes import QuerystringNode
from ..parse_utils import normalize_bits

register = template.Library()


@register.tag()
def querystring(parser, token):
    """
    The {% querystring %} template tag. The responsibility of this function is
    really just to parse the options values, and pass things on to
    `QuerystringNode.from_bits()` , which does all of the heavy lifting.
    """

    # break token into individual key, operator and value strings
    bits = normalize_bits(token.split_contents())

    return QuerystringNode.from_bits(bits, parser)
