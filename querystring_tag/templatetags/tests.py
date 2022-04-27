from unittest.mock import MagicMock, patch

from django.template import Context, Template
from django.test import RequestFactory, SimpleTestCase

request_factory = RequestFactory()


class TestTagOptionInterpretation(SimpleTestCase):
    def render_tag(self, tag_options: str) -> MagicMock:
        template = Template("{% querystring " + tag_options + " %}")

        request = request_factory.get(
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
            "letter_d": "c",
        }

        with patch(
            "querystring_tag.templatetags.querystring_tag.QuerystringNode.__init__",
            return_value="",
        ) as mocked_init:
            template.render(Context(context_data))
            return mocked_init

    def test_add_param_with_string(self):
        mocked_init = self.render_tag("newparam='new'")
        mocked_init.assert_called_once_with()

    def test_add_param_with_key_param(self):
        mocked_init = self.render_tag("new_param_name='new'")
        mocked_init.assert_called_once_with()

    def test_add_param_with_value_param(self):
        mocked_init = self.render_tag("newparam=two")
        mocked_init.assert_called_once_with()

    def test_replace_with_string(self):
        mocked_init = self.render_tag("foo='foo'")
        mocked_init.assert_called_once_with()

    def test_replace_with_key_param(self):
        mocked_init = self.render_tag("foo_parm_name='foo'")
        mocked_init.assert_called_once_with()

    def test_replace_with_value_param(self):
        mocked_init = self.render_tag("foo=one")
        mocked_init.assert_called_once_with()

    def test_replace_with_param_key_and_value(self):
        mocked_init = self.render_tag("foo_parm_name=one")
        mocked_init.assert_called_once_with()

    def test_add_with_strings(self):
        mocked_init = self.render_tag("foo+='d'")
        mocked_init.assert_called_once_with()

    def test_add_with_key_param(self):
        mocked_init = self.render_tag("foo_parm_name+='d'")
        mocked_init.assert_called_once_with()

    def test_add_with_value_param(self):
        mocked_init = self.render_tag("foo+=letter_d")
        mocked_init.assert_called_once_with()

    def test_add_with_param_key_and_value(self):
        mocked_init = self.render_tag("foo_parm_name+=letter_d")
        mocked_init.assert_called_once_with()

    def test_remove_with_strings(self):
        mocked_init = self.render_tag("bar-='1'")
        mocked_init.assert_called_once_with()

    def test_remove_with_key_param(self):
        mocked_init = self.render_tag("bar_parm_name-='1'")
        mocked_init.assert_called_once_with()

    def test_remove_with_value_param(self):
        mocked_init = self.render_tag("bar-=one")
        mocked_init.assert_called_once_with()

    def test_remove_with_param_key_and_value(self):
        mocked_init = self.render_tag("bar_parm_name-=one")
        mocked_init.assert_called_once_with()

    def test_discard_with_strings(self):
        mocked_init = self.render_tag("discard 'foo' 'bar'")
        mocked_init.assert_called_once_with()

    def test_discard_with_params(self):
        mocked_init = self.render_tag("discard foo_parm_name bar_param_name")
        mocked_init.assert_called_once_with()

    def test_dicsard_with_additional_changes(self):
        mocked_init = self.render_tag("discard 'foo' 'bar' baz=letter_a newparam='new'")
        mocked_init.assert_called_once_with()

    def test_only_with_strings(self):
        mocked_init = self.render_tag("only 'foo' 'bar'")
        mocked_init.assert_called_once_with()

    def test_only_with_params(self):
        mocked_init = self.render_tag("only foo_parm_name bar_param_name")
        mocked_init.assert_called_once_with()

    def test_only_with_additional_changes(self):
        mocked_init = self.render_tag("only 'foo' 'bar' baz=letter_a newparam='new'")
        mocked_init.assert_called_once_with()
