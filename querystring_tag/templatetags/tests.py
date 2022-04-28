from django.template import Context, Template
from django.test import RequestFactory, SimpleTestCase


class TestQuerystringTag(SimpleTestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.request_factory = RequestFactory()

    @classmethod
    def render_tag(cls, tag_options: str) -> str:
        template = Template("{% querystring " + tag_options + " %}")

        request = cls.request_factory.get(
            "/", data={"foo": ["a", "b", "c"], "bar": [1, 2, 3], "baz": "single-value"}
        )

        context_data = {
            "request": request,
            "foo_parm_name": "foo",
            "bar_param_name": "bar",
            "baz_param_name": "baz",
            "new_param_name": "newparam",
            "one": 1,
            "two": 2,
            "three": 3,
            "four": 4,
            "letter_a": "a",
            "letter_b": "b",
            "letter_c": "c",
            "letter_d": "d",
        }
        return template.render(Context(context_data))

    def test_add_param_with_string(self):
        result = self.render_tag("newparam='new'")
        self.assertEqual(
            result, "?foo=a&foo=b&foo=c&bar=1&bar=2&bar=3&baz=single-value&newparam=new"
        )

    def test_add_param_with_key_variable_substitution(self):
        result = self.render_tag("new_param_name='new'")
        self.assertEqual(
            result, "?foo=a&foo=b&foo=c&bar=1&bar=2&bar=3&baz=single-value&newparam=new"
        )

    def test_add_param_with_value_variable_substitution(self):
        result = self.render_tag("newparam=two")
        self.assertEqual(
            result, "?foo=a&foo=b&foo=c&bar=1&bar=2&bar=3&baz=single-value&newparam=2"
        )

    def test_replace_with_string(self):
        result = self.render_tag("foo='foo'")
        self.assertEqual(result, "?foo=foo&bar=1&bar=2&bar=3&baz=single-value")

    def test_replace_with_unqouted_string(self):
        result = self.render_tag("foo=foo")
        self.assertEqual(result, "?foo=foo&bar=1&bar=2&bar=3&baz=single-value")

    def test_replace_with_key_variable_substitution(self):
        result = self.render_tag("foo_parm_name='foo'")
        self.assertEqual(result, "?foo=foo&bar=1&bar=2&bar=3&baz=single-value")

    def test_replace_with_value_variable_substitution(self):
        result = self.render_tag("foo=one")
        self.assertEqual(result, "?foo=1&bar=1&bar=2&bar=3&baz=single-value")

    def test_replace_with_key_and_value_variable_substitution(self):
        result = self.render_tag("foo_parm_name=one")
        self.assertEqual(result, "?foo=1&bar=1&bar=2&bar=3&baz=single-value")

    def test_add_with_string(self):
        result = self.render_tag("foo+='d'")
        self.assertEqual(
            result, "?foo=a&foo=b&foo=c&foo=d&bar=1&bar=2&bar=3&baz=single-value"
        )

    def test_add_with_key_variable_substitution(self):
        result = self.render_tag("foo_parm_name+='d'")
        self.assertEqual(
            result, "?foo=a&foo=b&foo=c&foo=d&bar=1&bar=2&bar=3&baz=single-value"
        )

    def test_add_with_value_variable_substitution(self):
        result = self.render_tag("foo+=letter_d")
        self.assertEqual(
            result, "?foo=a&foo=b&foo=c&foo=d&bar=1&bar=2&bar=3&baz=single-value"
        )

    def test_add_with_key_and_value_variable_substitution(self):
        result = self.render_tag("foo_parm_name+=letter_d")
        self.assertEqual(
            result, "?foo=a&foo=b&foo=c&foo=d&bar=1&bar=2&bar=3&baz=single-value"
        )

    def test_add_with_mixed_option_spacing(self):
        options = [
            # Do not use request.GET
            "source='?'"
            # add '1' to 'bar' (consistant whitespace)
            "bar += 1",
            # add '2' to 'bar' (no whitespace)
            "bar+='2'",
            # add '3' to 'bar' (whitespace on right side of operator only)
            "bar-= 3",
            # add '4' to 'bar' (whitespace on left side of operator only)
            "bar -='4'",
        ]
        result = self.render_tag(" ".join(options))
        self.assertEqual(result, "?bar=1&bar=2&bar=3&bar=4")

    def test_add_with_mixed_option_spacing_and_variable_substitution(self):
        options = [
            # Do not use request.GET
            "source='?bar=5'",
            # add '1' to 'bar' (consistant whitespace)
            "bar_param_name += one",
            # add '2' to 'bar' (no whitespace)
            "bar_param_name+=two",
            # add '3' to 'bar' (whitespace on right side of operator only)
            "bar_param_name-= three",
            # add '4' to 'bar' (whitespace on left side of operator only)
            "bar_param_name -=four",
        ]
        result = self.render_tag(" ".join(options))
        self.assertEqual(result, "?bar=1&bar=2&bar=3&bar=4&bar=5")

    def test_remove_with_string(self):
        result = self.render_tag("bar-='1'")
        self.assertEqual(
            result, "?foo=a&foo=b&foo=c&foo=d&bar=2&bar=3&baz=single-value"
        )

    def test_remove_with_key_variable_substitution(self):
        result = self.render_tag("bar_param_name-='1'")
        self.assertEqual(result, "?foo=a&foo=b&foo=c&bar=2&bar=3&baz=single-value")

    def test_remove_with_value_variable_substitution(self):
        result = self.render_tag("bar-=one")
        self.assertEqual(result, "?foo=a&foo=b&foo=c&bar=2&bar=3&baz=single-value")

    def test_remove_with_key_and_value_variable_substitution(self):
        result = self.render_tag("bar_param_name-=three")
        self.assertEqual(result, "?foo=a&foo=b&foo=c&bar=1&bar=2&baz=single-value")

    def test_remove_with_mixed_spacing(self):
        options = [
            # Override source
            "source='?foo=a&foo=b&foo=c&foo=d&foo=x'",
            # remove 'a' from 'foo' (consistant whitespace)
            "foo -= 'a'",
            # remove 'b' from 'foo' (no whitespace)
            "foo-='b'",
            # remove 'c' from 'foo' (whitespace on right side of operator only)
            "foo-= 'c'",
            # remove 'd' from 'foo' (whitespace on left side of operator only)
            "foo -='d'",
        ]
        result = self.render_tag(" ".join(options))
        self.assertEqual(result, "?foo=x")

    def test_remove_with_mixed_spacing_and_variable_substitution(self):
        options = [
            # Override source
            "source='?foo=a&foo=b&foo=c&foo=d&foo=x'",
            # remove 'a' from 'foo' (consistant whitespace)
            "foo_param_name -= letter_a",
            # remove 'b' from 'foo' (no whitespace)
            "foo_param_name-=letter_b",
            # remove 'c' from 'foo' (whitespace on right side of operator only)
            "foo_param_name-= letter_c",
            # remove 'd' from 'foo' (whitespace on left side of operator only)
            "foo_param_name -=letter_d",
        ]
        result = self.render_tag(" ".join(options))
        self.assertEqual(result, "?foo=x")

    def test_discard_with_strings(self):
        result = self.render_tag("discard 'foo' 'bar'")
        self.assertEqual(result, "?baz=single-value")

    def test_discard_with_params(self):
        result = self.render_tag("discard foo_parm_name bar_param_name")
        self.assertEqual(result, "?baz=single-value")

    def test_dicsard_with_additional_changes(self):
        result = self.render_tag("discard 'foo' 'bar' baz=letter_a newparam='new'")
        self.assertEqual(result, "?baz=a&newparam=new")

    def test_only_with_strings(self):
        result = self.render_tag("only 'foo' 'bar'")
        self.assertEqual(result, "?foo=a&foo=b&foo=c&bar=1&bar=2&bar=3")

    def test_only_with_params(self):
        result = self.render_tag("only foo_parm_name bar_param_name")
        self.assertEqual(result, "?foo=a&foo=b&foo=c&bar=1&bar=2&bar=3")

    def test_only_with_additional_changes(self):
        result = self.render_tag("only 'foo' 'bar' baz=letter_a newparam='new'")
        self.assertEqual(
            result, "?foo=a&foo=b&foo=c&bar=1&bar=2&bar=3&baz=a&newparam=new"
        )
