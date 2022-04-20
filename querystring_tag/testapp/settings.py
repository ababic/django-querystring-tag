import os

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = (
    "querystring_tag",
    "querystring_tag.testapp",
)

ROOT_URLCONF = "querystring_tag.testapp.urls"
SECRET_KEY = "fake-key"

# Django i18n
TIME_ZONE = "Europe/London"
USE_TZ = True

# Don't redirect to HTTPS in tests
SECURE_SSL_REDIRECT = False

# By default, Django uses a computationally difficult algorithm for passwords hashing.
# We don't need such a strong algorithm in tests, so use MD5
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
