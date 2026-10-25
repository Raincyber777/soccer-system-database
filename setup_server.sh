#!/usr/bin/env bash
# ============================================================
# 绿茵汇后端 · 阿里云 ECS 一键部署脚本
# 前提：发布包已解压，且当前目录就是解压后的代码目录
#       （能看到 manage.py），用 root 或 sudo 执行：
#           bash setup_server.sh
# 幂等：重复执行安全（已存在的 prod.env / 服务不会被覆盖破坏）
# ============================================================
set -e
cd "$(dirname "$0")"
APP_DIR=$(pwd)

echo "==> 0/5 环境检查"
if ! command -v python3 >/dev/null; then
  echo "缺少 python3，请先安装：apt install -y python3 python3-venv python3-pip  或  dnf install -y python3.11 python3.11-pip"
  exit 1
fi
PYVER=$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')
echo "    python3 = $PYVER（Django 5 需要 >= 3.10）"
python3 - <<'EOF' || { echo "Python 版本过低，请升级到 3.10+"; exit 1; }
import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)
EOF

echo "==> 1/5 创建虚拟环境并安装依赖（阿里云 PyPI 镜像）"
[ -d venv ] || python3 -m venv venv
source venv/bin/activate
pip install -q -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ --upgrade pip

echo "==> 2/5 生成生产环境配置 prod.env（已存在则跳过，可自行编辑）"
if [ ! -f prod.env ]; then
  SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(48))")
  cat > prod.env <<EOF
DJANGO_SECRET_KEY=$SECRET
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=39.96.61.195
# 同源反代方案（nginx :8083 -> 127.0.0.1:8010）不需要 CORS；如改为跨域直连再打开：
# DJANGO_CORS_ORIGINS=http://39.96.61.195:8083
EOF
  echo "    已生成 prod.env（SECRET_KEY 为随机值）"
else
  echo "    prod.env 已存在，保留"
fi

echo "==> 3/5 数据库迁移"
set -a; source prod.env; set +a
python manage.py migrate --noinput

echo "==> 4/5 安装 systemd 服务（soccer，开机自启 + 崩溃自动拉起）"
cat > /etc/systemd/system/soccer.service <<EOF
[Unit]
Description=soccer backend (waitress on 127.0.0.1:8010)
After=network.target

[Service]
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/prod.env
ExecStart=$APP_DIR/venv/bin/python -m waitress --listen=127.0.0.1:8010 config.wsgi:application
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now soccer
sleep 2

echo "==> 5/5 自检"
curl -s "http://127.0.0.1:8010/api/portal/stats/ranking/?limit=1" | head -c 100; echo
systemctl is-active soccer && echo "OK 后端已在 127.0.0.1:8010 运行"

cat <<'TIP'

============================================================
后端就绪。剩下最后一步 —— nginx 反代（在 8083 站点配置里加）：

  location /api/ {
      proxy_pass http://127.0.0.1:8010;
      proxy_set_header Host $host;
      proxy_set_header X-Real-IP $remote_addr;
      client_max_body_size 25m;   # 上传文件 20MB 上限，默认 1m 会传不上！
  }
  location /media/ {
      proxy_pass http://127.0.0.1:8010;
  }

找配置：nginx -T 2>/dev/null | grep -B2 -A30 "listen 8083"
加完后：nginx -t && nginx -s reload
然后浏览器验证：http://39.96.61.195:8083/api/portal/stats/ranking/?limit=5
============================================================
TIP
