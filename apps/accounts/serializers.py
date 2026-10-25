from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()

ALLOWED_REGISTER_ROLES = ('school', 'athlete', 'coach')


class UserSerializer(serializers.ModelSerializer):
    """用户信息（登录/ me / 用户管理通用）"""

    role_display = serializers.CharField(source='get_role_display', read_only=True)
    persona = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'role', 'role_display', 'persona', 'real_name',
            'phone', 'email', 'region_code', 'region_name', 'unit_name',
            'is_active', 'is_superuser', 'date_joined',
        ]
        read_only_fields = ['id', 'is_superuser', 'date_joined']


class RegisterSerializer(serializers.ModelSerializer):
    """自助注册：仅开放用户端三种身份（school/athlete/coach）"""

    password = serializers.CharField(write_only=True, min_length=6)
    school_code = serializers.CharField(write_only=True, required=False, allow_blank=True, default='')

    class Meta:
        model = User
        fields = ['username', 'password', 'real_name', 'role', 'school_code', 'phone', 'email']

    def validate_role(self, value):
        if value not in ALLOWED_REGISTER_ROLES:
            raise serializers.ValidationError('仅支持注册球队负责人 / 学生运动员 / 教练员身份')
        return value

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('用户名已存在')
        return value

    def validate(self, attrs):
        from apps.common.models import School

        school_code = attrs.pop('school_code', '')
        if school_code:
            school = School.objects.filter(code=school_code, is_active=True).first()
            if not school:
                raise serializers.ValidationError({'school_code': '学校标识码不存在或未启用'})
            attrs['_school'] = school
        return attrs

    def create(self, validated_data):
        school = validated_data.pop('_school', None)
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        # 球队负责人把所属单位定为学校，便于展示与归属
        if school and user.role == 'school':
            user.unit_name = school.name
        user.save()
        return user


class UserCreateSerializer(serializers.ModelSerializer):
    """管理员开户（city 自动归属本区域）"""

    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ['username', 'password', 'real_name', 'role', 'unit_name', 'phone', 'region_code']

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('用户名已存在')
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        request = self.context.get('request')
        user = User(**validated_data)
        # 市州管理员开户强制归属本区域
        if request and request.user.role == 'city':
            user.region_code = request.user.region_code
            user.region_name = request.user.region_name
        user.set_password(password)
        user.save()
        return user


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=6)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('原密码不正确')
        return value

    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user
