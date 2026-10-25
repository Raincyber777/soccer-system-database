# 绿茵汇后端（soccer-system-database）

省级中小学足球系统「绿茵汇」的自研 Django 后端，与前端仓库 `足球系统开发/soccer-system` 配套。
接口契约见需求文档（《赛事系统前端接口需求文档》《赛事系统数据库改造指南》），本项目即为这两份文档的落地实现。

## 技术栈

Django 5.2 + DRF 3.17 + SimpleJWT。开发默认 SQLite（零配置开箱即跑），生产可切 MySQL 8（见 `config/settings.py` 注释）。

## 快速开始

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo      # 灌入演示数据（幂等）
python manage.py runserver 8000
```

启动后：

- 前端 `npm run dev`（vite 已把 `/api` 代理到 `http://127.0.0.1:8000`），门户三页即显示数据库真实数据
- 演示账号（密码均为 `123456`）：`user001`（球队负责人）/ `student001`（学生运动员）/ `coach001`（教练员）/ `admin001`（市州管理员·成都市）/ `super001`(省级管理员)
- Django 后台在 `/django-admin/`（前端占用了 `/admin` 路由，故错开）

## 结构

```
config/          settings / urls / wsgi
apps/common/     统一响应信封 + 业务码异常 + 分页 + 权限 + 行政区划/学校/字典/系统参数/上传
apps/accounts/   用户(角色体系) + JWT 认证 + 自助注册 + 账号管理 + 操作日志
apps/portal/     赛事/球队/球员/教练/报名两级审核/对阵赛果/进球判罚/图文直播/内容/遴选/统计
```

## 接口约定

- 统一响应：`{ code, message, data, trace_id, timestamp }`，`code=0` 成功
- 业务码：20001 未登录 / 20002 登录失败 / 40000 参数错误 / 40300 无权限 / 40400 不存在
- 分页：`?page=&page_size=` → `{ total, page, page_size, pages, results }`
- 认证：`Authorization: Bearer <access>`，access 2 小时，refresh 7 天

## 角色与数据域

| role | 前端端 | 数据范围 |
|---|---|---|
| admin | /super 超管端 | 全省 |
| city | /admin 管理端 | 本区域（region_code） |
| school / athlete / coach | /user 用户端 | 本队 / 本人 |

## 常用命令

```bash
python manage.py seed_demo                # 重建演示数据（先删 db.sqlite3 再跑）
python manage.py createsuperuser          # Django 后台账号（与业务角色无关）
python manage.py shell                    # 数据调试
```
