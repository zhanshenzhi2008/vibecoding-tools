description: |
  通用 Docker + Traefik + Portainer 部署技能。覆盖单主机 Docker 部署到生产环境的全流程。

  适用场景（触发词）：
  - "部署"、"上线"、"deploy"、"ship"
  - "怎么配 Traefik"、"Traefik 路由"
  - "Portainer 导入"、"docker compose 启动"
  - "Let's Encrypt 证书"、"HTTPS 配置"
  - "新服务器初始化"、"首次部署"
  - "502 / 404 / CORS 排查"

  模板变量说明（部署时替换）：
  - {{PROJECT_NAME}}  项目名，如 "myapp"
  - {{DOMAIN}}        域名，如 "myapp.example.com"
  - {{SERVER_IP}}     服务器 IP
  - {{DB_PASSWORD}}   PostgreSQL 密码（从 GitHub Secrets 读取）
  - {{JWT_SECRET}}    JWT 密钥（从 GitHub Secrets 读取）
  - {{ENCRYPTION_KEY}} 加密密钥（从 GitHub Secrets 读取）
  - {{LLM_API_KEY}}   LLM API Key（从 GitHub Secrets 读取）
  - {{SSH_USER}}      服务器 SSH 用户名
  - {{SSH_PORT}}      SSH 端口（默认 22）
---

# 通用 Docker 部署 Skill

> **目标**：把任何 Docker 化项目部署到带 **Traefik + Portainer** 的单台服务器。
>
> 本 skill 假设：
> - 服务器是 Linux（Ubuntu 22.04+ / Debian 12+）
> - Docker 已安装
> - Traefik 监听 80/443（自动 HTTPS）
> - Portainer 管理 Docker（可选）
> - PostgreSQL + Redis 公用基础设施已部署在 `/opt/databases/`

---

## ⚠️ 安全红线

> **本 skill 会随 Cursor 同步到多台机器。真实敏感信息只放 GitHub Secrets 或服务器本地 `.env`，绝不写进 skill 文件。**

| 信息类型 | 写进 Skill？ | 正确位置 |
|---------|------------|---------|
| 服务器真实 IP / 域名 | ❌ 用 `{{DOMAIN}}` 占位 | DNS / GitHub Secrets |
| SSH 私钥 / 密码 | ❌ | GitHub Secrets |
| 数据库密码 / JWT Secret / API Key | ❌ 用 `{{VARIABLE}}` 占位 | GitHub Secrets / 服务器 `.env` |
| 网络名（`app-net` / `db-net`） | ✅ 可以 | 非敏感 |

### 占位符规范

```
{{DOMAIN}}           → myapp.example.com
{{SERVER_IP}}        → your.server.ip
{{DB_PASSWORD}}      → change_me_to_secure_password
{{JWT_SECRET}}       → change_me_to_secure_jwt_secret
{{ENCRYPTION_KEY}}   → 32-byte-random-string（生成后绝对不换）
{{LLM_API_KEY}}      → sk-...（从服务商获取）
{{EMAIL}}            → your-email@example.com（Let's Encrypt 注册邮箱）
{{PROJECT_NAME}}     → myapp
{{APP_PORT}}         → 8080（应用容器端口）
{{APP_NETWORK}}      → app-net（应用层 Docker 网络）
{{DB_NETWORK}}       → db-net（公用数据库网络）
{{VOLUME_UPLOADS}}   → myapp-uploads
{{REGISTRY}}         → ghcr.io/username
```

### 提交前检查

```bash
cd ~/.cursor/skills/deploy/
# 真实 IP
grep -rE "(\d{1,3}\.){3}\d{1,3}" . | grep -v "your\.server\.ip" | grep -v "0\.0\.0\.0"
# 真实邮箱
grep -rE "[a-zA-Z0-9_]+@[a-z]+\.[a-z]+" . | grep -v "example\.com" | grep -v "your-email"
# OpenAI Key
grep -rE "sk-[a-zA-Z0-9]{20,}" .
# GitHub Token
grep -rE "ghp_[a-zA-Z0-9]{36}" .
# 私钥头
grep -rE "BEGIN .* PRIVATE KEY" .
```

