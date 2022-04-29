from typing import Any, Union

from django.db.models import Model


def normalize_value(
    value: Any, model_value_field: Union[None, str] = None
) -> Union[str, None]:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, Model):
        if model_value_field:
            try:
                return str(getattr(value, model_value_field))
            except AttributeError:
                pass
        field_name = getattr(value, "querystring_value_field", "pk")
        return str(getattr(value, field_name))
    return str(value)
