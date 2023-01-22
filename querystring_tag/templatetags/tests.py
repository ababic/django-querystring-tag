from datetime import date
from typing import Any, Dict, Optional, Union

from django.contrib.auth.models import User
from django.http.request import QueryDict
from django.template import Context, Template, TemplateSyntaxError
from django.test import RequestFactory, SimpleTestCase

# This is applied as GET data for requests created by render_tag()
REQUEST_GET = {"foo": ["a", "b", "c"], "bar": [1, 2, 3], "baz": "single-value"}

# When unmodified, the above GET data should produce this querystring
UNMODIFIED_QUERYSTRING = "?foo=a&foo=b&foo=c&bar=1&bar=2&bar=3&baz=single-value"


class TestQuerystringTag(SimpleTestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.request_factory = RequestFactory()

    @classmethod
    def render_tag(
        cls,
        *options: str,
        source: Union[str, Dict[str, Any], QueryDict] = None,
        add_to_template: Optional[str] = None,
        include_request_in_context: Optional[bool] = True,
    ) -> str:
        context_data = {
            "foo_param_name": "foo",
            "bar_param_name": "bar",
            "baz_param_name": "baz",
            "new_param_name": "newparam",
            "one": 1,
            "two": 2,
            "three": 3,
            "four": 4,
            "numbers": [1, 2, 3, 4],
            "start_of_year": date(2022, 1, 1),
            "letter_a": "a",
            "letter_b": "b",
            "letter_c": "c",
            "letter_d": "d",
            "letters": ["a", "b", "c", "d"],
            "user": User(pk=1, username="user-one"),
            "querydict": QueryDict("foo=1&foo=2&bar=baz", mutable=True),
            "dictionary": {"foo": ["1", "2"], "bar": "baz"},
        }
        if include_request_in_context:
            request = cls.request_factory.get("/", data=REQUEST_GET)
            context_data["request"] = request

        tag_options = " ".join(options)
        if source is not None:
            context_data["source"] = source
            tag_options += " source_data=source"

        template_string = "{% querystring " + tag_options + " %}"
        if add_to_template:
            template_string += add_to_template
        template = Template(template_string)

        return template.render(Context(context_data))

    def test_uses_request_get_as_data_source_by_default(self):
        result = self.render_tag()
        self.assertEqual(result, UNMODIFIED_QUERYSTRING)

    def test_creates_blank_data_source_if_request_is_unavailable(self):
        result = self.render_tag(include_request_in_context=False)
        self.assertEqual(result, "?")

    def test_as(self):
        """
        NOTE: This is a simple test with no modifications. Compatibility with
        'discard', 'only' and general modifications is covered by:
        - test_discard_with_modifications()
        - test_only_with_modifications()
        """
        options = "as some_var"

        # When 'as' is specified, the template tag alone should not render anything
        result = self.render_tag(options)
        self.assertEqual(result, "")

        # If we render the 'as' target variable to the template, we should see
        # the output
        result = self.render_tag(options, add_to_template="{{ some_var }}")
        self.assertEqual(result, UNMODIFIED_QUERYSTRING)

    def test_as_requires_target_variable_name(self):
        with self.assertRaises(TemplateSyntaxError):
            self.render_tag("as")

    def test_add_new_param_with_string(self):
        result = self.render_tag("newparam='new'")
        self.assertEqual(result, UNMODIFIED_QUERYSTRING + "&newparam=new")

    def test_add_new_param_with_key_variable_substitution(self):
        result = self.render_tag("new_param_name='new'")
        self.assertEqual(result, UNMODIFIED_QUERYSTRING + "&newparam=new")

    def test_add_new_param_with_value_variable_substitution(self):
        result = self.render_tag("newparam=two")
        self.assertEqual(result, UNMODIFIED_QUERYSTRING + "&newparam=2")

    def test_add_new_param_with_value_list(self):
        source = ""
        result = self.render_tag("foo=letters", source=source)
        self.assertEqual(result, "?foo=a&foo=b&foo=c&foo=d")

    def test_add_new_param_with_model_object(self):
        source = ""
        result = self.render_tag("foo=user", source=source)
        self.assertEqual(result, "?foo=1")

    def test_add_new_param_with_model_value_field(self):
        source = ""
        options = [
            "foo=user",
            "model_value_field='username'",
        ]
        result = self.render_tag(*options, source=source)
        self.assertEqual(result, "?foo=user-one")

    def test_add_new_param_with_non_existent_model_value_field_falls_back_to_pk(self):
        source = ""
        options = [
            "foo=user",
            "model_value_field='secret_key'",
        ]
        result = self.render_tag(*options, source=source)
        self.assertEqual(result, "?foo=1")

    def test_replace_with_string(self):
        result = self.render_tag("foo='foo'")
        self.assertEqual(result, "?foo=foo&bar=1&bar=2&bar=3&baz=single-value")

    def test_replace_with_key_variable_substitution(self):
        result = self.render_tag("foo_param_name='foo'")
        self.assertEqual(result, "?foo=foo&bar=1&bar=2&bar=3&baz=single-value")

    def test_replace_with_value_variable_substitution(self):
        result = self.render_tag("foo=one")
        self.assertEqual(result, "?foo=1&bar=1&bar=2&bar=3&baz=single-value")

    def test_replace_with_key_and_value_variable_substitution(self):
        result = self.render_tag("foo_param_name=one")
        self.assertEqual(result, "?foo=1&bar=1&bar=2&bar=3&baz=single-value")

    def test_replace_with_value_list(self):
        source = "foo=bar"
        result = self.render_tag("foo=letters", source=source)
        self.assertEqual(result, "?foo=a&foo=b&foo=c&foo=d")

    def test_replace_with_none_removes_parameter(self):
        result = self.render_tag("foo=None bar=None")
        self.assertEqual(result, "?baz=single-value")

    def test_add_with_string(self):
        result = self.render_tag("foo+='d'")
        self.assertEqual(
            result, "?foo=a&foo=b&foo=c&foo=d&bar=1&bar=2&bar=3&baz=single-value"
        )

    def test_add_with_key_variable_substitution(self):
        result = self.render_tag("foo_param_name+='d'")
        self.assertEqual(
            result, "?foo=a&foo=b&foo=c&foo=d&bar=1&bar=2&bar=3&baz=single-value"
        )

    def test_add_with_value_variable_substitution(self):
        result = self.render_tag("foo+=letter_d")
        self.assertEqual(
            result, "?foo=a&foo=b&foo=c&foo=d&bar=1&bar=2&bar=3&baz=single-value"
        )

    def test_add_with_date(self):
        source = "foo=bar"
        result = self.render_tag("foo+=start_of_year", source=source)
        self.assertEqual(result, "?foo=2022-01-01&foo=bar")

    def test_add_with_value_list(self):
        source = dict(foo=["x", "y", "z"])
        result = self.render_tag("foo+=letters", source=source)
        self.assertEqual(result, "?foo=a&foo=b&foo=c&foo=d&foo=x&foo=y&foo=z")

    def test_add_with_model_object(self):
        source = "bar=2"
        result = self.render_tag("bar+=user", source=source)
        self.assertEqual(result, "?bar=1&bar=2")

    def test_add_with_model_value_field(self):
        source = "foo=user-two"
        options = [
            "foo+=user",
            "model_value_field='username'",
        ]
        result = self.render_tag(*options, source=source)
        self.assertEqual(result, "?foo=user-one&foo=user-two")

    def test_add_with_non_existent_model_value_field_falls_back_to_pk(self):
        source = "foo=2"
        options = [
            "foo+=user",
            "model_value_field='secret_key'",
        ]
        result = self.render_tag(*options, source=source)
        self.assertEqual(result, "?foo=1&foo=2")

    def test_add_with_key_and_value_variable_substitution(self):
        result = self.render_tag("foo_param_name+=letter_d")
        self.assertEqual(
            result, "?foo=a&foo=b&foo=c&foo=d&bar=1&bar=2&bar=3&baz=single-value"
        )

    def test_add_with_mixed_option_spacing(self):
        source = ""
        options = [
            # add '1' to 'bar' (consistant whitespace)
            "bar += 1",
            # add '2' to 'bar' (no whitespace)
            "bar+='2'",
            # add '3' to 'bar' (whitespace on right side of operator only)
            "bar+= 3",
            # add '4' to 'bar' (whitespace on left side of operator only)
            "bar +='4'",
        ]
        result = self.render_tag(*options, source=source)
        self.assertEqual(result, "?bar=1&bar=2&bar=3&bar=4")

    def test_add_with_mixed_option_spacing_and_variable_substitution(self):
        source = "bar=5"
        options = [
            # add '1' to 'bar' (consistant whitespace)
            "bar_param_name += one",
            # add '2' to 'bar' (no whitespace)
            "bar_param_name+=two",
            # add '3' to 'bar' (whitespace on right side of operator only)
            "bar_param_name+= three",
            # add '4' to 'bar' (whitespace on left side of operator only)
            "bar_param_name +=four",
        ]
        result = self.render_tag(*options, source=source)
        self.assertEqual(result, "?bar=1&bar=2&bar=3&bar=4&bar=5")

    def test_remove_with_string(self):
        result = self.render_tag("bar-='1'")
        self.assertEqual(result, "?foo=a&foo=b&foo=c&bar=2&bar=3&baz=single-value")

    def test_remove_with_key_variable_substitution(self):
        result = self.render_tag("bar_param_name-='1'")
        self.assertEqual(result, "?foo=a&foo=b&foo=c&bar=2&bar=3&baz=single-value")

    def test_remove_with_value_variable_substitution(self):
        result = self.render_tag("bar-=one")
        self.assertEqual(result, "?foo=a&foo=b&foo=c&bar=2&bar=3&baz=single-value")

    def test_remove_with_value_list(self):
        source = dict(bar=[1, 2, 3, 8, 9, 10])
        result = self.render_tag("bar-=numbers", source=source)
        self.assertEqual(result, "?bar=10&bar=8&bar=9")

    def test_remove_with_date(self):
        source = dict(foo=["bar", "2022-01-01"])
        result = self.render_tag("foo-=start_of_year", source=source)
        self.assertEqual(result, "?foo=bar")

    def test_remove_with_model_object(self):
        source = dict(foo=[1, 2])
        result = self.render_tag("foo-=user", source=source)
        self.assertEqual(result, "?foo=2")

    def test_remove_with_model_value_field(self):
        source = {"foo": ["user-one", "user-two"]}
        options = [
            "foo-=user",
            "model_value_field='username'",
        ]
        result = self.render_tag(*options, source=source)
        self.assertEqual(result, "?foo=user-two")

    def test_remove_with_non_existent_model_value_field_falls_back_to_pk(self):
        source = {"foo": [1, 2]}
        options = [
            "foo-=user",
            "model_value_field='secret_key'",
        ]
        result = self.render_tag(*options, source=source)
        self.assertEqual(result, "?foo=2")

    def test_remove_with_key_and_value_variable_substitution(self):
        result = self.render_tag("bar_param_name-=three")
        self.assertEqual(result, "?foo=a&foo=b&foo=c&bar=1&bar=2&baz=single-value")

    def test_remove_with_mixed_spacing(self):
        source = {"foo": ["a", "b", "c", "d", "x"]}
        options = [
            # remove 'a' from 'foo' (consistant whitespace)
            "foo -= 'a'",
            # remove 'b' from 'foo' (no whitespace)
            "foo-='b'",
            # remove 'c' from 'foo' (whitespace on right side of operator only)
            "foo-= 'c'",
            # remove 'd' from 'foo' (whitespace on left side of operator only)
            "foo -='d'",
        ]
        result = self.render_tag(*options, source=source)
        self.assertEqual(result, "?foo=x")

    def test_remove_with_mixed_spacing_and_variable_substitution(self):
        source = {"foo": ["a", "b", "c", "d", "x"]}
        options = [
            # remove 'a' from 'foo' (consistant whitespace)
            "foo_param_name -= letter_a",
            # remove 'b' from 'foo' (no whitespace)
            "foo_param_name-=letter_b",
            # remove 'c' from 'foo' (whitespace on right side of operator only)
            "foo_param_name-= letter_c",
            # remove 'd' from 'foo' (whitespace on left side of operator only)
            "foo_param_name -=letter_d",
        ]
        result = self.render_tag(*options, source=source)
        self.assertEqual(result, "?foo=x")

    def test_discard_with_string_param_names(self):
        result = self.render_tag("discard 'foo' 'bar'")
        self.assertEqual(result, "?baz=single-value")

    def test_discard_with_variable_param_names(self):
        result = self.render_tag("discard foo_param_name bar_param_name")
        self.assertEqual(result, "?baz=single-value")

    def test_discard_with_missing_params(self):
        source = "foo=bar"
        result = self.render_tag("discard 'x' 'y'", source=source)
        self.assertEqual(result, "?foo=bar")

    def test_discard_with_modifications(self):
        options_without_as = "discard 'foo' bar_param_name baz=letter_a newparam='new'"
        options_with_as = options_without_as + " as qs"
        expected_querystring = "?baz=a&newparam=new"

        # Without 'as', the template tag should render the expected querystring
        self.assertEqual(self.render_tag(options_without_as), expected_querystring)

        # With 'as', the template tag alone should not render anything
        self.assertEqual(self.render_tag(options_with_as), "")

        # With the 'as' target variable rendered in the template,
        # we should see the output
        self.assertEqual(
            self.render_tag(options_with_as, add_to_template="{{ qs }}"),
            expected_querystring,
        )

    def test_only_with_string_param_names(self):
        result = self.render_tag("only 'foo' 'bar'")
        self.assertEqual(result, "?foo=a&foo=b&foo=c&bar=1&bar=2&bar=3")

    def test_only_with_variable_param_names(self):
        result = self.render_tag("only foo_param_name bar_param_name")
        self.assertEqual(result, "?foo=a&foo=b&foo=c&bar=1&bar=2&bar=3")

        result = self.render_tag("only 'foo' 'bar' baz=letter_a newparam='new'")
        self.assertEqual(
            result, "?foo=a&foo=b&foo=c&bar=1&bar=2&bar=3&baz=a&newparam=new"
        )

    def test_only_with_missing_params(self):
        source = "foo=bar"
        result = self.render_tag("only 'x' 'y'", source=source)
        self.assertEqual(result, "?")

    def test_only_with_modifications(self):
        options_without_as = "only 'foo' 'bar' baz=letter_a newparam='new'"
        options_with_as = options_without_as + " as qs"
        expected_result = "?foo=a&foo=b&foo=c&bar=1&bar=2&bar=3&baz=a&newparam=new"

        # Without 'as', the template tag should render the expected querystring
        self.assertEqual(self.render_tag(options_without_as), expected_result)

        # With 'as', the template tag alone should not render anything
        self.assertEqual(self.render_tag(options_with_as), "")

        # With the 'as' target variable rendered in the template,
        # we should see the output
        self.assertEqual(
            self.render_tag(options_with_as, add_to_template="{{ qs }}"),
            expected_result,
        )

    def test_with_querydict_source(self):
        source = QueryDict("foo=1&foo=2&bar=baz", mutable=True)
        result = self.render_tag("foo+=3 bar=None", source=source)
        self.assertEqual(result, "?foo=1&foo=2&foo=3")

    def test_with_unsuitable_source(self):
        source = ["lists", "are", "not", "supported"]
        result = self.render_tag("foo=1", source=source)
        self.assertEqual(result, "?foo=1")

    def test_remove_blank_default(self):
        source = {"foo": "", "bar": "", "baz": "not-empty"}
        result = self.render_tag(source=source)
        self.assertEqual(result, "?baz=not-empty")

    def test_remove_blank_true(self):
        source = {"foo": "", "bar": "", "baz": "not-empty"}
        result = self.render_tag("remove_blank=True", source=source)
        self.assertEqual(result, "?baz=not-empty")

    def test_remove_blank_false(self):
        source = {"foo": "", "bar": "", "baz": "not-empty"}
        result = self.render_tag("remove_blank=False", source=source)
        self.assertEqual(result, "?foo=&bar=&baz=not-empty")

    def test_remove_utm_default(self):
        source = dict(
            foo="bar", utm_source="email", utm_content="cta", utm_campaign="Test"
        )
        result = self.render_tag(source=source)
        self.assertEqual(result, "?foo=bar")

    def test_remove_utm_true(self):
        source = dict(
            foo="bar", utm_source="email", utm_content="cta", utm_campaign="Test"
        )
        result = self.render_tag("remove_utm=True", source=source)
        self.assertEqual(result, "?foo=bar")

    def test_remove_utm_false(self):
        source = dict(
            foo="bar", utm_source="email", utm_content="cta", utm_campaign="Test"
        )
        result = self.render_tag("remove_utm=False", source=source)
        self.assertEqual(
            result, "?foo=bar&utm_source=email&utm_content=cta&utm_campaign=Test"
        )