---

## 一、架构模式

```
                    ┌─────────────────────┐
                    │   Cloudflare DNS    │
                    │ {{DOMAIN}} → IP     │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  Traefik :80/:443   │
                    │  (自动 HTTPS)        │
                    └──────────┬──────────┘
                               │
            ┌─────────────────┼─────────────────┐
            │                 │                 │
            ▼                 ▼                 ▼
   ┌────────────────┐ ┌──────────────┐ ┌──────────────┐
   │  Web/Frontend  │ │  API Backend │ │  AI Service  │
   │   :{{PORT}}    │ │    :{{PORT}} │ │   :{{PORT}}  │
   │  / 根路径      │ │  /api/*      │ │  (内部访问)  │
   └────────────────┘ └──────────────┘ └──────────────┘
                               │
                    ┌──────────┴──────────┐
                    ▼                     ▼
              ┌──────────┐          ┌──────────┐
              │ postgres │          │  redis   │
              │ db-net   │          │ db-net   │
              └──────────┘          └──────────┘

共享网络：{{APP_NETWORK}}（应用层）
公用网络：{{DB_NETWORK}}（数据层，postgres/redis）
公用基础设施：/opt/databases/（所有项目共用）
```

---

## 二、目录规范

```
/opt/                          # 服务器目录约定
├── databases/                 # 公用数据库（所有项目共用）
│   ├── docker-compose.yml
│   ├── .env                  # chmod 600，数据库密码
│   └── postgres-init/
└── project/
    └── {{PROJECT_NAME}}/      # 项目代码
        ├── docker-compose.yml  # 生产编排（无 traefik-docker/ 子目录）
        ├── .env               # 应用配置
        └── app/               # 源代码

/opt/docker/                   # 基础设施（Traefik + Portainer）
```

---

## 三、公用数据库部署

> 每个项目共用一套 PostgreSQL + Redis，独立部署。

### 3.1 首次部署

```bash
# 1. 创建目录
sudo mkdir -p /opt/databases
sudo chown -R $(id -u):$(id -g) /opt/databases

# 2. 克隆或复制 compose
# 参考本 skill 的 references/databases/docker-compose.yml
cp databases/docker-compose.yml /opt/databases/

# 3. 配置密码（只放 /opt/databases/.env，绝对不提交 git）
cd /opt/databases
cat > .env << 'EOF'
POSTGRES_PASSWORD={{DB_PASSWORD}}
POSTGRES_USER=appuser
POSTGRES_DB={{PROJECT_NAME}}
REDIS_PASSWORD={{REDIS_PASSWORD:-}}
EOF
chmod 600 .env

# 4. 创建外部网络
docker network inspect {{DB_NETWORK}} >/dev/null 2>&1 \
  || docker network create {{DB_NETWORK}}

# 5. 启动
docker compose --env-file .env up -d

# 6. 验证
docker exec db-postgres pg_isready
docker exec db-redis redis-cli ping
```

### 3.2 应用连接配置

```yaml
# docker-compose.yml（应用侧）
services:
  {{PROJECT_NAME}}:
    networks:
      - {{APP_NETWORK}}
      - {{DB_NETWORK}}         # ← 必须加入公用网络
    environment:
      POSTGRES_HOST: postgres   # ← 容器名，不是 127.0.0.1
      POSTGRES_PORT: 5432
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      REDIS_HOST: redis
      REDIS_PORT: 6379
```

> **关键**：连接地址用**容器名**（`postgres` / `redis`），跨网络访问。

---

## 四、三种部署方式

| 方案 | 工具 | 适用场景 | 版本控制 |
|------|------|---------|---------|
| **A：Portainer 导入** | Portainer Web UI | 初次验证、图形化运维 | 弱（需手动同步） |
| **B：命令行部署** | SSH + docker compose | 应急、调试 | 强（git 跟踪） |
| **C：GitHub Actions** | CI/CD 自动 | 生产日常发布 | 最强 |

