from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from django.http.request import QueryDict
from django.template.base import FilterExpression, Node
from django.utils.safestring import mark_safe

if TYPE_CHECKING:
    from .expressions import ParamModifierExpression


class QuerystringNode(Node):
    def __init__(
        self,
        *,
        source_data: Optional[Union[str, Dict[str, Any], QueryDict]] = None,
        only: Optional[List[FilterExpression]] = None,
        discard: Optional[List[FilterExpression]] = None,
        param_modifiers: Optional[List["ParamModifierExpression"]] = None,
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
            return source_data.copy(mutable=True)
        if isinstance(source_data, dict):
            return QueryDict.fromkeys(source_data, mutable=True)
        if isinstance(source_data, str):
            return QueryDict(source_data, mutable=True)
        # TODO: Fail more loudly when source_data value not supported
        return QueryDict("", mutable=True)

    @staticmethod
    def remove_utm_params(querydict: QueryDict) -> None:
        for key in querydict.keys():
            if key.lower().startswith("utm_"):
                del querydict[key]

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
