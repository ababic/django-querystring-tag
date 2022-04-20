from typing import Any, Union

from django.db.models import Model


def normalize_value(value: Any, model_value_field: str = 'pk') -> Union[str, None]:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, Model):
        return str(getattr(value, model_value_field))
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    return str(value)
