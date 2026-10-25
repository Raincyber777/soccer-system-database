"""
总路由：/api/auth 认证、/api/common 基础数据、/api 各业务资源、/api/portal 门户公开
media 由 Django 在 DEBUG 下直接伺服（生产换 Nginx）
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('api/auth/', include('apps.accounts.urls')),
    path('api/admin/', include('apps.accounts.admin_urls')),
    path('api/common/', include('apps.common.urls')),
    path('api/', include('apps.portal.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
