from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

ErrorSchema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["code", "message"],
    properties={
        "code": openapi.Schema(type=openapi.TYPE_STRING, example="validation_error"),
        "message": openapi.Schema(type=openapi.TYPE_STRING, example="Данные не прошли валидацию"),
        "details": openapi.Schema(type=openapi.TYPE_OBJECT, example={"field": ["обязательно"]}),
        "ref": openapi.Schema(type=openapi.TYPE_STRING, example="a1b2c3d4"),
    },
)

def with_errors(**kwargs):
    """Декоратор для автодобавления ошибок в Swagger."""
    base = {400: ErrorSchema, 401: ErrorSchema, 403: ErrorSchema, 404: ErrorSchema, 409: ErrorSchema, 500: ErrorSchema}
    responses = kwargs.pop("responses", {})
    merged = {**base, **responses}
    return swagger_auto_schema(responses=merged, **kwargs)