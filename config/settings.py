"""
绿茵汇 · 省级中小学足球系统后端
Django settings（开发默认 SQLite，开箱即跑；生产切 MySQL 见 DATABASES 注释）
"""
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# 演示密钥：上线前务必换成环境变量注入的随机值
SECRET_KEY = 'demo-secret-key-change-me-in-production'

DEBUG = True

ALLOWED_HOSTS = ['*']

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
CORS_ALLOW_ALL_ORIGINS = True
