@echo off
REM ============================================================
REM 绿茵汇后端生产启动（Windows）
REM 用法：双击运行，或命令行 start_prod.bat
REM 先按需修改下方三处，再启动
REM ============================================================
chcp 65001 >nul
cd /d %~dp0

REM ---- ① 必改：换一个随机长字符串（每次部署换新的）----
if "%DJANGO_SECRET_KEY%"=="" set "DJANGO_SECRET_KEY=please-change-me-%RANDOM%%RANDOM%%RANDOM%"

REM ---- ② 必改：前端部署地址（CORS 白名单，多个用逗号分隔）----
if "%DJANGO_CORS_ORIGINS%"=="" set "DJANGO_CORS_ORIGINS=https://example.github.io"

REM ---- ③ 建议：对外域名或 IP（逗号分隔；保持 * 则不校验 Host，演示可用）----
if "%DJANGO_ALLOWED_HOSTS%"=="" set "DJANGO_ALLOWED_HOSTS=*"

REM 关闭调试模式（生产必须）
set "DJANGO_DEBUG=False"

REM 端口可按需改（对外要配套防火墙/安全组放行）
set "PORT=8000"

echo [1/3] 数据库迁移检查...
python manage.py migrate --noinput
if errorlevel 1 (
  echo 迁移失败，请检查 Python 环境：pip install -r requirements.txt
  pause
  exit /b 1
)

echo [2/3] 以生产模式启动 waitress（监听 0.0.0.0:%PORT%，Ctrl+C 停止）...
echo     DEBUG=%DJANGO_DEBUG%  CORS=%DJANGO_CORS_ORIGINS%
python -m waitress --listen=0.0.0.0:%PORT% config.wsgi:application
