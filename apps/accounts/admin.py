from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import AuditLog, User

# 自定义用户模型：覆盖 fieldsets 把 role/region_code/unit_name 等扩展字段带进编辑表单


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'real_name', 'role', 'region_code', 'unit_name', 'phone',
                    'is_active', 'is_superuser')
    list_filter = ('role', 'is_active', 'is_superuser')
    search_fields = ('username', 'real_name', 'unit_name')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('个人信息', {'fields': ('real_name', 'role', 'region_code', 'unit_name', 'phone', 'email')}),
        ('权限', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('重要日期', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'real_name', 'role', 'region_code', 'unit_name'),
        }),
    )


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'account', 'role', 'action', 'ip', 'created_at')
    search_fields = ('account', 'action')
    date_hierarchy = 'created_at'
