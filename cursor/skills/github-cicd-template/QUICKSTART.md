# GitHub CI/CD 模板 — 速查卡

## 两类文件，先认清楚

| 文件名以...开头 | 是什么 | 跑在哪 |
|------------------|--------|--------|
| `ci-*.yml` | **GitHub Actions workflow（CI 流程）** | 云端 Ubuntu VM |
| `ci-cd-*.yml` | **GitHub Actions workflow（CD 流程）** | 云端 Ubuntu VM |
| `compose-stack-*.yml` | **服务编排**（真正的 docker-compose.yml） | 你的服务器 |

> **CI 和 CD 必须分开**，职责单一，状态互不干扰。

## 5 个文件，按需取用

| 场景 | 用 |
|------|------|
| **必选** Spring Boot + 前端，测试验证 | `assets/ci-template.yml`（CI） |
| Spring Boot + 前端 + 单机部署 | `assets/ci-cd-workflow-template.yml`（CD）+ `assets/compose-stack-template.yml` |
| K8s 集群部署 | `assets/ci-cd-k8s-template.yml` |
| 纯静态前端（VitePress/Hugo） | `assets/ci-cd-static-template.yml` |

## CI 模板：只需 env，无需 secret

复制 `assets/ci-template.yml` → `.github/workflows/ci.yml`，改顶部 `env`：

```yaml
env:
  # 后端
  BACKEND_DIR: agent-insight-server
  JAVA_VERSION: '21'
  DB_NAME: agent_insight

  # 前端
  FRONTEND_DIR: agent-insight-web
  NODE_VERSION: '22'   # GitHub 推荐；禁止从旧项目抄 20

  # 服务镜像版本（与部署环境一致）
  MYSQL_IMAGE: mysql:8.4
  MONGODB_IMAGE: mongo:8.3
  REDIS_IMAGE: redis:8.8.0-alpine

  # 初始化脚本（相对于仓库根）
  SQL_INIT_SCRIPT: fixtures/mysql/init.sql
  MONGODB_INIT_SCRIPT: fixtures/mongodb/init.js

  # E2E
  E2E_PORT: 3010
```

| 变量 | 说明 |
|------|------|
| `BACKEND_DIR` | 后端代码目录 |
| `FRONTEND_DIR` | 前端代码目录 |
| `JAVA_VERSION` / `NODE_VERSION` | JDK / Node 版本 |
| `MYSQL_IMAGE` / `MONGODB_IMAGE` / `REDIS_IMAGE` | **与部署环境保持一致**，版本不对会导致测试通过但部署失败 |
| `SQL_INIT_SCRIPT` | 建表 SQL（相对仓库根），不存在则跳过 |
| `MONGODB_INIT_SCRIPT` | MongoDB 初始化脚本，不存在则跳过 |
| `E2E_PORT` | Playwright 测试时 Vite dev server 端口 |

> **CI 不需要配 secret**，不需要 SSH、不需要镜像 token、不需要服务器 IP。只需确保 SQL/MongoDB 初始化脚本路径正确。

## CD 模板：env + secrets

复制 `assets/ci-cd-workflow-template.yml` → `.github/workflows/cd.yml`，改 env + 配 secrets。

**CD 默认不拷贝 compose**：服务器自己维护 `docker-compose.yml` 和 `.env`。Demo CD 会 echo「不拷贝 compose 文件到远程机器」，SCP 步骤注释保留。远程只做 `docker login` → `pull` → `up`。

Traefik：路由器必须写 `service=`。没写时 Traefik 找和路由器同名的服务。Demo 里 `wifi-tie-admin` 路由 vs `wifi-tie-admin-web` 服务会对不上，公网 404。改 labels 只能改服务器上的 compose。详见 skill「坑 2.2」。

裸域 + www：Demo 默认不启用，compose 里注释保留 `Host(`${DOMAIN}`) || Host(`www.${DOMAIN}`)`，需要时再解开。

### CD env（写在 workflow 顶部）

