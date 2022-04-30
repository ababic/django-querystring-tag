from typing import Union

from django.http.request import QueryDict
from django.template.base import FilterExpression, VariableDoesNotExist

from .constants import QueryParamOperator
from .utils import normalize_value


class ParamModifierExpression:
    """
    A special 'expression' designed to modify a `QueryDict` value, based
    on the 'param_name' and 'value' tokens supplied.

    NOTE: All of the values received by `__init__()` are `FilterExpression`
    objects, which need to be 'resolved' to get the actual values. This
    happens in the `resolve()` method.
    """

    operator = None

    __slots__ = (
        "param_name_expression",
        "value_expression",
        "model_value_field_expression",
        "param_name",
        "value",
        "model_value_field",
    )

    def __init__(
        self,
        param_name: FilterExpression,
        value: FilterExpression,
        model_value_field: Union[FilterExpression, None],
    ):
        self.param_name_expression = param_name
        self.value_expression = value
        self.model_value_field_expression = model_value_field

        # The following will be updated when resolve()
        # is called for the above FilterExpression objects
        self.param_name = None
        self.value = None
        self.model_value_field = None

    def resolve(self, context, ignore_failures: bool = False) -> None:
        self.resolve_model_value_field(context, ignore_failures)
        self.resolve_param_name(context, ignore_failures)
        self.resolve_value(context, ignore_failures)

    def resolve_param_name(self, context, ignore_failures: bool = False) -> None:
        """
        Sets the 'self.param_name' attribute value from
        `self.param_name_expression`.
        """
        expr = self.param_name_expression
        self.param_name = expr.resolve(context, ignore_failures) or expr.token

    def resolve_value(self, context, ignore_failures: bool = False) -> None:
        """
        Sets the `self.value` attribute value from `self.value_expression`.
        If not `None`, the value is normalized to a list of strings to match
        the value format of `QueryDict`.
        """
        expr = self.value_expression
        resolved = expr.resolve(context, ignore_failures)
        if resolved is None:
            return

        # Normalize non-null values to a lists of strings
        if hasattr(resolved, "__iter__") and not isinstance(resolved, (str, bytes)):
            self.value = [normalize_value(v, self.model_value_field) for v in resolved]
        else:
            self.value = [normalize_value(resolved, self.model_value_field)]

    def resolve_model_value_field(self, context, ignore_failures: bool = False) -> None:
        """
        Sets the `self.model_value_field` attribute value from
        `self.model_value_field_expression`.
        """
        expr = self.model_value_field_expression
        if not expr:
            return
        self.model_value_field = expr.resolve(context, ignore_failures)

    def apply(self, querydict: QueryDict) -> None:
        """
        Uses the resolved `self.param_name` and `self.value` values
        to modify the supplied QueryDict.
        """
        raise NotImplementedError


class SetValueExpression(ParamModifierExpression):
    operator = QueryParamOperator.SET

    def apply(self, querydict: QueryDict) -> None:
        if self.value is None:
            try:
                del querydict[self.param_name]
            except KeyError:
                pass
        else:
            querydict.setlist(self.param_name, self.value)


class AddValueExpression(ParamModifierExpression):
    operator = QueryParamOperator.ADD

    def apply(self, querydict: QueryDict) -> None:
        current_values = set(querydict.getlist(self.param_name, ()))
        for val in self.value:
            if val not in current_values:
                querydict.appendlist(self.param_name, val)


class RemoveValueExpression(ParamModifierExpression):
    operator = QueryParamOperator.REMOVE

    def apply(self, querydict: QueryDict) -> None:
        current_values = set(querydict.getlist(self.param_name, ()))
        querydict.setlist(
            self.param_name, [v for v in current_values if v not in self.value]
        )


PARAM_MODIFIER_EXPRESSIONS = {
    klass.operator: klass for klass in ParamModifierExpression.__subclasses__()
}
