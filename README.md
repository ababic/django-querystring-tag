# django-querystring-tag

[![PyPi version](https://badgen.net/pypi/v/django-querystring-tag/)](https://pypi.org/project/django-querystring-tag/)
[![Test](https://github.com/ababic/django-querystring-tag/actions/workflows/test.yml/badge.svg?branch=master)](https://github.com/ababic/django-querystring-tag/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/ababic/django-querystring-tag/branch/master/graph/badge.svg?token=LDR7W1G2XC)](https://codecov.io/gh/ababic/django-querystring-tag)

This tiny package adds the `{% querystring %}` tag: A powerful, well tested template tag for modifying and rendering safe, suitably-encoded querystring values.

It's the clean and simple way to create pagination links, filters and other state-preserving links, without cluttering up your view code!

## Installation

1.  Install the package from pypi:

    **With Poetry**

    ```console
    $ poetry add django-querystring-tag
    ```

    **With pip**

    ```console
    $ pip install django-querystring-tag
    ```

2.  Add `"querystring_tag"` to the `INSTALLED_APPS` list in your Django project settings.

3.  Optional: To use the `{% querystring %}` tag freely, without having to `{% load %}` it into templates, add `"querystring_tag.templatetags.querystring_tag"` to the `['OPTIONS']['builtins']` list for your chosen template backend. [See an example](https://github.com/ababic/django-querystring-tag/blob/master/querystring_tag/testapp/settings.py#L36).

## How to use

Load the tag in the templates where you want to use it, by adding the following to the template (usually at the top):

```
{% load querystring_tag %}
```

You can then use the tag like this:

```
{% querystring param_one='value' param_two+='add-to-existing' param_three-="remove-from-existing" %}
```

### The basics

1. The tag uses `request.GET` as the data source by default. Check out the [`source_data`](#source_data) option if you have other ideas.
2. The examples below are deliberately simple: You can make as many modifications in the same tag as you need. GO CRAZY!
3. You may be wondering "I want to use this in an include template, where the parameter name is dynamic. Will that work?". **Yes it will!** I know it's unusual, but you can [use tempalate variables for parameter names](#using-template-variables-for-parameter-names) too.
4. You don't want to preserve Google tracking parameters in links, do you? I thought not. Any parameters starting with `utm_` are removed by default. See the [`remove_utm`](#remove_utm) option if you would rather keep them.
5. You're probably not interested in preserving blank parameters in links either, are you? See, I read your mind! Blank values removed by default too. See the [`remove_blank`](#remove_blank) option if you would rather keep them.
6. Want to variabalize the return value instead of rendering it? Go ahead any try the 'as' option. It works just as you would expect.

### Setting or replacing a parameter value

The most common requirement is to completely replace the value for a specific parameter. This is done using a regular keyword argument, with an `=` operator between the parameter name and value. For example:

```
{% querystring foo="bar" %}
```

### Removing values from a parameter value

When working with multi-value parameters, you may find yourself having to **remove** a specific value, without affecting any of the others.

In these situations, you can use the `-=` operator instead of the usual `=`. For example, if the current querystring looked something like this:

```
?q=test&bar=1&bar=2&bar=3
```

And you wanted to remove `&bar=2`, your querystring tag might look like this:

```
{% querystring bar-=2 %}
```

If the specified value isn't present, the instruction will simply be ignored.

### Adding values to a parameter value

When working with multi-value parameters, you may find yourself having to **add** a specific value for a parameter, without affecting any of the others.

In these situations, you can use the `+=` operator instead of the usual `=`. For example, if the current querystring looked something like this:

```
?q=test&bar=1&bar=2&bar=3
```

And you wanted to add `&bar=4`, your querystring tag might look like this:

```
{% querystring bar+=4 %}```
```

If the specified value is already present, the instruction will simply be ignored.

### Using template variables for parameter names

Unlike a lot of custom template tags, `{% querystring %}` supports the use of template variables in keys as well as values. For example, if the tag was being used to generate pagination links, and ``page_param_name`` and ``page_num`` were variables available in the template, you could use them both like so:

```
{% querystring page_param_name=page_num %}
```

### Supported value types

Values can be strings, booleans, integers, dates, datetimes, Django model instances, or iterables of either of these values.

When encountering a Django model instance, `{% querystring %}` will automatically take the `pk` value from it, and use that to modify the querystring. To use a different field value, you can use the tag's `model_value_field` option (see further down for details). Alternatively, you can add a `querystring_value_field` attribute to your model class. For example:

```python
class Category(models.Model):
    name = models.CharField(max_length=50)
    slug = models.SlugField(max_length=50, unique=True)

    # use 'slug' values in querystrings
    querystring_value_field = "slug"
```

### Specifying multiple values

As mentioned above, you can provide an iterable as a value to specify multiple values for a parameter at once. That could be a native Python type, such as a `list`, `tuple` or `set`, but could also be anything that implements the `__iter__` method to support iteration, for example, a `QuerySet`.

For example, if the context contained a variable ``tag_list``, which was list of strings (```['tag1', 'tag2', 'tag3']```), you can include all
of those values by referencing the list value. For example:

```
{% querystring tags=tag_list %}
```

The output of the above would be:

```
"?tags=tag1&amp;tags=tag2&amp;tags=tag3"
```

### Options reference

#### `source_data`

**Supported value types**: `QueryDict`, `dict`, `str`

**Default value**: `request.GET`

The tag defaults to using ``request.GET`` as the data source for the querystring, but the `source_data` keyword argument can be used to specify use an alternative ``QueryDict``, ``dict`` or string value.

For example, say you were using a Django form to validate query data, and only want valid data to be included. You could use the Form's `cleaned_data` to generate a querystring instead:

```
{% load querystring_tag %}
{% querystring source_data=form.cleaned_data page=2 %}
```

#### `remove_blank`

**Supported value types**: `bool`

**Default value**: `True`

Any parameter values with a value of `None` or `""` (an empty string) are removed from the querystring default.

To retain blank values, include `remove_blank=False` in your `{% querystring %}` tag.

#### `remove_utm`

**Supported value types**: `bool`

**Default value**: `True`

Parameter names starting with `"utm_"` (the format used for Google Analytics tracking parameters) are exluded from the generated querystrings by default, as it's unlikley that you'll want these to be repeated in links to other pages.

To retain these parameters instead, include `remove_utm=False` in your `{% querystring %}` tag.

#### `model_value_field`

**Supported value types**: `str`

**Default value**: `"pk"`

By default, when encountering a Django model instance as a value, `{% querystring %}` will take the `pk` value from the instance to use in the querystring. If you'd like to use a different field value, you can use the `model_value_field` option to specify an alternative field.

For example, if the model had a `slug` field that you were using as the public-facing identifier, you could specify that `slug` values be used in the querystring, like so:

```
{% querystring tags=tag_queryset model_field_value='slug' %}
```

#### `only`

Use this option at the start of your `{% querystring %}` tag when you only want the querystring to include values for specific parameters.

For example, say the current querystring looked like this:

```
?q=keywords&group=articles&category=2&published_after=2022-01-01
```

And you wanted to render a querystring containing only the `q` and `group` params. You could use `only` to achieve this:

```
{% load querystring_tag %}
{% querystring only 'q' 'group' %}
```

The resulting string would be:

```
?q=keywords&group=articles
```

NOTE: `only` is compatible with every other option except for `discard`. It can even be combined with any number of modifying keyword arguments; Just remember to keep the `only` keyword and related field names as the left-most parameters.

#### `discard`

Use this option at the start of your `{% querystring %}` tag when you want exclude specific parameter values from the querystring.

For example, say the current querystring looked like this:

```
?q=keywords&group=articles&category=2&published_after=2022-01-01
```

And you wanted to preserve everything except for `group` `published_after` in the rendered querystring. You could use `discard` to achieve this:

```
{% load querystring_tag %}
{% querystring discard 'group' 'published_after' %}
```

NOTE: `discard` is compatible with every other option except for `only`. It can even be combined with any number of modifying keyword arguments; Just remember to keep the `discard` keyword and related field names as the left-most parameters.

## Testing the code locally

If you have a recent version of Python 3 installed, you can use a simple virtualenv to run tests locally. After cloning the repository, navigate to the project's root directory on your machine, then run the following:

### To create the virtualenv

```console
$ virtualenv venv
$ source venv/bin/activate
$ pip install -e '.[test]' -U
$ deactivate
```

### To run tests

```console
$ source venv/bin/activate
$ pytest
$ deactivate
```
