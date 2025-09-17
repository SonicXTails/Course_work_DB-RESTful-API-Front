from django.db import connection, transaction
from rest_framework.exceptions import ValidationError, PermissionDenied, APIException

PG_CONFLICT_CODES = {"23505", "23503", "23514"}  # unique, fk, check
PG_APP_ERRORS = {"P2001", "P2002", "P2003"}     # твои кастомные RAISE ERRCODE

def call_proc(sql: str, params=None, fetchone=True):
    params = params or []
    try:
        with transaction.atomic():
            with connection.cursor() as cur:
                cur.execute(sql, params)
                if fetchone:
                    row = cur.fetchone()
                    return row[0] if row and len(row) == 1 else row
                return None
    except Exception as e:
        # аккуратный маппинг ошибок Postgres → DRF
        pgcode = getattr(e, "pgcode", None)
        message = getattr(getattr(e, "diag", None), "message_primary", None) or str(e)

        if pgcode in PG_APP_ERRORS or pgcode in PG_CONFLICT_CODES:
            raise ValidationError({"detail": message})
        if pgcode == "28000":
            raise PermissionDenied(message)
        raise APIException(message)