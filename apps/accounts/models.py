"""用户模型（role 语义与前端三端对齐）与操作日志"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """角色枚举值沿用行业惯例，语义按前端三端重排：

    admin=省级最高(super) / city=市州管理员(admin) / school=球队负责人(leader)
    athlete=学生运动员(student) / coach=教练员(coach) / province=省级内容发布（暂不接）
    """

    class Role(models.TextChoices):
        ADMIN = 'admin', '省级管理员'
        PROVINCE = 'province', '省级内容发布'
        CITY = 'city', '市州管理员'
        SCHOOL = 'school', '球队负责人'
        ATHLETE = 'athlete', '学生运动员'
        COACH = 'coach', '教练员'
        PERSONAL = 'personal', '个人用户'

    role = models.CharField('角色', max_length=20, choices=Role.choices, default='personal', db_index=True)
    real_name = models.CharField('姓名/单位名', max_length=100, blank=True, default='')
    phone = models.CharField('手机号', max_length=20, blank=True, default='')
    region_code = models.CharField('所属市州区划代码', max_length=6, null=True, blank=True, db_index=True)
    region_name = models.CharField('所属市州名', max_length=30, blank=True, default='')
    unit_name = models.CharField('所属机构/单位', max_length=100, blank=True, default='')

    class Meta:
        db_table = 'accounts_user'
        verbose_name = '用户'

    def __str__(self):
        return f'{self.username}({self.get_role_display()})'

    @property
    def persona(self) -> str | None:
        """用户端身份映射：前端按 persona 决定菜单可见性"""
        return {'school': 'leader', 'athlete': 'student', 'coach': 'coach'}.get(self.role)


class AuditLog(models.Model):
    """操作日志（管理员端两处日志页）"""

    user = models.ForeignKey(User, verbose_name='操作人', on_delete=models.SET_NULL, null=True, blank=True)
    account = models.CharField('账号', max_length=50)
    role = models.CharField('操作时角色', max_length=20)
    action = models.CharField('操作内容', max_length=255)
    ip = models.GenericIPAddressField('IP 地址', null=True, blank=True)
    created_at = models.DateTimeField('操作时间', auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'accounts_audit_log'
        verbose_name = '操作日志'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.account} {self.action}'


def log_action(request, action: str) -> None:
    """在关键写操作里记一条日志"""
    user = request.user
    AuditLog.objects.create(
        user=user if user.is_authenticated else None,
        account=getattr(user, 'username', '') or '-',
        role=getattr(user, 'role', '') or '-',
        action=action,
        ip=request.META.get('REMOTE_ADDR'),
    )