```yaml
env:
  IMAGE_REGISTRY: ghcr.io
  IMAGE_NAMESPACE: ${{ github.repository_owner }}
  IMAGE_PROJECT: agent-insight           # ← 改成你的项目名
  COMPOSE_FILE: docker-compose.yml
  COMPOSE_SERVICES: agent-insight-backend agent-insight-frontend
```

### CD secrets（配在 GitHub Secrets）

```bash
# ── SSH 连接（4 个，按顺序填）──
gh secret set DEPLOY_HOST        --body "{{SERVER_IP}}"         --env production
gh secret set DEPLOY_USER        --body "deploy"                  --env production
gh secret set DEPLOY_SSH_PORT    --body "22000"                   --env production
gh secret set DEPLOY_SSH_KEY     < ~/.ssh/github_actions          --env production

# ── 部署路径（1 个，多环境切换时有用，所以放 secret）──
gh secret set DEPLOY_PATH        --body "/opt/docker/agent-insight" --env production

# ── 镜像仓库登录 token（1 个，对应镜像仓库的账号密码）──
gh secret set IMAGE_REGISTRY_TOKEN --body "ghp_xxxxxxxxxxxx"     --env production
```

| Secret | 怎么拿 |
|--------|--------|
| `DEPLOY_HOST` | 服务器 `ip addr` 看公网 IP |
| `DEPLOY_USER` | 服务器 `adduser deploy` 新建（**非 root**） |
| `DEPLOY_SSH_PORT` | 服务器 sshd 端口，默认 `22`（你的是 `22000`） |
| `DEPLOY_SSH_KEY` | `ssh-keygen -t ed25519` 后取**私钥全文**（`~/.ssh/github_actions`），含 `BEGIN/END` 行 |
| `DEPLOY_PATH` | 服务器上的项目根目录（compose 文件所在目录的父级） |
| `IMAGE_REGISTRY_TOKEN` | GitHub Settings → Developer settings → PAT → 勾 `write:packages` |

> **⚠️ 私钥换行符陷阱**：GitHub Secret UI 会 strip 末尾 `\n`，导致 `ssh-keygen -l` 报错 `invalid format`。模板里用 `printf '%s\n'` 写文件兜底。

**`--env xcy` 是什么？**

`xcy` 是 GitHub 的 **environment** 名（部署环境分组），不是 yaml 里的 env 变量。两层语义：

| 写法 | 含义 |
|------|------|
| `gh secret set ... --env xcy` | 把 secret 配到 `xcy` 这个 environment 下 |
| workflow 里 `environment: xcy` | 触发时使用这个 environment 的 secret |

**一台云服务器带多个项目**：按"服务器名"建 environment，所有项目共享一套 SSH/registry 配置：

```bash
# xcy 是你云服务器的名字，所有仓库共用
gh secret set DEPLOY_HOST --body "{{SERVER_IP}}" --env xcy
gh secret set DEPLOY_SSH_KEY < ~/.ssh/github_actions --env xcy

# 不同服务器，新建不同 environment
gh secret set DEPLOY_HOST --body "10.0.1.5" --env aliyun-projectA
gh secret set DEPLOY_HOST --body "10.0.2.8" --env aliyun-projectB
```

workflow 里要对应（模板默认 `production`）：
```yaml
jobs:
  deploy:
    environment: xcy   # ← 改成你的 environment 名
```

## 5 个常见坑

| 症状 | 解决 |
|------|------|
| `Permission denied (publickey)` / `invalid format` | 用 `printf '%s\n'` 写私钥（模板已含），不要 echo / heredoc |
| `image not found` after push | PAT 必须 `write:packages`，或把 ghcr 包设 public |
| 服务启动后立即被 kill | compose 加 `start_period: 60s` |
| `inputs.service` 为 null | 加 `|| == ''` 兜底 |
| 构建慢 / 镜像大 | `cache-from: type=gha` + multi-stage + alpine |
| CD 覆盖了服务器 compose / SCP Permission denied | 不要解开 SCP；compose 由服务器本地维护，CD 只拉镜像 |
