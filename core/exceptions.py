from rest_framework.views import exception_handler
from rest_framework.exceptions import (
    APIException, ValidationError, NotAuthenticated,
    PermissionDenied, NotFound, ParseError
)
from rest_framework.response import Response
from rest_framework import status
from django.db import IntegrityError, DatabaseError
import uuid

def _fmt(code: str, message: str, status_code: int, details=None, ref=None):
    return {"code": code, "message": message, "details": details or {}, "ref": ref}

class AppAPIException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "app_error"
    default_detail = "Application error"

    def __init__(self, message="Application error", code="app_error", status_code=None, details=None):
        super().__init__(message)
        self.code = code
        self.details_payload = details or {}
        if status_code:
            self.status_code = status_code

def custom_exception_handler(exc, context):
    ref = str(uuid.uuid4())[:8]
    # Пусть DRF сначала даст стандартный Response (если знает)
    resp = exception_handler(exc, context)

    # Наши кастомные
    if isinstance(exc, AppAPIException):
        payload = _fmt(getattr(exc, "code", "app_error"), str(exc.detail),
                       getattr(exc, "status_code", 400), exc.details_payload, ref)
        return Response(payload, status=getattr(exc, "status_code", 400))

    if resp is not None:
        sc = resp.status_code
        if isinstance(exc, ValidationError):
            payload = _fmt("validation_error", "Данные не прошли валидацию", sc, exc.detail, ref)
        elif isinstance(exc, NotAuthenticated):
            payload = _fmt("not_authenticated", "Требуется аутентификация", sc, {}, ref)
        elif isinstance(exc, PermissionDenied):
            payload = _fmt("permission_denied", "Доступ запрещён", sc, {}, ref)
        elif isinstance(exc, NotFound):
            payload = _fmt("not_found", "Ресурс не найден", sc, {}, ref)
        elif isinstance(exc, ParseError):
            payload = _fmt("bad_request", "Некорректные данные запроса", sc, {}, ref)
        else:
            payload = _fmt("error", str(exc), sc, getattr(exc, "detail", {}), ref)
        resp.data = payload
        return resp