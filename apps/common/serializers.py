from rest_framework import serializers

from .models import DictItem, Region, School, SystemConfig


class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = ['code', 'name', 'parent_code']


class SchoolSerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(read_only=True)
    stage_display = serializers.CharField(read_only=True)

    class Meta:
        model = School
        fields = ['code', 'name', 'city_code', 'city_name', 'district_name', 'stage', 'stage_display', 'is_active']


class DictItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = DictItem
        fields = ['id', 'dict_type', 'value', 'label', 'sort', 'is_active']


class SystemConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemConfig
        fields = ['id', 'key', 'name', 'description', 'value', 'updated_at']
