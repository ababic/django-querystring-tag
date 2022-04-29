from typing import Union

from django.db.models import TextChoices
from django.http.request import QueryDict
from django.template.base import FilterExpression, VariableDoesNotExist

from .utils import normalize_value


class Operator(TextChoices):
    ADD = "+=", "add"
    REMOVE = "-=", "remove"
    SET = "=", "set"


class ParamModifierExpression:
    """
    A special 'expression' designed to modify a `QueryDict` value, based
    on the 'param_name' and 'value' tokens supplied.

    NOTE: All of the values received by `__init__()` are `FilterExpression`
    objects, which need to be 'resolved' to get the actual values. This
    happens in the `resolve()` method.
    """

    operator = None

    def __init__(
        self,
        param_name: FilterExpression,
        value: FilterExpression,
        model_value_field: Union[FilterExpression, None],
    ):
        self.param_name_expression = param_name
        self.param_name = None
        self.value_expression = value
        self.values = None
        self.model_value_field_expression = model_value_field
        self.model_value_field = None

    def resolve(self, context, ignore_failures: bool = False) -> None:
        self.resolve_param_name(context, ignore_failures)
        self.resolve_value(context, ignore_failures)
        self.resolve_model_value_field(context, ignore_failures)

    def resolve_param_name(self, context, ignore_failures: bool = False) -> None:
        """
        Sets the 'self.param_name' attribute value from
        `self.param_name_expression`.
        """
        expression = self.param_name_expression
        if not expression:
            self.param_name = None
            return

        try:
            resolved = expression.resolve(context)
        except VariableDoesNotExist:
            if ignore_failures:
                resolved = None
            raise

        self.param_name = resolved or expression.token.strip("'").strip('"')

    def resolve_value(self, context, ignore_failures: bool = False) -> None:
        """
        Sets the `self.value` attribute value from `self.value_expression`.
        """
        expression = self.value_expression
        if not expression:
            return

        # If the token looks like a quoted string, return with quotes removed
        stripped = expression.token.strip("'").strip('"')
        if len(expression.token) - len(stripped) == 2:
            value = stripped
        else:
            try:
                value = expression.resolve(context)
            except VariableDoesNotExist:
                if "." not in expression.token and "|" not in expression.token:
                    value = expression.token
                if ignore_failures:
                    return
                raise

        # Normalize resolved value to a lists of strings
        if hasattr(value, "__iter__") and not isinstance(value, (str, bytes)):
            self.value = [normalize_value(v, self.model_value_field) for v in value]
        else:
            self.value = [normalize_value(value)]

    def resolve_model_value_field(self, context, ignore_failures: bool = False) -> None:
        """
        Sets the `self.model_value_field` attribute value from
        `self.model_value_field_expression`.
        """
        expression = self.model_value_field_expression
        if not expression:
            return

        self.model_value_field = expression.resolve(context, ignore_failures)

    def apply(self, querydict: QueryDict) -> None:
        """
        Uses the following resolved attribute values to modify the supplied QueryDict:
        * `self.param_name`
        * `self.value`
        * `self.model_value_field`
        """
        raise NotImplementedError


class SetValueExpression(ParamModifierExpression):
    operator = Operator.SET

    def apply(self, querydict: QueryDict) -> None:
        if self.value is None:
            try:
                del querydict[self.param_name]
            except KeyError:
                pass
        else:
            querydict.setlist(self.param_name, self.value)


class AddValueExpression(ParamModifierExpression):
    operator = Operator.ADD

    def apply(self, querydict: QueryDict) -> None:
        current_values = set(querydict.getlist(self.param_name, ()))
        for val in self.value:
            if val not in current_values:
                querydict.appendlist(self.param_name, val)


class RemoveValueExpression(ParamModifierExpression):
    operator = Operator.REMOVE

    def apply(self, querydict: QueryDict) -> None:
        current_values = set(querydict.getlist(self.param_name, ()))
        querydict.setlist(
            self.param_name, [v for v in current_values if v not in self.value]
        )


PARAM_MODIFIER_EXPRESSIONS = {
    klass.operator: klass for klass in ParamModifierExpression.__subclasses__()
}
