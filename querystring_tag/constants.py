from django.db.models import TextChoices


class QueryParamOperator(TextChoices):
    ADD = "+=", "add"
    REMOVE = "-=", "remove"
    SET = "=", "set"
