"""认证（登录/刷新/me/注册/改密）与用户账号管理"""
from django.contrib.auth import authenticate, get_user_model
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import APIException
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.common.permissions import IsAdminRole, IsStaffRole, IsStaffOrReadOnly, apply_region_scope

from .models import AuditLog, User, log_action
from .serializers import (
    ChangePasswordSerializer,
    RegisterSerializer,
    UserCreateSerializer,
    UserSerializer,
)

User = get_user_model()

ACCESS_LIFETIME_SECONDS = 2 * 60 * 60


class LoginFailed(APIException):
    """登录失败：业务码 20002（区别于未登录 20001）"""

    status_code = 401
    default_detail = '用户名或密码错误'
    business_code = 20002


class LoginView(APIView):
    """POST /api/auth/login/：账号密码换 JWT，统一入口按角色跳转三端"""

    permission_classes = [AllowAny]

    def post(self, request):
        username = (request.data.get('username') or '').strip()
        password = request.data.get('password') or ''
        user = authenticate(request, username=username, password=password)
        if user is None:
            raise LoginFailed('用户名或密码错误')
        if not user.is_active:
            raise LoginFailed('账号已被禁用')

        refresh = RefreshToken.for_user(user)
        data = {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'token_type': 'Bearer',
            'expires_in': ACCESS_LIFETIME_SECONDS,
            'user': UserSerializer(user).data,
        }
        return Response(data)


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """POST /api/auth/register/：自助注册（注册即返回 token，前端直接进入登录态）"""
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    refresh = RefreshToken.for_user(user)
    data = {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'token_type': 'Bearer',
        'expires_in': ACCESS_LIFETIME_SECONDS,
        'user': UserSerializer(user).data,
    }
    return Response(data, status=201)


@api_view(['GET', 'PATCH'])
def me(request):
    """GET /api/auth/me/：当前登录用户；PATCH：本人维护基础资料（仅安全字段，防越权改角色/归属）"""
    if request.method == 'GET':
        return Response(UserSerializer(request.user).data)
    allowed = {'real_name', 'phone', 'email', 'unit_name'}
    data = {k: v for k, v in request.data.items() if k in allowed}
    serializer = UserSerializer(request.user, data=data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    log_action(request, '更新了本人基础资料')
    return Response(UserSerializer(request.user).data)


@api_view(['PUT'])
def change_password(request):
    """PUT /api/auth/password/：本人修改密码"""
    serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
    serializer.is_valid(raise_exception=True)
    serializer.save()
    log_action(request, '修改了本人密码')
    return Response({'detail': '密码修改成功'})


class UserViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
                  mixins.UpdateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """用户账号管理：city 本区域 / admin 全省；删除仅 admin"""

    serializer_class = UserSerializer
    permission_classes = [IsStaffRole]

    def get_queryset(self):
        qs = User.objects.all().order_by('-date_joined')
        p = self.request.query_params
        if keyword := p.get('keyword'):
            qs = qs.filter(username__icontains=keyword) | qs.filter(real_name__icontains=keyword)
        if role := p.get('role'):
            qs = qs.filter(role=role)
        if status := p.get('status'):
            qs = qs.filter(is_active=status == 'active')
        return apply_region_scope(self.request.user, qs, field='region_code')

    def get_serializer_class(self):
        return UserCreateSerializer if self.action == 'create' else UserSerializer

    def perform_destroy(self, instance):
        if self.request.user.role != 'admin':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('删除账户仅省级管理员可执行')
        log_action(self.request, f'删除了账户 {instance.username}')
        instance.delete()

    def perform_update(self, serializer):
        instance = serializer.save()
        log_action(self.request, f'更新了账户 {instance.username} 的资料')

    def create(self, request, *args, **kwargs):
        """开户：写入用 UserCreateSerializer，响应用 UserSerializer（含 id 与 role_display）"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        log_action(request, f'创建了账户 {instance.username}')
        return Response(UserSerializer(instance).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='reset-password')
    def reset_password(self, request, pk=None):
        """重置密码为 123456（演示口径），返回提示"""
        user = self.get_object()
        user.set_password('123456')
        user.save()
        log_action(request, f'重置了账户 {user.username} 的密码')
        return Response({'detail': f'已重置 {user.username} 的密码为初始密码'})

    @action(detail=True, methods=['post'], url_path='toggle-active')
    def toggle_active(self, request, pk=None):
        """禁用 / 启用（可逆操作）"""
        user = self.get_object()
        user.is_active = not user.is_active
        user.save(update_fields=['is_active'])
        state = '启用' if user.is_active else '禁用'
        log_action(request, f'{state}了账户 {user.username}')
        return Response({'detail': f'已{state}账户 {user.username}', 'is_active': user.is_active})


class AuditLogViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """操作日志：管理端可查"""

    serializer_class = None
    permission_classes = [IsStaffRole]

    def get_queryset(self):
        return AuditLog.objects.all()

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        p = request.query_params
        if keyword := p.get('keyword'):
            qs = qs.filter(account__icontains=keyword) | qs.filter(action__icontains=keyword)
        if date_from := p.get('date_from'):
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to := p.get('date_to'):
            qs = qs.filter(created_at__date__lte=date_to)
        # city 只能看本区域账号产生的日志（简化：按操作人 region 过滤）
        if request.user.role == 'city':
            qs = qs.filter(user__region_code=request.user.region_code) | qs.filter(user__isnull=True)

        page = self.paginate_queryset(qs)
        items = [
            {
                'id': item.id,
                'account': item.account,
                'role': item.role,
                'action': item.action,
                'ip': item.ip,
                'created_at': item.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            }
            for item in page
        ]
        return self.get_paginated_response(items)
