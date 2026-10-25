"""
绿茵汇 · 省级中小学足球系统后端
Django settings（开发默认 SQLite，开箱即跑；生产切 MySQL 见 DATABASES 注释）
"""
import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# 安全敏感项一律支持环境变量注入（生产启动脚本/云平台里设置，不设则保持开发默认值）：
#   DJANGO_SECRET_KEY      生产必设的随机长字符串
#   DJANGO_DEBUG           生产设 False
#   DJANGO_ALLOWED_HOSTS   逗号分隔的对外域名/IP，如 example.com,1.2.3.4
#   DJANGO_CORS_ORIGINS    逗号分隔的前端来源白名单，如 https://xxx.github.io
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'demo-secret-key-change-me-in-production')

DEBUG = os.environ.get('DJANGO_DEBUG', 'True').lower() in ('1', 'true', 'yes')

ALLOWED_HOSTS = [h.strip() for h in os.environ.get('DJANGO_ALLOWED_HOSTS', '*').split(',') if h.strip()]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # 第三方
    'rest_framework',
    'corsheaders',
    # 业务
    'apps.common',
    'apps.accounts',
    'apps.portal',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ===== 数据库 =====
# 开发默认 SQLite（零配置开箱即跑）
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
# 生产切 MySQL 8 时：pip install PyMySQL，然后在 manage.py 顶部加
#   import pymysql; pymysql.install_as_mysqldb()
# 并替换为：
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.mysql',
#         'NAME': 'soccer_system',
#         'USER': 'root',
#         'PASSWORD': '你的密码',
#         'HOST': '127.0.0.1',
#         'PORT': '3306',
#         'OPTIONS': {'charset': 'utf8mb4'},
#     }
# }

AUTH_PASSWORD_VALIDATORS = [
    # 演示账号密码是 123456，去掉强度校验；生产按需加回
]

LANGUAGE_CODE = 'zh-hans'

# 时间一律本地时区、不带 UTC 偏移，接口直接输出 YYYY-MM-DD HH:MM:SS
TIME_ZONE = 'Asia/Shanghai'
USE_TZ = False

STATIC_URL = 'static/'
# django-admin 后台静态文件（collectstatic 收集到这里，生产由 nginx 伺服）
STATIC_ROOT = BASE_DIR / 'static_root'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# 自定义用户模型
AUTH_USER_MODEL = 'accounts.User'

# ===== DRF =====
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.AllowAny',
    ),
    'DEFAULT_PAGINATION_CLASS': 'apps.common.pagination.EnvelopePagination',
    'PAGE_SIZE': 10,
    'EXCEPTION_HANDLER': 'apps.common.exceptions.envelope_exception_handler',
    'DEFAULT_RENDERER_CLASSES': ('apps.common.renderers.EnvelopeRenderer',),
    'DATETIME_FORMAT': '%Y-%m-%d %H:%M:%S',
    'NON_FIELD_ERRORS_KEY': 'detail',
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=2),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# ===== CORS（前端走 vite 代理时用不到，直连时放行）=====
# 生产设 DJANGO_CORS_ORIGINS 为前端来源白名单；不设则放行所有来源（开发方便，生产建议收紧）
_CORS_ORIGINS = [o.strip() for o in os.environ.get('DJANGO_CORS_ORIGINS', '').split(',') if o.strip()]
if _CORS_ORIGINS:
    CORS_ALLOWED_ORIGINS = _CORS_ORIGINS
else:
    CORS_ALLOW_ALL_ORIGINS = True

# django-admin 在反代后面提交表单时需要：与浏览器地址栏一致的完整来源（含端口）
CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.environ.get('DJANGO_CSRF_ORIGINS', '').split(',') if o.strip()]
