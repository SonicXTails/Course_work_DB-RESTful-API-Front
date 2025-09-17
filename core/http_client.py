from rest_framework.views import exception_handler
from psycopg2.errors import RaiseException

MAP = {
  'CAR_NOT_AVAILABLE': (409, 'Авто недоступно'),
  'ORDER_INVALID_STATE': (409, 'Недопустимое состояние заказа'),
  'ORDER_NOT_FOUND': (404, 'Заказ не найден'),
}

def custom_exception_handler(exc, context):
    resp = exception_handler(exc, context)
    if resp is not None:
        return resp
    # psycopg2 RaiseException → читаемый ответ
    if isinstance(getattr(exc, 'orig', None), RaiseException) or isinstance(exc, RaiseException):
        msg = str(exc)
        for code, (status, text) in MAP.items():
            if code in msg:
                from rest_framework.response import Response
                return Response({'code': code, 'message': text}, status=status)
    return None