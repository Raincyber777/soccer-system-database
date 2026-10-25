"""公共基础数据接口 + 通用文件上传"""
import os
import time

from django.core.files.storage import default_storage
from rest_framework import mixins, viewsets
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import DictItem, Region, School, SystemConfig
from .permissions import IsAuthenticatedRole, IsStaffOrReadOnly
from .serializers import DictItemSerializer, RegionSerializer, SchoolSerializer, SystemConfigSerializer

# 允许上传的扩展名与大小上限
IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
DOC_EXTS = {'.xlsx', '.xls', '.zip', '.pdf', '.doc', '.docx'}
MAX_UPLOAD_SIZE = 20 * 1024 * 1024  # 20MB（照片包/学籍材料可能较大）


class RegionViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """行政区划：?parent_code=510100 取区县，不传取 21 市州（公开）"""

    queryset = Region.objects.all().order_by('code')
    serializer_class = RegionSerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_queryset(self):
        qs = super().get_queryset()
        parent_code = self.request.query_params.get('parent_code')
        if parent_code:
            return qs.filter(parent_code=parent_code)
        return qs.filter(parent_code__isnull=True)


class SchoolViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """学校库：?keyword=&city_code=&stage=（公开，前端 SchoolSelect 数据源）"""

    queryset = School.objects.all().order_by('code')
    serializer_class = SchoolSerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if keyword := p.get('keyword'):
            qs = qs.filter(name__icontains=keyword) | qs.filter(code__icontains=keyword)
        if city_code := p.get('city_code'):
            qs = qs.filter(city_code=city_code)
        if stage := p.get('stage'):
            qs = qs.filter(stage=stage)
        return qs


class DictItemViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """字典：?dict_type=cert_level"""

    queryset = DictItem.objects.filter(is_active=True)
    serializer_class = DictItemSerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_queryset(self):
        qs = super().get_queryset()
        dict_type = self.request.query_params.get('dict_type')
        return qs.filter(dict_type=dict_type) if dict_type else qs


class SystemConfigViewSet(mixins.ListModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """系统参数：读需登录，改仅省级管理员"""

    queryset = SystemConfig.objects.all().order_by('key')
    serializer_class = SystemConfigSerializer
    permission_classes = [IsStaffOrReadOnly]
    pagination_class = None


@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def upload_file(request):
    """通用文件上传（登录用户）：form-data file + scene（子目录用途）"""
    user = request.user
    if not user.is_authenticated:
        return Response({'detail': '请先登录'}, status=401)

    file = request.FILES.get('file')
    if not file:
        return Response({'detail': '缺少文件 file'}, status=400)
    if file.size > MAX_UPLOAD_SIZE:
        return Response({'detail': '文件超过 20MB 上限'}, status=400)

    ext = os.path.splitext(file.name)[1].lower()
    if ext not in IMAGE_EXTS | DOC_EXTS:
        return Response({'detail': f'不支持的文件类型 {ext}'}, status=400)

    scene = request.data.get('scene') or 'misc'
    # 防目录穿越：scene 只保留字母数字下划线中划线
    scene = ''.join(ch for ch in str(scene) if ch.isalnum() or ch in '_-') or 'misc'
    today = time.strftime('%Y/%m/%d')
    save_path = f'{scene}/{today}/{int(time.time() * 1000)}{ext}'
    saved = default_storage.save(save_path, file)

    return Response({
        'url': request.build_absolute_uri(f'/media/{saved}'),
        'path': f'/media/{saved}',
        'name': saved,
    })
