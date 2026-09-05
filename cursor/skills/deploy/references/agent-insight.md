# agent-insight 部署参考（来源：仓库 `docker-traefik/`）

> 本文件是 `deploy` skill 的项目特化附录。通用流程见 `SKILL.md`；
> 源码真相以仓库 `docker-traefik/` 为准。

---

## 1. 仓库 → 服务器映射

| 仓库路径 | 服务器路径 | 职责 |
|---------|-----------|------|
| `docker-traefik/traefik/` | `/opt/docker/` | Traefik + Portainer |
| `docker-traefik/databases/` | `/opt/databases/` | MySQL / MongoDB / Redis / pgsql |
| `docker-traefik/agent-insight/` | `/opt/project/agent-insight/` | 应用 compose + 启动 |
| （无仓文件） | `/opt/project/envs/` | 跨项目共享 `db.env` / `llm.env` |
| （运行时） | `/opt/project/agent-insight/data/` | 日志 / 脚本 Bind Mount（`DATA_ROOT`） |

> **路径约定**：Cogniforge 规范用 `/opt/project/<name>/`。
> 仓库部分注释仍写 `/opt/app/agent-insight` —— **以 `/opt/project/` 为准**，部署时统一。

---

## 2. 网络（固定名，不要改）

| 网络 | 谁创建 | 谁加入 |
|------|--------|--------|
| `proxy` | `/opt/docker/docker-compose-base.yml` | Traefik、Portainer、对外暴露的应用容器 |
| `db-net` | `/opt/databases/docker-compose.yml` | 数据库 + 需要连库的应用容器 |

- Traefik `providers.docker.network: proxy`
- 数据库**不要**加入 `proxy`
- 方案 A 后端只加 `db-net`（不暴露给 Traefik）

---

## 3. 应用路由三选一（互斥）

三个 compose **容器名相同**，同一台机只能启用一个。

| 文件 | 模式 | Traefik 挂谁 | 何时用 |
|------|------|-------------|--------|
| `docker-compose.yml` | **方案 A（推荐）** | 仅 frontend | Nginx 内部代理 `/api` → `agent-insight-backend:9280` |
| `docker-compose.b-traefik-api.yml` | 方案 B | frontend + backend | Traefik 同域分流：`PathPrefix(/api)` priority=100 |
| `docker-compose.c-separate-domains.yml` | 方案 C | frontend + backend | `FRONTEND_DOMAIN` + `API_DOMAIN` 双域名 |

### 方案 A labels（摘录）

```yaml
# 仅 frontend
traefik.enable=true
traefik.http.routers.agent-insight-frontend.rule=Host(`${DOMAIN}`)
traefik.http.routers.agent-insight-frontend.entrypoints=websecure
traefik.http.routers.agent-insight-frontend.tls.certresolver=letsencrypt
traefik.http.services.agent-insight-frontend.loadbalancer.server.port=80
traefik.docker.network=proxy
```

### 方案 B 额外

```yaml
# backend priority 高于 frontend
Host(`${DOMAIN}`) && PathPrefix(`/api`)  # priority=100
# frontend Host(`${DOMAIN}`)             # priority=10
# 前端镜像须 VITE_API_BASE_URL=/api
```

### 方案 C

```yaml
Host(`${API_DOMAIN}`)           # backend :9280
Host(`${FRONTEND_DOMAIN}`)      # frontend :80
# 前端构建：VITE_API_BASE_URL=https://${API_DOMAIN}/api
# 后端需开 CORS
```

### Portainer Stack 环境变量

| 方案 | 必填 |
|------|------|
| A / B | `DOMAIN=insight.example.com`，可选 `DATA_ROOT` |
| C | `FRONTEND_DOMAIN` + `API_DOMAIN`，可选 `DATA_ROOT` |

> `${DOMAIN}` 必须出现在 **compose 同级 `.env` 或 Portainer Stack env**，
> 写在 `environment:` 块里**不能**替换 labels 中的 `${DOMAIN}`。

---

## 4. env_file 布局（与 compose 对齐）

compose 写的是：

```yaml
env_file:
  - ../envs/db.env
  - ../envs/llm.env
```

因此服务器真实布局必须是：

```
/opt/project/
├── envs/
│   ├── db.env      # 从 agent-insight/envs/db.env.example 复制填写
│   └── llm.env     # 从 agent-insight/envs/llm.env.example 复制填写
└── agent-insight/
    ├── docker-compose.yml
    ├── .env        # DOMAIN / DATA_ROOT / IMAGE_NAMESPACE
    └── data/       # DATA_ROOT 默认指向这里
```

| 变量文件 | 内容 |
|---------|------|
| `../envs/db.env` | `MYSQL_*` / `MONGODB_*` / `REDIS_*`（agent-insight 用）；`PGSQL_*` 给同机其他项目 |
| `../envs/llm.env` | `AI_ENABLED` / `AI_PROVIDER` / `OPENAI_*` 等 |
| `agent-insight/.env` | `DOMAIN`、`DATA_ROOT`、`IMAGE_NAMESPACE` |

**密码对齐**：`db.env` 的 `MYSQL_PASSWORD` 必须等于 `/opt/databases/.env` 的 `MYSQL_ROOT_PASSWORD`。

---

## 5. 镜像与端口

