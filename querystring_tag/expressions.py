from django.db.models import TextChoices
from django.http.request import QueryDict
from django.template.base import FilterExpression, VariableDoesNotExist

from .utils import normalize_value


class Operator(TextChoices):
    ADD = "+=", "add"
    REMOVE = "-=", "remove"
    SET = "=", "set"


class ParamModifierExpression:
    operator = None

    def __init__(
        self,
        param_name: FilterExpression,
        value: FilterExpression,
        model_value_field: str = "pk",
    ):
        self.param_name = param_name
        self.resolved_param_name = None
        self.value = value
        self.resolved_value = None
        self.model_value_field = model_value_field

    def resolve(self, context, ignore_failures: bool = False) -> None:
        self.resolved_param_name = self._resolve_expression(
            self.param_name, context, ignore_failures
        )
        value = self._resolve_expression(self.value, context, ignore_failures)

        if value is None:
            self.resolved_value = None
            return

        # Normalize value to a lists of strings
        if hasattr(value, "__iter__") and not isinstance(value, (str, bytes)):
            self.resolved_value = [
                normalize_value(v, self.model_value_field) for v in value
            ]
        else:
            self.resolved_value = [normalize_value(value)]

    @staticmethod
    def _resolve_expression(value, context, ignore_failures=False):
        if value is None or isinstance(value, str):
            return value

        token = value.token
        stripped = token.strip("'" + '"')
        if len(token) - len(stripped) == 2:
            # Assume this was a quoted string and return it unquoted
            return stripped

        try:
            return value.resolve(context)
        except VariableDoesNotExist:
            if "." not in token and "|" not in token:
                # Interpret as an unquoted string
                return stripped
            if ignore_failures:
                return None
            raise

    def apply(self, querydict: QueryDict) -> None:
        raise NotImplementedError


class AddValueExpression(ParamModifierExpression):
    operator = Operator.ADD

    def apply(self, querydict: QueryDict) -> None:
        param_name = self.resolved_param_name
        current_values = set(querydict.get_list(param_name, ()))
        for val in self.resolved_value:
            if val not in current_values:
                querydict.appendlist(param_name, val)


class RemoveValueExpression(ParamModifierExpression):
    operator = Operator.REMOVE

    def apply(self, querydict: QueryDict) -> None:
        param_name = self.resolved_param_name
        current_values = set(querydict.get_list(param_name, ()))
        querydict.setlist(
            param_name, [v for v in current_values if v not in self.resolved_value]
        )


class SetValueExpression(ParamModifierExpression):
    operator = Operator.SET

    def apply(self, querydict: QueryDict) -> None:
        param_name = self.resolved_param_name
        if self.resolved_value is None:
            try:
                del querydict[param_name]
            except KeyError:
                pass
        else:
            querydict.setlist(param_name, self.resolved_value)


PARAM_MODIFIER_EXPRESSIONS = {
    klass.operator: klass for klass in ParamModifierExpression.__subclasses__()
}