> **推荐**：A 初次手动导入验证 → C 后续自动更新。

---

## 五、方案 A：Portainer 导入 Stack

### 5.1 前置准备

1. **创建外部网络**（Portainer → Networks → Add network）：
   - Name: `{{APP_NETWORK}}`
   - Driver: `bridge`

2. **创建外部卷**（Portainer → Volumes → Add volume）：
   - `{{VOLUME_UPLOADS}}`
   - `postgres-data`（如果 DB 不在 /opt/databases/）

3. **确认 Traefik 加入 `{{APP_NETWORK}}`**（否则无法路由）

### 5.2 导入 Stack

Portainer → **Stacks** → **Add stack**：

- **方式 1（推荐）**：Git repository（自动同步最新）
  ```
  Repository URL: git@github.com:username/{{PROJECT_NAME}}.git
  Reference: main
  Compose path: docker-compose.yml
  ```

- **方式 2**：Web editor（手动粘贴 compose 内容）

- **Environment variables**：填入 `.env` 内容

- **Deploy the stack**

### 5.3 Traefik 网络要求

如果 Traefik 也是 Portainer 部署，必须加入 `{{APP_NETWORK}}`：

```yaml
# Traefik stack
services:
  traefik:
    networks:
      - {{APP_NETWORK}}          # ← 关键
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro

networks:
  {{APP_NETWORK}}:
    external: true
    name: {{APP_NETWORK}}
```

> Traefik 必须挂载 `/var/run/docker.sock` 才能自动发现容器路由。

---

## 六、方案 B：命令行部署

```bash
# 1. 确保基础设施
docker network inspect {{DB_NETWORK}} >/dev/null 2>&1 \
  || docker network create {{DB_NETWORK}}
docker network inspect {{APP_NETWORK}} >/dev/null 2>&1 \
  || docker network create {{APP_NETWORK}}
docker volume create {{VOLUME_UPLOADS}}

# 2. 克隆代码
git clone git@github.com:username/{{PROJECT_NAME}}.git \
  /opt/project/{{PROJECT_NAME}}

# 3. 配置 .env（只放服务器本地，不提交 git）
cd /opt/project/{{PROJECT_NAME}}
cp .env.example .env
vi .env   # 填入真实值

# 4. 启动
docker compose up -d

# 5. 验证
docker compose ps
docker compose logs -f
```

---

## 七、方案 C：GitHub Actions 自动部署

### 7.1 GitHub Secrets 配置

进入仓库 → **Settings → Secrets and variables → Actions**，添加：

| Secret | 内容 |
|--------|------|
| `DEPLOY_HOST` | 服务器 IP |
| `DEPLOY_USER` | `{{SSH_USER}}` |
| `DEPLOY_SSH_PORT` | `{{SSH_PORT}}` |
| `DEPLOY_SSH_KEY` | SSH 私钥全文 |
| `IMAGE_REGISTRY_TOKEN` | GitHub PAT（`write:packages`） |
| `POSTGRES_PASSWORD` | `{{DB_PASSWORD}}` |
| `JWT_SECRET` | `{{JWT_SECRET}}` |
| `ENCRYPTION_KEY` | `{{ENCRYPTION_KEY}}` |
| `LLM_API_KEY` | `{{LLM_API_KEY}}` |

### 7.2 服务器 SSH 配置

```bash
# 生成专用密钥对
ssh-keygen -t ed25519 -C "github-deploy" -f ~/.ssh/github_deploy
cat ~/.ssh/github_deploy.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys

# 复制私钥到 GitHub Secret
cat ~/.ssh/github_deploy
```

### 7.3 触发部署

```bash
# 推送即部署
git push origin main

# 或 GitHub → Actions → Deploy workflow → Run workflow
```

---

## 八、Traefik Docker Labels 详解

