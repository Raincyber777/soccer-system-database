"""统一响应包装：所有接口输出 { code, message, data, trace_id, timestamp }，code=0 为成功"""
import json
import time
import uuid

from rest_framework.renderers import JSONRenderer


class EnvelopeRenderer(JSONRenderer):
    charset = 'utf-8'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get('response') if renderer_context else None
        # 异常响应已由 envelope_exception_handler 包装成信封，这里原样输出
        if response is not None and response.status_code >= 400:
            return super().render(data, accepted_media_type, renderer_context)
        # 204 等无响应体
        if response is not None and response.status_code == 204:
            return b''
        envelope = {
            'code': 0,
            'message': 'success',
            'data': data,
            'trace_id': uuid.uuid4().hex,
            'timestamp': int(time.time()),
        }
        return super().render(envelope, accepted_media_type, renderer_context)


def envelope_dict(data, code=0, message='success'):
    """在 serializer/view 里手动构造信封（登录等自定义视图用）"""
    return {
        'code': code,
        'message': message,
        'data': data,
        'trace_id': uuid.uuid4().hex,
        'timestamp': int(time.time()),
    }


def json_dumps(data) -> bytes:
    return json.dumps(data, ensure_ascii=False).encode('utf-8')