| 服务 | 镜像 | 容器端口 |
|------|------|---------|
| backend | `ghcr.io/${IMAGE_NAMESPACE}/agent-insight/backend:latest` | **9280** |
| frontend | `ghcr.io/${IMAGE_NAMESPACE}/agent-insight/frontend:latest` | **80** |

- 生产：服务器只 `docker compose pull` + `up -d`，不在服务器 `git pull` 源码构建；CD 默认不拷贝 compose
- 本地源码构建时才打开 compose 里注释掉的 `build:` 块

---

## 6. 基础设施注意点

### Traefik 版本（Docker 29）

- 必须 **`traefik:v3.6.1+`**
- Docker Engine 29 最低 API 1.44；旧 Traefik 硬编码 API 1.24 → 报错 `client version 1.24 is too old`，Docker provider 失效 → 全站 404
- 自定义挂载 `./traefik/traefik.yml:/traefik.yml` 时，`command` 必须带 `--configFile=/traefik.yml`

### Frontend / Backend healthcheck（BusyBox · Traefik v3 · 方案 A）

| 角色 | 技术 | 正确探测 | 错误示例 |
|------|------|----------|----------|
| frontend | Nginx | `wget -q --spider http://127.0.0.1:80/health`（nginx.conf 自配） | 探 `9280` / Actuator / 端口 `3000` / `--bind-address` |
| backend | **Spring Boot 原生 Actuator** | `curl -f http://127.0.0.1:9280/actuator/health` | 探 Nginx `80/health`，或误用 `/health`（默认不是此路径） |
| backend（对照） | **Go 项目自建** | 常见 `http://127.0.0.1:8080/health`（非官方统一标准） | 与前端/Spring 路径混用 |

- agent-insight 后端是 **Java/Spring Boot**：健康端点是 **`/actuator/health`**（官方 Actuator），**不是** `/health`
- compose 里 frontend 的 `80/health` **没有写错**：那是 Nginx，和 Java 无关
- Traefik 只看 **打了 `traefik.enable=true` 的容器** 的 healthy；方案 A 一般是 **frontend**
- frontend healthy ≠ backend 业务可用；backend 挂了通常是 `/api` 502，不是整站 Traefik 404
- Alpine BusyBox `wget` **不支持** `--bind-address`、`--no-verbose`、`--tries`
- Dockerfile `HEALTHCHECK` 与 compose `healthcheck` 须一致；compose 可覆盖镜像内指令

### Portainer 路由

- 推荐 Docker Labels：`Host(\`portainer.${BASE_DOMAIN}\`)`
- `/opt/docker/.env`：从 `assets/traefik.env.example` 复制；`BASE_DOMAIN=example.duckdns.org`（**不含** `portainer.` / `traefik.` 前缀）
- Dashboard 以后要加锁：`htpasswd -nbB admin 'your-password'`，输出里的 `$` 改成 `$$`，写入 `TRAEFIK_DASHBOARD_AUTH`；多人用逗号拼接 `admin:$$hash1,alice:$$hash2`
- `traefik.yml` 的 file provider 已废弃注释；不要与 Labels **同时**写同一条 portainer 路由

### PostgreSQL 18 数据目录

- 挂载点：`./pgsql/data:/var/lib/postgresql`（**不是** `/var/lib/postgresql/data`）
- agent-insight 自身当前不连 pgsql；库仍可给 cogniforge 等项目共用

---

## 7. 首次部署顺序

```bash
# 1) 网络会随 compose 自动创建；也可预创建
docker network inspect proxy  >/dev/null 2>&1 || docker network create proxy
docker network inspect db-net >/dev/null 2>&1 || docker network create db-net

# 2) 数据库
cd /opt/databases && cp databases.env.example .env && vi .env
docker compose --env-file .env up -d

# 3) Traefik（镜像 ≥ v3.6.1，.env 含 BASE_DOMAIN）
cd /opt/docker
cp traefik.env.example .env && vi .env   # BASE_DOMAIN=your.base.domain
docker compose -f docker-compose-base.yml up -d

# 4) 应用
mkdir -p /opt/project/envs /opt/project/agent-insight/data
# 复制 compose；把 example 填到 /opt/project/envs/{db,llm}.env
# /opt/project/agent-insight/.env → DOMAIN=insight.your.base.domain
cd /opt/project/agent-insight
docker compose up -d
```

---

## 8. 故障速查（本项目常见）

| 现象 | 检查 |
|------|------|
| 全站 404 | Traefik 版本、`docker logs traefik` 是否 API 1.24；容器是否在 `proxy`；路由器是否写了 `.service=`（没写会找同名服务） |
| 路由器 404 / 无后端 | 路由器名 ≠ compose 服务名时必须 `routers.X.service=Y`（例：`wifi-tie-admin` → `wifi-tie-admin-web`） |
| 后端连库失败 `lookup port=0` | `../envs/db.env` 路径是否存在、变量是否为空 |
| frontend unhealthy | 方案 A 下 Nginx 是否能解析 `agent-insight-backend`（同 `db-net`） |
| Portainer 404 | `BASE_DOMAIN` 是否被 compose 替换进 label；DNS 子域是否存在 |
| Restricted 用户看不到 compose/CD 容器 | 每个服务加 `io.portainer.accesscontrol.users={{PORTAINER_RESTRICTED_USER}}`；详见 `SKILL.md` §5.4 |
| Let's Encrypt 失败 | DNS A 记录、80 开放、`acme.json` 权限 600 |
