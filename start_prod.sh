#!/usr/bin/env bash
# ============================================================
# 绿茵汇后端生产启动（Linux 云服务器 / macOS）
# 用法：先改下面三个值，然后 chmod +x start_prod.sh && ./start_prod.sh
# ============================================================
set -e
cd "$(dirname "$0")"

# ---- ① 必改：随机长字符串（python -c "import secrets; print(secrets.token_urlsafe(48))" 生成）----
export DJANGO_SECRET_KEY="${DJANGO_SECRET_KEY:-please-change-me}"

# ---- ② 必改：前端部署地址（CORS 白名单，多个用逗号分隔）----
export DJANGO_CORS_ORIGINS="${DJANGO_CORS_ORIGINS:-https://example.github.io}"

# ---- ③ 建议：对外域名或 IP（逗号分隔；* 则不校验，演示可用）----
export DJANGO_ALLOWED_HOSTS="${DJANGO_ALLOWED_HOSTS:-*}"

# 生产必须关调试
export DJANGO_DEBUG=False

PORT="${PORT:-8000}"

echo "[1/3] 数据库迁移检查..."
python manage.py migrate --noinput

echo "[2/3] 以生产模式启动 waitress（监听 0.0.0.0:${PORT}，Ctrl+C 停止）..."
echo "    DEBUG=${DJANGO_DEBUG}  CORS=${DJANGO_CORS_ORIGINS}"
exec python -m waitress --listen="0.0.0.0:${PORT}" config.wsgi:application
