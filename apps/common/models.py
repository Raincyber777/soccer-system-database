"""公共基础数据：行政区划 / 学校库 / 字典 / 系统参数"""
from django.db import models


class Region(models.Model):
    """行政区划（GB/T 2260）：21 个市州 parent_code 为空，区县指向所属市州"""

    code = models.CharField('区划代码', max_length=6, primary_key=True)
    name = models.CharField('名称', max_length=30)
    parent_code = models.CharField('上级行政区划代码', max_length=6, null=True, blank=True, db_index=True)

    class Meta:
        db_table = 'common_region'
        verbose_name = '行政区划'

    def __str__(self):
        return self.name


class School(models.Model):
    """学校库：学校（机构）标识码为唯一主键，前端 SchoolSelect 数据源"""

    class Stage(models.TextChoices):
        PRIMARY = 'primary', '小学'
        MIDDLE = 'middle', '初中'
        HIGH = 'high', '高中'
        UNIVERSITY = 'university', '高校'

    code = models.CharField('学校标识码', max_length=10, primary_key=True)
    name = models.CharField('学校名称', max_length=100)
    city_code = models.CharField('所属市州区划代码', max_length=6, db_index=True)
    district_name = models.CharField('所属区县', max_length=30, blank=True, default='')
    stage = models.CharField('学段', max_length=20, choices=Stage.choices)
    is_active = models.BooleanField('启用', default=True)

    class Meta:
        db_table = 'common_school'
        verbose_name = '学校'

    def __str__(self):
        return self.name

    @property
    def city_name(self) -> str:
        region = Region.objects.filter(code=self.city_code).first()
        return region.name if region else ''

    @property
    def stage_display(self) -> str:
        return self.get_stage_display()


class DictItem(models.Model):
    """字典：cert_level 教练等级 / position 场上位置 等枚举维护"""

    dict_type = models.CharField('字典类型', max_length=30, db_index=True)
    value = models.CharField('存库值', max_length=50)
    label = models.CharField('展示名', max_length=50)
    sort = models.IntegerField('排序', default=0)
    is_active = models.BooleanField('启用', default=True)

    class Meta:
        db_table = 'common_dict'
        verbose_name = '字典项'
        ordering = ['dict_type', 'sort']

    def __str__(self):
        return f'{self.dict_type}:{self.label}'


class SystemConfig(models.Model):
    """系统参数（前端 SystemConfig 页）"""

    key = models.CharField('参数键', max_length=50, unique=True)
    name = models.CharField('参数名', max_length=100)
    description = models.CharField('说明', max_length=200, blank=True, default='')
    value = models.CharField('当前值', max_length=200, blank=True, default='')
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'common_config'
        verbose_name = '系统参数'
