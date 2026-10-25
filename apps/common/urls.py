from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter(trailing_slash=True)
router.register('regions', views.RegionViewSet, basename='region')
router.register('schools', views.SchoolViewSet, basename='school')
router.register('dicts', views.DictItemViewSet, basename='dict')
router.register('configs', views.SystemConfigViewSet, basename='config')

urlpatterns = [
    path('', include(router.urls)),
    path('upload/', views.upload_file, name='upload'),
]
