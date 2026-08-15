description: |
  通用 Docker + Traefik + Portainer 部署技能。覆盖单主机 Docker 部署到生产环境的全流程。
  含 agent-insight（仓库 docker-traefik/）专项约定：见 references/agent-insight.md。

  适用场景（触发词）：
  - "部署"、"上线"、"deploy"、"ship"
  - "怎么配 Traefik"、"Traefik 路由"
  - "Portainer 导入"、"docker compose 启动"
  - "Let's Encrypt 证书"、"HTTPS 配置"
  - "新服务器初始化"、"首次部署"
  - "502 / 404 / CORS 排查"
  - "healthcheck"、"健康检查"、"unhealthy"、"BusyBox wget"
  - "前端 /health 还是 actuator"、"Nginx health"
  - "agent-insight 部署"、"docker-traefik"
  - "cogniforge 部署"、"PGSQL"、"镜像内置 configs"
  - "localhost:8080"、"公网打到本地"、"API_BASE"、"NUXT_PUBLIC_API_BASE"

  模板变量说明（部署时替换）：
  - {{PROJECT_NAME}}  项目名，如 "myapp" / "agent-insight"
  - {{DOMAIN}}        完整访问域名，如 "insight.example.com"
  - {{BASE_DOMAIN}}   基础域名（无子前缀），如 "example.com"；Portainer 拼 portainer.${BASE_DOMAIN}
  - {{SERVER_IP}}     服务器 IP
  - {{DB_PASSWORD}}   数据库密码（从 GitHub Secrets 读取）
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

共享网络：{{APP_NETWORK}}（应用层；**agent-insight / Cogniforge 生产约定名是 `proxy`**）
公用网络：{{DB_NETWORK}}（数据层，默认名 `db-net`）
公用基础设施：/opt/databases/（所有项目共用）
边缘入口：/opt/docker/（Traefik + Portainer）
```

> **网络命名对照**：通用模板里的 `{{APP_NETWORK}}` 在本机房实际部署中 = **`proxy`**。
> 写 labels / compose 时跟仓库 `docker-traefik` 保持一致，不要混用 `app-net` 与 `proxy`。

---

## 二、目录规范

### 单仓场景（参考）

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

### 多仓单部署根目录（推荐：微服务 / 多端产品）

适用场景：一个产品拆成多个仓（前端 / 后端 / AI），但生产环境**只用一个部署根目录**集中所有 compose 文件。

```
/opt/project/                                       # ← 部署根
├── cogniforge/                                     # ← 品牌根 = 部署根（同名）
│   ├── docker-compose.yml                          #   后端 compose（来自 cogniforge 仓）
│   ├── docker-compose-ai.yml                       #   AI compose（来自 cogniforge-ai 仓）
│   ├── docker-compose-web.yml                      #   前端 compose（来自 cogniforge-web 仓）
│   ├── .env                                        #   后端私有配置（含主要业务密钥）
│   ├── .env.ai                                     #   AI 私有配置（覆盖公共 envs/llm.env 的部分项）
│   # ── 注意：前端 API 基址是镜像构建时写入的（Dockerfile ARG API_BASE，生产为空=同源）。
│   #    compose 只需要 DOMAIN（Traefik Host）。不要用 NUXT_PUBLIC_API_BASE 运行时覆盖。
│   #    详见 references/cogniforge.md
└── envs/                                           # ← 公共配置（部署根的同级目录）
    ├── db.env                                      #   PostgreSQL + Redis 连接（grep 提取自主仓 .env.example）
    └── llm.env                                     #   LLM Provider keys（grep 提取自主仓 .env.example）