> 推荐用 Docker labels（与容器绑定，容器启动即路由生效）。

### 8.1 Web 前端

```yaml
labels:
  - "traefik.enable=true"
  # 路由：访问 {{DOMAIN}} → 本容器
  - "traefik.http.routers.{{PROJECT_NAME}}-web.rule=Host(`{{DOMAIN}}`)"
  - "traefik.http.routers.{{PROJECT_NAME}}-web.entrypoints=websecure"
  - "traefik.http.routers.{{PROJECT_NAME}}-web.tls=true"
  - "traefik.http.routers.{{PROJECT_NAME}}-web.tls.certresolver=letsencrypt"
  - "traefik.http.services.{{PROJECT_NAME}}-web.loadbalancer.server.port={{PORT}}"
  # HTTP → HTTPS 跳转
  - "traefik.http.middlewares.{{PROJECT_NAME}}-web-redirect.redirectscheme.scheme=https"
  - "traefik.http.middlewares.{{PROJECT_NAME}}-web-redirect.redirectscheme.permanent=true"
  - "traefik.http.routers.{{PROJECT_NAME}}-web-http.rule=Host(`{{DOMAIN}}`)"
  - "traefik.http.routers.{{PROJECT_NAME}}-web-http.entrypoints=web"
  - "traefik.http.routers.{{PROJECT_NAME}}-web-http.middlewares={{PROJECT_NAME}}-web-redirect"
```

### 8.2 API 后端

```yaml
labels:
  - "traefik.enable=true"
  # 只路由 /api/* 路径
  - "traefik.http.routers.{{PROJECT_NAME}}-api.rule=Host(`{{DOMAIN}}`) && PathPrefix(`/api`)"
  - "traefik.http.routers.{{PROJECT_NAME}}-api.entrypoints=websecure"
  - "traefik.http.routers.{{PROJECT_NAME}}-api.tls=true"
  - "traefik.http.routers.{{PROJECT_NAME}}-api.tls.certresolver=letsencrypt"
  - "traefik.http.services.{{PROJECT_NAME}}-api.loadbalancer.server.port={{PORT}}"
```

### 8.3 内部服务（不暴露公网）

```yaml
labels:
  - "traefik.enable=false"   # 不走 Traefik，仅内部调用
```

### 8.4 Traefik 核心配置（traefik.yml）

```yaml
providers:
  docker:
    endpoint: "unix:///var/run/docker.sock"
    exposedByDefault: false   # 必须显式 traefik.enable=true 才路由
    network: {{APP_NETWORK}}  # Traefik 必须加入应用网络

certificatesResolvers:
  letsencrypt:
    acme:
      email: {{EMAIL}}
      storage: /letsencrypt/acme.json
      httpChallenge:
        entryPoint: web       # 通过 80 端口 HTTP 验证
```

---

## 九、常见故障排查

### ❌ 404 — Traefik 没匹配到路由

```bash
# 查看 Traefik 日志
docker logs traefik --tail 50

# 查看 Traefik 发现的路由
curl http://localhost:8080/api/http/routers

# 确认容器有 traefik.enable=true
docker inspect {{PROJECT_NAME}} | grep -A 5 Labels
```

### ❌ 502 — 后端容器不可达

- 确认 `traefik.http.services.*.loadbalancer.server.port` 与容器实际端口一致
- 确认容器在 `{{APP_NETWORK}}` 网络

### ❌ Let's Encrypt 申请失败

```bash
# 确认 DNS 解析
dig {{DOMAIN}}

# 确认 80 端口可访问
curl -I http://{{SERVER_IP}}

# 查看 acme 日志
docker logs traefik 2>&1 | grep -i acme
```

### ❌ CORS 跨域

**根因**：前后端不同源。**解决**：前端用 `https://{{DOMAIN}}/api/*` 调用后端（同源）。

### ❌ 容器间网络不通

```bash
# 确认同网络
docker inspect {{PROJECT_NAME}} | grep Networks -A 10

# 容器内测试
docker exec {{PROJECT_NAME}} curl http://internal-service:8080/health
```

