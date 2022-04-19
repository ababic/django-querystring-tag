from typing import Any, List, Union

from django.db.models import Model


def normalize_value(value: Any) -> Union[str, None]:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, Model):
        return str(value.pk)
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    return str(value)


def get_value_list(value: Any) -> List[Union[None, str]]:
    if hasattr(value, "__iter__") and not isinstance(value, (str, bytes)):
        return [normalize_value(v) for v in value]
    return [normalize_value(value)]