```

**核心约定：服务器只负责拉镜像，不跑 git**

| 角色 | 做什么 |
|------|--------|
| **CI（GitHub Actions）** | 跑测试 → build 镜像 → push 到 ghcr |
| **服务器** | **只 `docker compose pull`**（镜像）+ `up -d`，不 `git clone`、不 `git pull` |
| **运维** | 首次部署手工把每个仓的 compose 文件**汇总到** `/opt/project/cogniforge/` |

**为什么这样设计**：
- ✅ 服务器只拉已签名镜像，安全攻击面小（不执行任意 git 内容）
- ✅ 所有服务的 compose、env、网络拓扑集中在**一个目录**，运维一目了然
- ✅ 一次 `cd /opt/project/cogniforge` 就能操作所有服务（pull / up / logs / ps）
- ✅ 跨服务共享配置（DB、AI keys）通过 `../envs/*.env` 引用，不进 git
- ✅ 镜像版本可追溯（每个 tag 对应一个 git commit）

**关键共享机制**：

| 共享机制 | 内容 | 谁能用 |
|---------|------|--------|
| `db-net` docker 网络 | PostgreSQL/Redis 容器名寻址 | 所有 join `db-net` 的服务 |
| `../envs/db.env`（相对部署根） | DB 连接字符串 | 通过 `env_file: ../envs/db.env` 引用 |
| `../envs/llm.env`（相对部署根） | LLM Provider keys | 通过 `env_file: ../envs/llm.env` 引用 |
| 共享网络 `cogniforge-net` | 服务间容器名寻址 | 所有后端/AI/前端互通 |

**为什么 `DEPLOY_PATH` 在三个仓的 CD 里都填同一个 `/opt/project/cogniforge`**：

因为部署机上三个 compose 文件**物理上都放在同一个目录**，CI 拉镜像时不需要 `cd` 到不同目录。每仓只是**不同的 compose 文件名**：

| GitHub 仓 | DEPLOY_PATH | COMPOSE_FILE |
|----------|-------------|--------------|
| `cogniforge` | `/opt/project/cogniforge` | `docker-compose.yml` |
| `cogniforge-ai` | `/opt/project/cogniforge` | `docker-compose-ai.yml` |
| `cogniforge-web` | `/opt/project/cogniforge` | `docker-compose-web.yml` |

**为什么这样设计**：

| 维度 | 单仓 | 多仓单部署根目录 |
|------|------|-----------------|
| 仓职责 | 一个仓含全部代码 | 每个仓只管自己（前端 / 后端 / AI） |
| 部署目录 | `/opt/project/<仓>/` | **`/opt/project/<品牌>/`**（三个仓共用） |
| compose 文件 | 单一 `docker-compose.yml` | 多个 `docker-compose-{role}.yml` |
| 启动命令 | `docker compose up -d` | `docker compose -f docker-compose-<role>.yml up -d` |
| 镜像版本 | 一锅炖 | 各仓独立 tag、独立发布 |

> **关键约定**：仓名 ≠ 部署根目录名。**部署根目录名 = 产品品牌名**（这里叫 `cogniforge`，但仓叫 `cogniforge`、`cogniforge-ai`、`cogniforge-web`）。仓代码最终都汇总到部署根目录下的不同 compose 文件中。

**首次部署步骤（一次性，运维手工做）**：

```bash
# 1. 创建部署根目录结构
mkdir -p /opt/project/envs
mkdir -p /opt/project/cogniforge
cd /opt/project/cogniforge

# 2. 拉取各仓代码（手工 git clone，只取 compose 文件 + Dockerfile 等）
git clone <cogniforge-repo-url> _src_cogniforge
git clone <cogniforge-ai-repo-url> _src_cogniforge-ai
git clone <cogniforge-web-repo-url> _src_cogniforge-web

# 3. 把各仓的 compose 文件汇总到部署根目录
cp _src_cogniforge/docker-compose.yml       ./docker-compose.yml
cp _src_cogniforge-ai/docker-compose-ai.yml ./docker-compose-ai.yml
cp _src_cogniforge-web/docker-compose-web.yml ./docker-compose-web.yml

# 4. 创建各服务独立 env（手动填值）
#    前端不需要 .env.web（环境变量少到 ≤5 个，已全部写在 docker-compose-web.yml 里）
cp _src_cogniforge/.env.example       ./.env
cp _src_cogniforge-ai/.env.example    ./.env.ai
vi ./.env ./.env.ai                  # 填 JWT_SECRET、ENCRYPTION_KEY、DOMAIN 等

# 5. 创建公共 env（跨服务共享）
#    从主仓 .env.example 提取 DB 字段生成 ../envs/db.env
grep -E '^POSTGRES_|^REDIS_' _src_cogniforge/.env.example > ../envs/db.env

#    从主仓 .env.example 提取 LLM 字段生成 ../envs/llm.env
grep -E '^(OPENAI|ANTHROPIC|OPENROUTER)_' _src_cogniforge/.env.example > ../envs/llm.env

#    手工填入真实值
vi ../envs/db.env    # 填 POSTGRES_PASSWORD
vi ../envs/llm.env   # 填 OPENAI_API_KEY / ANTHROPIC_API_KEY / OPENROUTER_API_KEY

chmod 600 ../envs/*.env ./.env*

# 6. 创建网络
docker network create cogniforge-net
docker network create db-net
```

**后续部署（CI 自动跑，服务器无 git 操作）**：

```yaml
# CI SSH 脚本核心逻辑
cd /opt/project/cogniforge                          # 切到部署目录（已有代码，不 git pull）
docker compose -f docker-compose.yml pull cogniforge # 只拉镜像，不跑 git
docker compose -f docker-compose.yml up -d --no-deps cogniforge
docker image prune -f --filter "until=72h"
```

**服务器永远不执行 `git pull`**：compose 文件夹下的 `.git/` 目录可能在仓里也可能不在，每次部署 CI/手工维护只需保证 compose 文件 + env_file 配置正确就行，代码版本由镜像 tag 决定。

### 共享 env 文件（env_file 引用）

`/opt/project/envs/` 是**同级目录**，不在任何仓里。存放**跨仓共享的配置**：

```bash
/opt/project/envs/
├── db.env          # 数据库连接（PG_HOST/PORT/USER/PASSWORD/DB + REDIS_HOST/PORT）
└── llm.env         # LLM Provider keys（OPENAI/ANTHROPIC/OPENROUTER keys）
```

**各仓 compose 用相对路径引用**：

```yaml
# cogniforge/docker-compose.yml（后端）
services:
  cogniforge:
    env_file:
      - ../envs/db.env        # ← 共享 DB 连接
      - .env                  # ← 本仓私有（JWT、ENCRYPTION_KEY、DOMAIN）
    environment:
      AI_SERVICE_URL: http://cogniforge-ai:8086
```

```yaml
# cogniforge-ai/docker-compose-ai.yml
services:
  cogniforge-ai:
    env_file:
      - ../envs/db.env        # ← DB 连接
      - ../envs/llm.env       # ← LLM Provider keys
      - .env                  # ← 本仓私有（LOG_LEVEL 等）
```

```yaml
# cogniforge-web/docker-compose-web.yml
# 静态 Nginx 镜像：API 地址在构建时写入（ARG API_BASE= 空 = 同源 /api/v1）。
# 运行时 environment 改不了已打包的 JS。DOMAIN 给 Traefik labels 用，写在同目录 .env。
services:
  cogniforge-web:
    image: ghcr.io/${IMAGE_NAMESPACE}/cogniforge/cogniforge-web:latest
    labels:
      - "traefik.http.routers.cogniforge-web.rule=Host(`${DOMAIN:?DOMAIN is required}`)"
```

**为什么 web 仓不需要独立 .env.web**：生产前端几乎只有 `DOMAIN`（Traefik）。API 基址是构建参数，不是容器 env。

**env_file 引用约定**：

| 服务的环境变量 | 放在哪 | 引用方式 |
|--------------|--------|----------|
| **DB 连接**（跨服务共享） | `../envs/db.env` | `env_file: ../envs/db.env` |
| **LLM keys**（跨服务共享） | `../envs/llm.env` | `env_file: ../envs/llm.env` |
| **后端密钥**（JWT、ENCRYPTION_KEY） | 本仓 `.env` | `env_file: .env` |
| **AI 私有覆盖** | 本仓 `.env.ai` | `env_file: .env.ai` |
| **前端变量**（≤5 个） | Traefik 用的 `DOMAIN` 放部署目录 `.env`；**API 基址走镜像 build-arg，不要写 compose environment** | `${DOMAIN:?...}` |

**${VAR:-default} vs ${VAR:?error msg}**：

- `${VAR:-default}` → 变量未设时用默认值（适合可选项）
- `${VAR:?error msg}` → 变量未设时**启动报错并退出**（适合必填项如 `DOMAIN`）

**为什么用相对路径**：每个仓 `git clone` 到自己的子目录，`../envs/` 自动定位到共享目录。

**本地开发兼容**（`../envs/` 在你电脑不存在）：

```yaml
env_file:
  - path: ../envs/db.env
    required: false            # ← 本地缺文件时跳过，不报错（Docker ≥ v2.24）
  - .env
```

---

## 三、公用数据库部署

> 每个项目共用一套 PostgreSQL + Redis，独立部署。
> 推荐版本与 agent-insight 对齐：PostgreSQL 18（`pgvector/pgvector:0.8.6-pg18-bookworm`）+ Redis 8（`redis:8.8.0-alpine`）。

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
  Reference: master（若仓库主分支是 main，则填 main）
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
# 单仓：docker compose up -d
# 多仓：docker compose -f docker-compose.yml -f docker-compose-ai.yml -f docker-compose-web.yml up -d
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
| `IMAGE_REGISTRY_TOKEN` | GitHub PAT（`write:packages`，仅兜底） |
| `POSTGRES_PASSWORD` | `{{DB_PASSWORD}}` |
| `JWT_SECRET` | `{{JWT_SECRET}}` |
| `ENCRYPTION_KEY` | `{{ENCRYPTION_KEY}}` |
| `LLM_API_KEY` | `{{LLM_API_KEY}}` |

默认认证建议：优先使用 GitHub Actions 自带 `${{ github.token }}` 登录 GHCR；`IMAGE_REGISTRY_TOKEN` 只在组织策略限制时兜底。

### 7.1.1 GitHub Variables（分支开关）

进入仓库 → **Settings → Secrets and variables → Actions → Variables**，可选添加：

| Variable | 内容 | 说明 |
|---------|------|------|
| `DEPLOY_PRIMARY_BRANCH` | `master` 或 `main` | 指定主部署分支；不填时自动判定：有 `master` 用 `master`，否则 `main` |

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
git push origin master
# 若你的主分支是 main，则 push main

# 或 GitHub → Actions → Deploy workflow → Run workflow
```

### 7.4 CD 分支策略 + GITHUB_TOKEN Demo（可直接复用）

```yaml
on:
  push:
    branches: [master, main]

permissions:
  contents: read
  packages: write

env:
  DEPLOY_PRIMARY_BRANCH: ${{ vars.DEPLOY_PRIMARY_BRANCH }}

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - id: branch_gate
        run: |
          set -e
          configured="${{ env.DEPLOY_PRIMARY_BRANCH }}"
          if [ -n "${configured}" ]; then
            [ "${configured}" = "master" ] || [ "${configured}" = "main" ] || { echo "::error::DEPLOY_PRIMARY_BRANCH must be master/main"; exit 1; }
            preferred="${configured}"
          elif git ls-remote --exit-code origin refs/heads/master >/dev/null 2>&1; then
            preferred="master"
          else
            preferred="main"
          fi
          [ "${GITHUB_REF_NAME}" = "${preferred}" ] && echo "should_deploy=true" >> "$GITHUB_OUTPUT" || echo "should_deploy=false" >> "$GITHUB_OUTPUT"
      - if: steps.branch_gate.outputs.should_deploy == 'true'
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ github.token }}
```

### 7.5 Compose 文件职责（防混淆）

| 文件 | 谁使用 | 作用 |
|------|--------|------|
| `docker-compose.yml` | 远程服务器、GitHub Actions | 生产编排；只拉镜像，不在服务器 build |
| `docker-compose.local.yml` | 本地开发机 | 本地覆盖；补 `build`，仅本地 `--build` 使用 |
| `env-docker-tag.example` | 团队协作（模板） | 记录 `DOCKER_TAG` 历史示例，不直接作为生产生效文件 |

命令对照：

```bash
# 远程/CD（只拉镜像）
docker compose --env-file .env -f docker-compose.yml pull
docker compose --env-file .env -f docker-compose.yml up -d

# 本地（需要构建）
docker compose --env-file .env -f docker-compose.yml -f docker-compose.local.yml up -d --build
```

DOCKER_TAG 约定（当镜像标签用 `${DOCKER_TAG}` 时）：

1. 生效值只放部署机 `.env`：`DOCKER_TAG=env-YYYYMMDD`
2. `.env` 只允许一行生效 `DOCKER_TAG`
3. 历史示例写到 `env-docker-tag.example`，避免在 `.env` 里堆多行历史

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

> 若 `traefik.yml` 挂载到自定义容器路径（例如 `./traefik/traefik.yml:/traefik.yml:ro`），
> 必须在 Traefik 服务里显式加 `command: ["traefik", "--configFile=/traefik.yml"]`。
> `--configFile` 的路径必须与 volume 的容器侧路径一一对应，否则 Traefik 会使用默认路径启动，常见现象是只看到 internal routers，业务域名返回 404。

### 8.5 健康检查：前端 Nginx ≠ 后端框架（必读）

> **方案 A（推荐）**：Traefik **只路由前端容器**；前端 Nginx 再反代 `/api` 到后端。  
> 域名能否访问，取决于 **前端容器** 是否 `healthy` 并被 Traefik 注册，**不等于**后端应用是否存活。

#### 不同技术栈的「原生 / 约定」健康路径

| 技术栈 | 健康机制 | 典型路径 | 说明 |
|--------|----------|----------|------|
| **Nginx 前端**（静态站 / SPA） | 自配 `location = /health` | `/health`（监听 **80**） | **不是**框架自带；写在 `nginx.conf` 里 `return 200` |
| **Spring Boot** | **官方 Actuator**（`spring-boot-starter-actuator`） | **`/actuator/health`**（业务端口，如 9280） | 原生能力；**不是** `/health`（除非你自己改了 `management.endpoints.web.base-path`） |
| **Go（Gin 等）** | **项目自建**路由，无统一官方标准 | 常见自建 **`/health`**（如 cogniforge） | 框架不自带 Actuator；看仓库 `router` 里是否注册了 `/health` |
| **Python FastAPI** | 项目自建 | 常见 `/health` | 同上，看代码 |

> agent-insight：后端是 **Java / Spring Boot** → 探 **`9280/actuator/health`**。  
> 前端 compose 里的 `http://127.0.0.1:80/health` 只针对 **Nginx 容器**，**不要**改成 actuator。

| 容器角色 | 典型进程 | 健康检查目标 | 正确示例 |
|---------|----------|--------------|----------|
| **Web 前端** | Nginx（`nginx:alpine`） | **本容器** 80 + Nginx `/health` | `wget -q --spider http://127.0.0.1:80/health` |
| **Go 后端** | Gin 等 | **本容器** 业务端口 + **项目自建** `/health` | `wget -qO- http://127.0.0.1:8080/health` |
| **Spring Boot 后端** | Actuator | **本容器** 业务端口 + **原生** `/actuator/health` | `curl -f http://127.0.0.1:9280/actuator/health` |
| **Python/FastAPI** | uvicorn | **本容器** 业务端口 + 项目自建路径 | 按项目实际路径 |

**禁止混用：**

- ❌ 在 **frontend** 容器里探测 `9280` / `actuator/health`（容器内没有 Spring，必 fail → Traefik 过滤 → 域名 404）
- ❌ 在 **backend** 容器里探测 `80` / Nginx `/health`（后端不是 Nginx）
- ❌ 以为「Java 项目所以 frontend 的 `/health` 不对」——那是 Nginx 的检查，和 Java 无关
- ❌ 前端 health 端口写成 Node 开发端口 `3000`（生产 Nginx 是 `80`）
- ❌ Spring 写成 `/health` 却未改 Actuator 配置（默认是 **`/actuator/health`**）

**方案 A 示例（compose 片段）：**

```yaml
# ── 前端：Traefik 入口；health 只查本容器 Nginx（与后端是不是 Java 无关）──
frontend:
  expose: ["80"]
  networks: [proxy, {{APP_NETWORK}}]
  labels:
    - "traefik.enable=true"
    - "traefik.docker.network=proxy"
    - "traefik.http.routers.app-web.rule=Host(`{{DOMAIN}}`)"
    - "traefik.http.routers.app-web.entrypoints=websecure"
    - "traefik.http.routers.app-web.tls.certresolver=letsencrypt"
    - "traefik.http.services.app-web.loadbalancer.server.port=80"
  healthcheck:
    # BusyBox wget：禁止 --bind-address / --no-verbose / --tries
    # 这是 Nginx /health，不是 Spring Actuator
    test: ["CMD", "wget", "-q", "--spider", "http://127.0.0.1:80/health"]
    interval: 15s
    timeout: 5s
    retries: 3
    start_period: 10s

# ── 后端：内部调用；无 Traefik labels（或不 enable）──
backend:
  expose: ["9280"]   # 或 Go: 8080
  networks: [{{APP_NETWORK}}, {{DB_NETWORK}}]
  # Spring Boot：官方 Actuator（原生）
  healthcheck:
    test: ["CMD", "curl", "-f", "http://127.0.0.1:9280/actuator/health"]
    interval: 30s
    timeout: 5s
    retries: 3
    start_period: 60s
  # Go：项目自建 /health（非框架统一标准）
  # healthcheck:
  #   test: ["CMD", "wget", "-qO-", "http://127.0.0.1:8080/health"]
```

**Nginx 须有精确 location**（避免 SPA `try_files` 误判健康）：

```nginx
location = /health {
    access_log off;
    default_type text/plain;
    return 200 "OK\n";
}
```

**和 404 的关系（实战链路）：**

```
浏览器 → Traefik → frontend:80（必须 healthy）→ Nginx /api/* → backend
                    ↑
                    这里 fail = 域名 404（即使 backend /actuator/health 已 OK）
```

DEBUG 日志见 `Filtering unhealthy or starting container` 时：先修 **被 Traefik enable 的那个容器** 的 healthcheck，不是先改后端框架。

---

## 九、常见故障排查

### ❌ 404 — Traefik 没匹配到路由

```bash
# 0. Docker 29 + 旧 Traefik：先看是否 API 过旧（provider 根本起不来）
docker exec traefik traefik version   # 需要 ≥ 3.6.1
docker logs traefik --tail 50 | grep -i '1.24 is too old'

# 查看 Traefik 日志
docker logs traefik --tail 50

# 查看 Traefik 发现的路由
curl http://localhost:8080/api/http/routers

# 确认容器有 traefik.enable=true，且在 proxy 网络
docker inspect {{PROJECT_NAME}} | grep -A 5 Labels
docker inspect {{PROJECT_NAME}} --format '{{json .NetworkSettings.Networks}}'
```

> **Traefik v3 会过滤 `unhealthy` / `starting` 容器**（DEBUG：`Filtering unhealthy or starting container`）。  
> 域名 404 时优先查 **Traefik 启用的前端容器** 是否 healthy，不要先把问题归到 Spring Boot / Go。  
> 详见 **§8.5 健康检查：前端 Nginx ≠ 后端框架**。
>
> healthcheck 常见坑（Alpine / BusyBox `wget`）：
> - 端口写错（Nginx 是 `80`，勿写 `3000`）
> - 前端错误地探后端 `actuator/health` 或 `9280`
> - 用不支持的参数：`--bind-address`、`--no-verbose`、`--tries`
> - 正确示例：前端 `wget -q --spider http://127.0.0.1:80/health`；Spring `curl -f http://127.0.0.1:9280/actuator/health`；Go `wget -qO- http://127.0.0.1:8080/health`
>
> Traefik 本身：
> - 镜像必须 **≥ v3.6.1**（Docker Engine 29）
> - 自定义 `:/traefik.yml` 挂载必须 `command: ["traefik", "--configFile=/traefik.yml"]`

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

**根因**：前后端不同源。**解决（方案 A）**：前端请求当前域名 `/api/*`，由前端 Nginx 反代到后端。

### ❌ 公网站点请求 localhost:8080（ERR_CONNECTION_REFUSED）

**症状**：打开 `https://{{DOMAIN}}` 登录失败；本机一启动后端又好了。控制台是：

```
POST http://localhost:8080/api/v1/auth/login  net::ERR_CONNECTION_REFUSED
```

**根因**：JS 在**访客浏览器**里执行。`localhost` = 访客电脑，不是 SSH 那台服务器。  
静态前端把 `http://localhost:8080` 打进包，或把 `API_BASE` 写成 `/api` 再拼 `/api/v1`，都会错。

**解决**（Cogniforge 详见 `references/cogniforge.md`）：

- 生产 `API_BASE` 为空字符串（同源 `/api/v1/...`）
- 本地 `pnpm dev` 才用 `http://localhost:8080`
- 禁止在业务代码里写死 localhost；改完必须**重建前端镜像**（改 compose env 无效）
- 验证：无痕窗口打开域名，Network 里应是 `https://{{DOMAIN}}/api/v1/...`

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
# 单仓
docker compose pull && docker compose up -d
# 多仓：按角色独立更新
docker compose -f docker-compose-ai.yml pull && docker compose -f docker-compose-ai.yml up -d
docker compose -f docker-compose-web.yml pull && docker compose -f docker-compose-web.yml up -d
```

### 备份数据库

```bash
docker exec db-postgres pg_dump -U postgres {{PROJECT_NAME}} \
  > backup_$(date +%Y%m%d).sql
```

---

## 十二、agent-insight 专项（仓库 `docker-traefik/`）

> 详细步骤与路由表见 **`references/agent-insight.md`**。这里只列硬约束，避免与通用章节冲突时选错。

### 12.1 三层目录（固定）

```
/opt/docker/                     # Traefik v3.6.1+ + Portainer
/opt/databases/                  # mysql + mongodb + redis + pgsql(pgvector)
/opt/project/
├── envs/{db,llm}.env            # compose 通过 ../envs/*.env 引用
└── agent-insight/               # 应用 compose；.env 放 DOMAIN / DATA_ROOT
    └── data/                    # DATA_ROOT 默认挂载点
```

### 12.2 路由方案（三选一，容器名冲突不可并存）

| Compose 文件 | 模式 |
|--------------|------|
| `docker-compose.yml` | **A 推荐**：只暴露 frontend；Nginx 代理 `/api` → backend:9280 |
| `docker-compose.b-traefik-api.yml` | B：Traefik 同域 `PathPrefix(/api)` |
| `docker-compose.c-separate-domains.yml` | C：`FRONTEND_DOMAIN` + `API_DOMAIN` |

### 12.3 端口与镜像

- 后端 **9280**，前端 **80**（仅 `expose`，不映射宿主机）
- 镜像：`ghcr.io/${IMAGE_NAMESPACE}/agent-insight/{backend,frontend}:latest`
- 服务器只 pull 镜像，不在生产机 `git pull` 构建

### 12.4 Traefik / Portainer

- Traefik 镜像必须 **≥ v3.6.1**（Docker Engine 29 兼容；否则 Docker provider 挂掉全站 404）
- Portainer：`Host(\`portainer.${BASE_DOMAIN}\`)`，`/opt/docker/.env` 只写基础域名
- 优先 Docker Labels；`traefik.yml` 的 file provider 可关，避免与 Labels 双写同一路由

### 12.5 常见坑

| 坑 | 正确做法 |
|----|---------|
| labels 里 `${DOMAIN}` 不替换 | 写在 compose 同级 `.env` 或 Portainer Stack env，不要指望 `environment:` |
| `env_file: ../envs/db.env` 找不到 | 文件放 `/opt/project/envs/`，不是 `agent-insight/envs/` |
| `/opt/app` vs `/opt/project` | 统一 **`/opt/project`** |
| PG 18 挂载旧路径 | `./pgsql/data:/var/lib/postgresql` |

---

## 十三、Cogniforge 专项（三仓 / 方案 A）

> 详细约定见 **`references/cogniforge.md`**。这里只列硬约束。

- 部署根：`/opt/project/cogniforge/`（三个 compose 放一起）
- 路由：**方案 A** — Traefik 只挂 `cogniforge-web`；Nginx `location /api/` → `cogniforge:8080`
- 前端镜像是静态 Nginx：`API_BASE` 必须 **build-arg**，生产为空（同源 `/api/v1`）
- **禁止** JS 写死 `http://localhost:8080`；禁止 compose 用 `NUXT_PUBLIC_API_BASE` 幻想运行时改地址
- 公网 `ERR_CONNECTION_REFUSED localhost:8080` = 浏览器打到了访客电脑，重建 web 镜像

---

## 配套文件

| 文件 | 用途 |
|------|------|
| `references/agent-insight.md` | **agent-insight / docker-traefik 专项部署真相** |
| `references/cogniforge.md` | **Cogniforge 前端 API_BASE / 同源反代 / 公网打到 localhost 专项** |
| `references/databases/docker-compose.yml` | 公用数据库 compose 模板（PG18 pgvector + Redis8） |
| `references/databases/databases.env.example` | 数据库环境变量模板 |
| `assets/traefik-stack.yml` | Portainer 部署 Traefik compose（需 ≥ v3.6.1） |
| `assets/deploy.sh` | 一键部署脚本（需填入真实值后使用） |

---

## 模板变量速查

| 变量 | 示例值 | 来源 |
|------|--------|------|
| `{{PROJECT_NAME}}` | `myapp` | 用户指定（部署目录名 = 品牌名，不是仓名） |
| `{{DEPLOY_DIR}}` | `/opt/project/{{PROJECT_NAME}}` | 部署根目录（多仓共用） |
| `{{COMPOSE_FILE}}` | `docker-compose.yml` 或 `docker-compose-<role>.yml` | 多仓场景下加 `-role` 后缀 |
| `{{ENV_FILE}}` | `.env` 或 `.env.<role>` | 多仓场景下加 `.<role>` 后缀 |
| `{{DOMAIN}}` | `myapp.example.com` | 用户指定（完整 Host） |
| `{{BASE_DOMAIN}}` | `example.com` | Portainer 等子域拼接用 |
| `{{SERVER_IP}}` | `your.server.ip` | GitHub Secrets |
| `{{SSH_USER}}` | `deploy` | 用户指定 |
| `{{SSH_PORT}}` | `22` | GitHub Secrets |
| `{{DB_PASSWORD}}` | `xxx` | GitHub Secrets |
| `{{JWT_SECRET}}` | `xxx` | GitHub Secrets |
| `{{ENCRYPTION_KEY}}` | `xxx` | GitHub Secrets（生成后永不换） |
| `{{LLM_API_KEY}}` | `sk-xxx` | GitHub Secrets |
| `{{EMAIL}}` | `admin@example.com` | Let's Encrypt 注册邮箱 |
| `{{APP_NETWORK}}` | `proxy`（本机房） | agent-insight / Cogniforge 固定用 `proxy`；通用模板也可用 `{{PROJECT_NAME}}-net` |
| `{{DB_NETWORK}}` | `db-net` | 固定：所有项目共用 |
| `{{VOLUME_UPLOADS}}` | `myapp-uploads` | 用户指定（建议 `{{PROJECT_NAME}}-uploads`） |
| `{{PORT}}` | `8080` | 项目 docker-compose.yml |
| `{{REGISTRY}}` | `ghcr.io/username` | GitHub Packages |