---

## 十、新服务器部署清单

```bash
# ===== 1. 服务器初始化 =====
curl -fsSL https://get.docker.com | sh
useradd -m -s /bin/bash {{SSH_USER}}
mkdir -p /opt/project && chown {{SSH_USER}}:{{SSH_USER}} /opt/project

# ===== 2. 部署公用数据库 =====
mkdir -p /opt/databases
# 复制 references/databases/docker-compose.yml 到 /opt/databases/
vi /opt/databases/.env    # 只填 POSTGRES_PASSWORD={{DB_PASSWORD}}
docker network inspect {{DB_NETWORK}} >/dev/null 2>&1 \
  || docker network create {{DB_NETWORK}}
docker compose --env-file /opt/databases/.env \
  -f /opt/databases/docker-compose.yml up -d

# ===== 3. 创建应用层网络 =====
docker network create {{APP_NETWORK}}
docker volume create {{VOLUME_UPLOADS}}

# ===== 4. 克隆并部署项目 =====
mkdir -p /opt/project
git clone git@github.com:username/{{PROJECT_NAME}}.git \
  /opt/project/{{PROJECT_NAME}}
cd /opt/project/{{PROJECT_NAME}}
cp .env.example .env && vi .env   # 填入真实值
docker compose up -d

# ===== 5. 验证 =====
curl https://{{DOMAIN}}
curl https://{{DOMAIN}}/api/v1/health
docker compose ps
docker network inspect {{APP_NETWORK}}
```

---

## 十一、证书与维护

### 自动续签

Let's Encrypt 证书有效期 90 天，Traefik 自动续签。续签失败时：

```bash
docker compose stop traefik
rm -f /letsencrypt/acme.json
docker compose start traefik
```

### 手动更新镜像

```bash
cd /opt/project/{{PROJECT_NAME}}
docker compose pull && docker compose up -d
```

### 备份数据库

```bash
docker exec db-postgres pg_dump -U postgres {{PROJECT_NAME}} \
  > backup_$(date +%Y%m%d).sql
```

---

## 配套文件

| 文件 | 用途 |
|------|------|
| `references/databases/docker-compose.yml` | 公用数据库 compose 模板 |
| `references/databases/databases.env.example` | 数据库环境变量模板 |
| `assets/traefik-stack.yml` | Portainer 部署 Traefik compose |
| `assets/deploy.sh` | 一键部署脚本（需填入真实值后使用） |

---

## 模板变量速查

| 变量 | 示例值 | 来源 |
|------|--------|------|
| `{{PROJECT_NAME}}` | `myapp` | 用户指定 |
| `{{DOMAIN}}` | `myapp.example.com` | 用户指定 |
| `{{SERVER_IP}}` | `your.server.ip` | GitHub Secrets |
| `{{SSH_USER}}` | `deploy` | 用户指定 |
| `{{SSH_PORT}}` | `22` | GitHub Secrets |
| `{{DB_PASSWORD}}` | `xxx` | GitHub Secrets |
| `{{JWT_SECRET}}` | `xxx` | GitHub Secrets |
| `{{ENCRYPTION_KEY}}` | `xxx` | GitHub Secrets（生成后永不换） |
| `{{LLM_API_KEY}}` | `sk-xxx` | GitHub Secrets |
| `{{EMAIL}}` | `admin@example.com` | Let's Encrypt 注册邮箱 |
| `{{APP_NETWORK}}` | `myapp-net` | 用户指定（建议 `{{PROJECT_NAME}}-net`） |
| `{{DB_NETWORK}}` | `db-net` | 固定：所有项目共用 |
| `{{VOLUME_UPLOADS}}` | `myapp-uploads` | 用户指定（建议 `{{PROJECT_NAME}}-uploads`） |
| `{{PORT}}` | `8080` | 项目 docker-compose.yml |
| `{{REGISTRY}}` | `ghcr.io/username` | GitHub Packages |

