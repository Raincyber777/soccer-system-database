"""
总路由：/api/auth 认证、/api/common 基础数据、/api 各业务资源、/api/portal 门户公开
media 由 Django 直接伺服（生产 DEBUG=False 也保留，中小流量够用；大流量再换 Nginx 静态）
"""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve as media_serve

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('api/auth/', include('apps.accounts.urls')),
    path('api/admin/', include('apps.accounts.admin_urls')),
    path('api/common/', include('apps.common.urls')),
    path('api/', include('apps.portal.urls')),
]

# 上传的图片/材料走 /media/ 访问（DEBUG 开关都伺服，演示规模无压力）
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', media_serve, {'document_root': settings.MEDIA_ROOT}),
]
