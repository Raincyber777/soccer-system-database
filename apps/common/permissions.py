"""权限类与数据域过滤 helper

角色语义（与前端三端对齐）：
- admin    省级最高管理员：全省数据、终审、账号管理
- province 省级内容发布（保留，暂无前端页面）
- city     市州管理员：按 region_code 隔离本区域
- school/athlete/coach：用户端三种身份
"""
from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdminRole(BasePermission):
    """仅省级最高管理员（admin）"""
    message = '仅省级管理员可执行该操作'

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == 'admin')


class IsStaffRole(BasePermission):
    """市州管理员（city）或省级管理员（admin）——管理端内容维护"""
    message = '仅管理员可执行该操作'

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role in ('admin', 'city'))


class IsStaffOrReadOnly(BasePermission):
    """公开读、管理端（city/admin）写"""
    message = '仅管理员可执行该操作'

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        return bool(user and user.is_authenticated and user.role in ('admin', 'city'))


class IsStaffOrTeamOwner(BasePermission):
    """公开读；city/admin 可写；school 可写本人球队相关资源（球队/球员/教练）"""

    message = '仅管理员或球队负责人可执行该操作'

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        return bool(user and user.is_authenticated and user.role in ('admin', 'city', 'school'))


class IsAuthenticatedRole(BasePermission):
    message = '请先登录'

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


def apply_region_scope(user, queryset, field='city_code'):
    """数据域过滤：city 只看本区域，admin/其他看全部（列表侧再按需收紧）"""
    if user.is_authenticated and user.role == 'city' and user.region_code:
        return queryset.filter(**{field: user.region_code})
    return queryset
