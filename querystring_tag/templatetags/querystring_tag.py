from typing import Any, Dict, List, Optional, Union

from django import template
from django.http.request import QueryDict
from django.template import TemplateSyntaxError
from django.template.base import FilterExpression, Node
from django.utils.safestring import mark_safe

from ..expressions import PARAM_MODIFIER_EXPRESSIONS, ParamModifierExpression
from ..parse_utils import extract_kwarg_groups, extract_param_names, normalize_bits
from ..utils import normalize_value

register = template.Library()


@register.tag()
def querystring(parser, token):
    """
    The {% querystring %} template tag. The responsibility of this function is
    really just to parse the options values, and pass things on to
    `QuerystringTagNode.from_bits()` , which does all of the heavy lifting.
    """

    # break token into individual key, operator and value strings
    bits = normalize_bits(token.split_contents())

    return QuerystringTagNode.from_bits(bits, parser)


class QuerystringTagNode(Node):
    @classmethod
    def from_bits(cls, bits: List[str], parser) -> "QuerystringTagNode":
        """
        Returns a ``QuerystringTagNode`` instance, initialised from
        the `bits` extracted from a specific usage of {% querystring %}
        in a template.
        """
        kwargs = cls.init_kwargs_from_bits(bits, parser)
        return cls(**kwargs)

    @classmethod
    def init_kwargs_from_bits(cls, bits: List[str], parser) -> dict:
        """
        Converts the `bits` extracted from a specific usage of {% querystring %}
        into a dict of keyword arguments that can be used to to create a
        ``QuerystringTagNode`` instance.
        """
        kwargs = {}

        # drop the initial "querystring" bit
        if bits and bits[0] == "querystring":
            bits.pop(0)

        if not bits:
            return kwargs

        # if the "as" keyword has been used to parameterize the result,
        # capture the target variable name and remove the items from `bits`.
        if "as" in bits:
            if len(bits) < 2 or bits[-2] != "as":
                raise TemplateSyntaxError(
                    "When using the 'as' option, it must be used at the end of tag, with "
                    "a single 'variable name' value included after the 'as' keyword."
                )
            kwargs["target_variable_name"] = bits[-1].strip("'").strip('"')
            bits = bits[:-2]

        # if the 'only' or 'discard' options are used, identify all of the
        # 'parameter name' arguments that follow it, and remove them from `bits`
        if bits and bits[0] in ("only", "discard"):
            params = tuple(extract_param_names(parser, bits[1:]))
            if bits[0] == "only":
                kwargs["only"] = params
            else:
                kwargs["discard"] = params
            start_index = len(params) + 1
            bits = bits[start_index:]

        # the remaining bits should be keyword arguments, so we group them
        # into (key, operator, value) tuples
        model_value_field = None
        param_modifier_groups = []
        for group in extract_kwarg_groups(parser, bits):
            # variabalize known option values
            if group[0].token == "remove_blank":
                kwargs["remove_blank"] = group[2]
            elif group[0].token == "remove_utm":
                kwargs["remove_utm"] = group[2]
            elif group[0].token == "source_data":
                kwargs["source_data"] = group[2]
            elif group[0].token == "model_value_field":
                model_value_field = group[2]
                kwargs["model_value_field"] = group[2]
            elif group[1] in PARAM_MODIFIER_EXPRESSIONS:
                # these will be dealt with below, once we have all option values
                param_modifier_groups.append(group)

        # convert special (key, operator, value) tuples to ParamModifierExpression
        # objects, which are capabile of modify the source QueryDict
        param_modifiers = []
        for group in param_modifier_groups:
            expression_class = PARAM_MODIFIER_EXPRESSIONS.get(group[1])
            param_modifiers.append(
                expression_class(
                    param_name=group[0],
                    value=group[2],
                    model_value_field=model_value_field,
                )
            )
        kwargs["param_modifiers"] = param_modifiers

        return kwargs

    def __init__(
        self,
        *,
        source_data: Optional[Union[str, Dict[str, Any], QueryDict]] = None,
        only: Optional[List[FilterExpression]] = None,
        discard: Optional[List[FilterExpression]] = None,
        param_modifiers: Optional[List[ParamModifierExpression]] = None,
        model_value_field: Optional[FilterExpression] = None,
        remove_blank: Union[bool, FilterExpression] = True,
        remove_utm: Union[bool, FilterExpression] = True,
        target_variable_name: Optional[str] = None,
    ):
        self.source_data = source_data
        # parameters for the 'only' or 'discard' options
        self.only = only or ()
        self.discard = discard or ()
        # modifiers
        self.param_modifiers = param_modifiers or ()
        # other options
        self.remove_blank = remove_blank
        self.remove_utm = remove_utm
        self.model_value_field = model_value_field
        # Set when 'as' is used to variabalize the value
        self.target_variable_name = target_variable_name

    def get_resolved_arguments(self, context):
        only = [var.resolve(context) for var in self.only]
        discard = [var.resolve(context) for var in self.discard]
        for item in self.param_modifiers:
            item.resolve(context)
        return only, discard, self.param_modifiers

    def get_base_querydict(self, context):
        if self.source_data is None:
            if "request" in context:
                return context["request"].GET.copy()
            return QueryDict("", mutable=True)
        try:
            source_data = self.source_data.resolve(context)
        except AttributeError:
            source_data = self.source_data
        if isinstance(source_data, QueryDict):
            return source_data.copy()
        if isinstance(source_data, dict):
            source = QueryDict("", mutable=True)
            if hasattr(self.model_value_field, "resolve"):
                model_value_field = self.model_value_field.resolve(context)
            else:
                model_value_field = None
            for key, value in source_data.items():
                if hasattr(value, "__iter__") and not isinstance(value, (str, bytes)):
                    source.setlist(
                        key,
                        (normalize_value(v, model_value_field) for v in value),
                    )
                else:
                    source.setlist(key, [normalize_value(value)])
            return source
        if isinstance(source_data, str):
            return QueryDict(source_data, mutable=True)
        # TODO: Fail more loudly when source_data value not supported
        return QueryDict("", mutable=True)

    @staticmethod
    def clean_querydict(
        querydict: QueryDict, remove_blank: bool = True, remove_utm: bool = True
    ) -> None:
        values_to_remove = {None}
        if remove_blank:
            values_to_remove.add("")

        for key, values in tuple(querydict.lists()):
            if remove_utm and key.lower().startswith("utm_"):
                del querydict[key]
                continue

            cleaned_values = [v for v in values if v not in values_to_remove]
            if cleaned_values:
                querydict.setlist(key, sorted(cleaned_values))
            else:
                del querydict[key]

    def get_querydict(self, context) -> QueryDict:
        querydict = self.get_base_querydict(context)
        only, discard, param_modifiers = self.get_resolved_arguments(context)

        if only:
            remove_keys = (k for k in tuple(querydict.keys()) if k not in only)
        elif discard:
            remove_keys = discard
        else:
            remove_keys = ()

        for key in remove_keys:
            try:
                del querydict[key]
            except KeyError:
                pass

        # Modify according to supplied kwargs
        for item in param_modifiers:
            item.apply(querydict)

        # Remove null/blank values and utm params
        remove_blank = self.remove_blank
        if hasattr(remove_blank, "resolve"):
            remove_blank = remove_blank.resolve(context)
        remove_utm = self.remove_utm
        if hasattr(remove_utm, "resolve"):
            remove_utm = remove_utm.resolve(context)
        self.clean_querydict(querydict, remove_blank, remove_utm)

        return querydict

    def get_querystring(self, context) -> str:
        querydict = self.get_querydict(context)
        return mark_safe("?" + querydict.urlencode())

    def render(self, context):
        output = self.get_querystring(context)
        if self.target_variable_name is not None:
            context[self.target_variable_name] = output
            return ""
        return output
