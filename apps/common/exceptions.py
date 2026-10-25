"""异常 → 统一业务码信封：HTTP 语义保留（401/403/404…），信封 code 按 §0.2 业务码映射"""
import time
import traceback
import uuid

from rest_framework import exceptions as drf_exceptions
from rest_framework.views import exception_handler


def _business_code(status: int) -> int:
    return {
        400: 40000,
        401: 20001,
        403: 40300,
        404: 40400,
        405: 40500,
        429: 42900,
    }.get(status, 50000)


def _flatten(detail):
    """把 DRF 校验错误（dict/list 嵌套）拍平成一条可读 message"""
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list):
        return '；'.join(str(_flatten(item)) for item in detail)
    if isinstance(detail, dict):
        parts = []
        for key, value in detail.items():
            text = str(_flatten(value))
            parts.append(f'{key}: {text}' if key != 'detail' else text)
        return '；'.join(parts)
    return str(detail)


def envelope_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        # 未捕获异常：打日志、返回 500 信封
        traceback.print_exc()
        response_data = {
            'code': 50000,
            'message': '服务器内部错误',
            'data': {'detail': str(exc)},
            'trace_id': uuid.uuid4().hex,
            'timestamp': int(time.time()),
        }
        from rest_framework.response import Response
        return Response(response_data, status=500)

    # 异常可带 business_code 属性覆盖默认映射（如登录失败 20002）
    code = getattr(exc, 'business_code', None) or _business_code(response.status_code)
    message = _flatten(response.data) or '请求失败'
    response.data = {
        'code': code,
        'message': message,
        'data': response.data,
        'trace_id': uuid.uuid4().hex,
        'timestamp': int(time.time()),
    }
    return response
