# 绿茵汇后端部署文档

> 前置说明：前端是纯静态站点（Vue3 构建），后端是 Django + SQLite 的 API 服务。
> 前端已部署，后端要做的就是：**把 API 跑起来 + 让部署好的前端能访问到它**。

## ⭐ 实机方案（已定，2026-10-25）

前端：`http://39.96.61.195:8083/`（阿里云 ECS，nginx 静态托管，http）
后端：**同一台 ECS**，waitress 跑 `127.0.0.1:8010`，由 nginx 在 **8083 同源反代** `/api/` 与 `/media/`。

同源方案的好处：
- 前端构建时 `VITE_API_BASE` 为空 → 本来就请求自己域名下的 `/api`，**无需重新构建前端**
- 浏览器视为同源，**无需 CORS**、无混合内容问题（前后端都是 http）
- 后端只监听 127.0.0.1，**安全组不用开新端口**

操作步骤（三步）：

```bash
# ① 本机：发布包已生成在桌面 soccer-backend.tar.gz，传到服务器
scp C:\Users\ASUS\Desktop\soccer-backend.tar.gz root@39.96.61.195:/opt/

# ② 服务器：解压 + 一键部署（脚本自动 venv/依赖/迁移/prod.env/systemd 自启）
ssh root@39.96.61.195
mkdir -p /opt/soccer-backend && cd /opt/soccer-backend
tar -xzf /opt/soccer-backend.tar.gz
bash setup_server.sh

# ③ 服务器：把脚本末尾打印的 nginx 两段 location 加进 8083 站点配置，然后
nginx -t && nginx -s reload
```

验证：浏览器开 `http://39.96.61.195:8083/api/portal/stats/ranking/?limit=5` 返回 JSON 信封（code=0）即全通，
已部署的前端页面**刷新即可用真数据**。

---
以下为通用参考（其他部署形态备用）。


## 一、架构与改动说明

```
浏览器 → 已部署的前端（静态）
              │  fetch /api/...（baseURL = VITE_API_BASE）
              ▼
        后端 Django API（waitress 启动，0.0.0.0:8000）
              └── SQLite（db.sqlite3）+ media/（上传文件）
```

本仓库已做的生产化改动（2026-10-25）：

| 文件 | 改动 |
|---|---|
| `config/settings.py` | SECRET_KEY / DEBUG / ALLOWED_HOSTS / CORS 白名单全部支持环境变量注入，不设则保持开发默认 |
| `config/urls.py` | `/media/` 上传文件在 DEBUG=False 时也由 Django 伺服（演示规模够用） |
| `requirements.txt` | 加 `waitress`（Windows/Linux 通用的生产 WSGI 服务器） |
| `start_prod.bat` / `start_prod.sh` | 一键生产启动脚本（迁移 + waitress） |

## 二、⚠️ 先想清楚三件事（决定方案）

1. **前端部署地址是什么？**（如 `https://xxx.github.io/soccer-system/`）——CORS 白名单和前端重建都要用它。
2. **前端是 https 吗？** GitHub Pages / 多数托管都是 https。
   **浏览器禁止 https 页面调用 http 接口（混合内容拦截）**：
   - 前端 https → 后端必须 https（用 Caddy / Nginx+certbot 套证书，或用带 https 的内网穿透如 ngrok）
   - 前端 http（自建服务器无证书）→ 后端 http 直连即可
3. **后端跑在哪？** 三个常见选择，按序推荐：
   - **A. 云服务器（Linux ECS）**：最稳，公网 IP 直达
   - **B. 本机 Windows + 内网穿透**：零成本演示（ngrok / 花生壳 / frp）
   - **C. 本机 Windows + 路由器公网 IP 端口映射**：家里宽带需有公网 IPv4

## 三、Windows 本机跑后端（方案 B/C）

```bat
cd /d E:\githubfirst\后端集\足球系统后端\soccer-system-database
pip install -r requirements.txt
start_prod.bat       REM 先编辑脚本里的 ①②③ 三处再运行
```

- 防火墙放行 8000 端口（首次运行 Windows 会弹窗，选"允许"）
- 内网穿透示例（ngrok）：`ngrok http 8000` → 得到 `https://xxxx.ngrok-free.app`，这就是后端对外地址
- 验证：浏览器开 `http://127.0.0.1:8010/api/portal/stats/ranking/?limit=5`，返回 JSON 信封即通

## 四、Linux 云服务器部署（方案 A）

```bash
# 1. 上传代码（或 git clone）
scp -r soccer-system-database/ root@服务器IP:/opt/soccer-backend/

# 2. 装环境（Python 3.11+）
cd /opt/soccer-backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 3. 改 start_prod.sh 的 ①②③，然后
chmod +x start_prod.sh && ./start_prod.sh
# 云控制台安全组放行 8000（或反代端口 80/443）
```

**常驻运行（systemd）** `/etc/systemd/system/soccer.service`：

```ini
[Unit]
Description=soccer backend
After=network.target

[Service]
WorkingDirectory=/opt/soccer-backend
EnvironmentFile=/opt/soccer-backend/prod.env
ExecStart=/opt/soccer-backend/venv/bin/python -m waitress --listen=0.0.0.0:8000 config.wsgi:application
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# prod.env 内容：
DJANGO_SECRET_KEY=<随机长字符串>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=<域名或IP>
DJANGO_CORS_ORIGINS=<前端地址>

systemctl enable --now soccer && systemctl status soccer
```

**https（前端是 https 时必配）**：装 Nginx 或 Caddy 反代 8000 → 443/80 并签证书。
Caddy 最省事：`Caddyfile` 两行 `你的域名 { reverse_proxy 127.0.0.1:8010 }` 即自动签 https。

## 五、前端配合（必做，否则部署好的前端连不上）

前端 `baseURL = VITE_API_BASE || ''`，构建时没设就会请求**前端自己域名下的 /api**（静态托管上必然 404，页面只能显示演示数据）。

```bat
cd 前端仓库 soccer-system
set VITE_API_BASE=https://后端对外地址        REM 如 https://xxxx.ngrok-free.app（不带结尾斜杠）
REM Git Bash: VITE_API_BASE=... npm run build
npm run build
```

把 `dist/` 重新发布到前端托管平台即可。GitHub Pages 部署记得带 `DEPLOY_BASE=soccer-system`。

## 六、上线检查清单

- [ ] `DJANGO_SECRET_KEY` 已换成随机值（演示密钥曾公开，**必须换**）
- [ ] `DJANGO_DEBUG=False`
- [ ] `DJANGO_ALLOWED_HOSTS` 收紧到真实域名/IP
- [ ] `DJANGO_CORS_ORIGINS` 只填前端地址（不再全放行）
- [ ] 演示账号改密：super001 / admin001 / user001 / student001 / coach001（默认密码 123456）
- [ ] `db.sqlite3` 定期备份（`copy db.sqlite3 backup\%date:~0,10%.db`）
- [ ] 前端已用 `VITE_API_BASE` 重新构建并发布
- [ ] https 页面调用 https 接口（无混合内容警告）
- [ ] 公网验证：`curl https://后端地址/api/portal/stats/ranking/?limit=5` 返回 code=0
