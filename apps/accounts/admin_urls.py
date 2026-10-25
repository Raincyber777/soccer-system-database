"""管理端账号接口：/api/admin/users、/api/admin/audit-logs"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter(trailing_slash=True)
router.register('users', views.UserViewSet, basename='admin-user')
router.register('audit-logs', views.AuditLogViewSet, basename='admin-audit-log')

urlpatterns = [
    path('', include(router.urls)),
]
