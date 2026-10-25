from django.contrib import admin

from .models import DictItem, Region, School, SystemConfig

# Django 后台（/django-admin/）：基础数据可视化维护

@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'parent_code')
    search_fields = ('code', 'name')


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'city_code', 'district_name', 'stage', 'is_active')
    list_filter = ('stage', 'is_active')
    search_fields = ('code', 'name')


@admin.register(DictItem)
class DictItemAdmin(admin.ModelAdmin):
    list_display = ('dict_type', 'value', 'label', 'sort', 'is_active')
    list_filter = ('dict_type', 'is_active')
    search_fields = ('value', 'label')


@admin.register(SystemConfig)
class SystemConfigAdmin(admin.ModelAdmin):
    list_display = ('key', 'name', 'value', 'updated_at')
    search_fields = ('key', 'name')
