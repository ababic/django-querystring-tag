from typing import Any, Dict, Iterable, Optional, Sequence, Tuple, Union

from django.db.models import TextChoices
from django.http.request import QueryDict
from django.template.base import FilterExpression, VariableDoesNotExist


from .utils import get_value_list


class Operator(TextChoices):
    ADD = "+=", "add"
    REMOVE = "-=", "remove"
    SET = "=", "set"


class ParamModifierExpression:
    operator = None

    def __init__(self, param_name: FilterExpression, value: FilterExpression):
        self.param_name = param_name
        self.resolved_param_name = None
        self.value = value
        self.resolved_value = None

    def _resolve_expression(value, context, ignore_failures=False):
        if value is None or isinstance(value, str):
            return value

        token = value.token
        if token.startswith("'") and "|" not in token:
            return token.strip("'")
        if token.startswith('"') and "|" not in token:
            return token.strip('"')

        try:
            value.resolve(context)
        except VariableDoesNotExist:
            if ignore_failures:
                return None
            raise

    def resolve(self, context, ignore_failures: bool = False) -> None:
        self.resolved_param_name = self._resolve_expression(
            self.param_name, context, ignore_failures
        )
        self.resolved_value = self._resolve_expression(
            self.value, context, ignore_failures
        )

    def apply(self, querydict: QueryDict) -> None:
        raise NotImplementedError


class AddValueExpression(ParamModifierExpression):
    operator = Operator.ADD

    def apply(self, querydict: QueryDict) -> None:
        param_name = self.resolved_param_name
        current_values = set(querydict.get_list(param_name, ()))
        for val in get_value_list(self.resolved_value):
            if val not in current_values:
                querydict.appendlist(param_name, val)


class RemoveValueExpression(ParamModifierExpression):
    operator = Operator.REMOVE

    def apply(self, querydict: QueryDict) -> None:
        param_name = self.resolved_param_name
        current_values = set(querydict.get_list(param_name, ()))
        values_to_remove = get_value_list(self.resolved_value)
        querydict.setlist(
            param_name, [v for v in current_values if v not in values_to_remove]
        )


class SetValueExpression(ParamModifierExpression):
    operator = Operator.SET

    def apply_to(self, querydict: QueryDict) -> None:
        param_name = self.resolved_param_name
        if self.resolved_value is None:
            try:
                del querydict[param_name]
            except KeyError:
                pass
        else:
            querydict.setlist(param_name, get_value_list(self.resolved_value))


PARAM_MODIFIER_EXPRESSIONS = {
    klass.operator: klass for klass in ParamModifierExpression.__subclasses__
}
