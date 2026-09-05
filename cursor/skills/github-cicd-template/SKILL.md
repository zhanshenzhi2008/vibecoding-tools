---
name: github-cicd-template
description: 生成 GitHub Actions CI/CD 工作流模板，覆盖 Spring Boot + React/Vue/Angular + Docker + 远程服务器部署场景。当用户需要"建 CI/CD"、"配 GitHub Actions 部署"、"自动部署到服务器"、"写 docker-compose + workflow"，或排查静态前端把 localhost 打进镜像、公网请求 localhost:8080 时使用本 skill。
---

# GitHub Actions CI/CD 模板生成器

> 一套**参数化**的 CI/CD 模板，适配任何 Spring Boot + 前端 + Docker + 远程服务器项目。
> 用法和 `package.json` 模板类似：复制 → 改变量 → 用。

---

## 何时使用

| 用户说 | 用本 skill |
|--------|-----------|
| "帮我建 GitHub Actions 部署" | ✅ |
| "配一下 CI/CD，push 到 master/main 自动部署" | ✅ |
| "我想 push 后自动 build docker 镜像" | ✅ |
| "服务器是阿里云 / 自建机，怎么自动部署" | ✅ |
| "我想跑 GitHub Actions 自动发布" | ✅ |

---

## 核心思想（为什么这套模板能复用）

把 CI/CD 拆成 **4 个可参数化的层**：

```
┌─────────────────────────────────────────────────────┐
│ 1. 触发层（WHEN）    push / PR / tag / manual      │
│ 2. 构建层（WHAT）    backend / frontend / all      │
│ 3. 制品层（OUTPUT）  ghcr.io / aliyun / 自建       │
│ 4. 部署层（WHERE）   ssh / k8s / docker-compose    │
└─────────────────────────────────────────────────────┘
```

每层用 **environment variable + secret** 表达，**不**在 yaml 里写死：

**硬规则：CD 默认不向远程拷贝 compose / `.env`**

- 远程机器只拉镜像并启动：`docker login` → `docker compose pull` → `docker compose up -d`
- `docker-compose.yml` 和 `.env` 由服务器本地维护（运维首次手工放好）
- **禁止**默认用 SCP/rsync 覆盖远程 compose，避免把仓库改动误配到生产
- Demo CD（`assets/ci-cd-workflow-template.yml`）必须：部署前 `echo` 说明不拷贝；SCP 步骤整段**注释保留**，需要时再解开
- 静态站模板的 `rsync` 是前端产物，不是 compose，不受这条约束

**硬规则：命令行 / CD 拉起的容器要给 Portainer Restricted 用户打权限 label**

- Label：`io.portainer.accesscontrol.users=<Portainer 用户名>`
- 不写则：页面里重启还在，`docker compose --force-recreate` 后 Restricted 用户看不到
- 每个业务服务都要写；模板见 `assets/compose-stack-template.yml` 注释；通说见 `deploy` skill §5.4
- CD **不**拷贝 compose，改 label 必须改**服务器本地**文件后再重建

**硬规则：前端 Node 默认 22（GitHub 推荐）**

- CI：`NODE_VERSION: '22'`（`assets/ci-template.yml` / `assets/ci-cd-static-template.yml` 已写死 22）
- 前端 Dockerfile：`FROM node:22-alpine`，**禁止**从旧项目抄 `node:20-alpine` / `NODE_VERSION: '20'`
- `package.json` → `engines` 可以继续写 `node >=20`、`pnpm >=8`（22/9 本来就满足，不必为了对齐去改）
- 本机可以用 22 或更新的 LTS（如 24）；CI 和镜像必须是 22，不要各写各的

**硬规则：Action 本体不要用 `@v4`（Node 20 运行时已弃用）**

- 这和 `NODE_VERSION: '22'` **不是一回事**。`NODE_VERSION` 是项目构建用的 Node；`checkout@v4` 是 GitHub 跑这个工具自己的 Node
- 警告 `Node.js 20 is deprecated... actions/checkout@v4` 就是这个，升 major 即可
- 默认：`actions/checkout@v6`、`actions/setup-node@v6`、`actions/cache@v5`、`pnpm/action-setup@v6`

**env（公开配置，写在 workflow 顶部）**

| 维度 | 变量 | 默认值 | 说明 |
|------|------|--------|------|
| 镜像仓库 | `IMAGE_REGISTRY` | `ghcr.io` | 也可填 `registry.cn-hangzhou.aliyuncs.com` |
| 镜像命名空间 | `IMAGE_NAMESPACE` | `${{ github.repository_owner }}` | ghcr.io 用户名 = owner |
| 镜像项目名 | `IMAGE_PROJECT` | `YOUR_PROJECT_NAME` | 项目标识 |
| 部署目录 | `DEPLOY_PATH` | `/opt/project/YOUR_PROJECT_NAME` | 服务器上的项目根目录 |
| Compose 文件名 | `COMPOSE_FILE` | `docker-compose.yml` | 相对 `DEPLOY_PATH` |
| 要更新的服务 | `COMPOSE_SERVICES` | `your-backend your-frontend` | compose 里的 service 名，空格分隔 |

**secret（敏感信息，配在 GitHub Secrets 里）**

| 维度 | 变量 | 必填 | 说明 |
|------|------|------|------|
| 服务器 | `DEPLOY_HOST` | **是** | 公网 IP / 域名 |
| SSH 用户 | `DEPLOY_USER` | **是** | 推荐非 root（deploy） |
| SSH 端口 | `DEPLOY_SSH_PORT` | 否（默认 22） | 自定义 SSH 端口时填 |
| SSH 私钥 | `DEPLOY_SSH_KEY` | **是** | `ssh-keygen -t ed25519` 生成 |
| Registry token | `IMAGE_REGISTRY_TOKEN` | 否（兜底） | PAT with `write:packages` 权限（默认优先用 `GITHUB_TOKEN`） |

---

## 模板清单（5 个）

| 文件 | 是什么 | 放哪里 | 用途 |
|------|--------|--------|------|
| `assets/ci-template.yml` | **GitHub Actions workflow**（CI 流程，测试验证） | 本地 → `.github/workflows/ci.yml` | **必选**：后端单元测试 + 前端单元测试 + 前端 E2E 测试。**CI 和 CD 必须分开**，职责单一、状态清晰 |
| `assets/ci-cd-workflow-template.yml` | **GitHub Actions workflow**（CD 流程，部署上线） | 本地 → `.github/workflows/cd.yml` | **推荐**：build 镜像 → SSH **只拉镜像** → `docker compose up`。默认不拷贝 compose。90% 项目首选 |
| `assets/compose-stack-template.yml` | **服务编排定义**（docker compose 文件） | 服务器 → `/opt/project/<repo>/docker-compose.yml` | 给 CD 模板配套（健康检查 / depends_on / 卷挂载） |
| `assets/ci-cd-k8s-template.yml` | **GitHub Actions workflow** | 本地 → `.github/workflows/cd-k8s.yml` | build 镜像 → `kubectl set image`。有 K8s 集群时用 |
| `assets/ci-cd-static-template.yml` | **GitHub Actions workflow** | 本地 → `.github/workflows/cd-static.yml` | build 前端 → rsync 到 nginx。纯前端静态站用 |

> **CI 和 CD 必须分开**，不要把 test 塞进 CD workflow 里。分开的好处：PR 阶段只跑 test（快，不触发构建），主分支阶段（`master`/`main`）才 build + 部署；状态页上 CI 和 CD 的通过/失败独立显示，不会互相干扰。

---

## 标准使用流程

### 第 1 步：选模板

判断项目类型：

```
Spring Boot + React/Vue + 一台服务器？
  └─→ ci-cd-workflow-template.yml ✅（首选）+ compose-stack-template.yml

已经是 K8s / Docker Swarm 集群？
  └─→ ci-cd-k8s-template.yml

只有静态前端？
  └─→ ci-cd-static-template.yml
```

### 第 2 步：准备 4 个 GitHub Secret（默认方案）

进仓库 → Settings → Secrets and variables → Actions → New repository secret：

| Secret 名 | 内容 | 怎么获取 |
|-----------|------|----------|
| `DEPLOY_HOST` | 服务器公网 IP / 域名 | `ip addr` 或服务商控制台 |
| `DEPLOY_USER` | SSH 用户名（推荐非 root） | 服务器新建 `deploy` 用户 |
| `DEPLOY_SSH_PORT` | SSH 端口（默认 22，可选） | 服务端 sshd 配置 |
| `DEPLOY_SSH_KEY` | 私钥全文 | `ssh-keygen -t ed25519 -C "github-deploy"` |

**或者用 `gh` CLI 一把梭**：

```bash
gh secret set DEPLOY_HOST          --body "156.226.176.141"     --env production
gh secret set DEPLOY_USER          --body "deploy"              --env production
gh secret set DEPLOY_SSH_PORT      --body "22000"               --env production
gh secret set DEPLOY_SSH_KEY       < ~/.ssh/github_actions      --env production
```

PAT 兜底（仅当组织权限策略导致 `GITHUB_TOKEN` 拉取 GHCR 失败时）：

```bash
gh secret set IMAGE_REGISTRY_TOKEN --body "ghp_xxxxxxxxxxxx" --env production
```

> **env vs secret 区分原则**：
> - 公开信息（registry 地址、镜像命名空间）→ **env**（写在 workflow 里）
> - 敏感凭据（token、私钥、密码）→ **secret**（GitHub Secrets 里）
>
> 区分标准：能不能写进 git commit 让所有人看到？能 → env，不能 → secret。

**`gh secret set --env xxx` 是什么？**

`--env` 后面跟的是 GitHub 的 **environment**（部署环境分组），不是我们说的 env 变量。两层语义：

| 维度 | 你说的 `env` | 实际含义 |
|------|-------------|----------|
| `gh secret set ... --env xcy` | GitHub **environment** 名 | `Settings → Environments → xcy` 下的 secret 分组 |
| workflow 里的 `environment: production` | 同上 | 触发时使用对应分组的 secret |
| workflow 里的 `env: IMAGE_REGISTRY: ghcr.io` | 工作流变量 | 写在 yaml 顶部的纯字符串 |

**environment 的好处：多仓库共用一套部署配置**

你这种"一台云服务器带多个项目"的场景，推荐按"云服务器名"或"公司-项目-环境"建 environment：

```bash
# 一台云服务器，对应一个 environment，所有仓库共享
gh secret set DEPLOY_HOST --body "156.226.176.141" --env xcy
gh secret set DEPLOY_USER --body "deploy" --env xcy
gh secret set DEPLOY_SSH_KEY < ~/.ssh/github_actions --env xcy

# 不同服务器/项目，新建不同的 environment
gh secret set DEPLOY_HOST --body "10.0.1.5" --env aliyun-projectA
gh secret set DEPLOY_HOST --body "10.0.2.8" --env aliyun-projectB
```

**environment 命名建议**：

| 模式 | 例子 | 适用 |
|------|------|------|
| 云服务器名 | `xcy` `aliyun-shanghai` `aws-tokyo` | 一个人管多台服务器，每台一个 environment |
| 公司-项目-环境 | `acme-blog-prod` `acme-blog-staging` | 多项目共用云，每项目一 environment |
| 仅环境 | `production` `staging` | 单项目多环境 |

**workflow 里要对应**（模板里默认 `production`）：

```yaml
jobs:
  deploy:
    environment: production   # ← 改这里匹配你的 environment 名
```

**多仓库共享同一个 environment**：

GitHub environment 只能在单个仓库下，但有一个变通：
1. 在每个仓库都执行一次 `gh secret set --env xcy`（命令相同）
2. 或者建一个 organization-level secret（GitHub Team/Enterprise 计划支持，免费版只能仓库级）

**生成 SSH key 的标准做法**（服务器端）：

```bash
# 1. 在服务器上生成 key pair
ssh-keygen -t ed25519 -C "github-deploy" -f ~/.ssh/github_deploy

# 2. 把公钥加到 authorized_keys
cat ~/.ssh/github_deploy.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys

# 3. 把私钥全文（含 BEGIN/END 行）复制到 GitHub Secret
cat ~/.ssh/github_deploy
```

**⚠️ 私钥末尾换行符被 GitHub Secret UI 截断（最常见坑）**

GitHub Secret 输入框在粘贴时**会自动 strip 末尾换行符**，导致私钥文件少一个 `\n`。OpenSSH 私钥规范要求文件以换行符结尾，缺失时：

- `ssh-keygen -l -f key` 报错：`invalid format`
- `ssh` 连接报错：`Permission denied (publickey)` / `key_load_public: No such file or directory`

**解法**：Workflow 里用 `printf '%s\n'` 写文件（模板已用），不要用 `echo`，因为 `echo` 在某些 runner 里会把 `\n` 追加两次：

```bash
# ✅ 正确：确保末尾有且仅有一个换行符
printf '%s\n' "${{ secrets.DEPLOY_SSH_KEY }}" > ~/.ssh/deploy_key

# ❌ 错误：echo 会追加额外的换行（macOS bash 行为不同）
echo "${{ secrets.DEPLOY_SSH_KEY }}" > ~/.ssh/deploy_key

# ❌ 错误：直接重定向不保证换行
cat <<< "${{ secrets.DEPLOY_SSH_KEY }}" > ~/.ssh/deploy_key
```

**验证私钥格式是否正确**（模板里已含 fingerprint 校验 step）：

```bash
# 私钥字节数应该在 100-2000 之间（ed25519 通常 ~400 字节）
wc -c ~/.ssh/deploy_key

# 如果正常，会输出 fingerprint（不报错）
ssh-keygen -l -f ~/.ssh/deploy_key
# 输出类似：256 SHA256:xxxxxxxxxxx github-deploy (ED25519)
```

如果 `ssh-keygen -l` 报错 `invalid format`，说明 GitHub Secret 里私钥末尾换行符丢失，用 `printf '%s\n'` 修 workflow 文件即可。

### 第 3 步：复制 CI 模板（必选）

```bash
mkdir -p .github/workflows
cp assets/ci-template.yml .github/workflows/ci.yml
```

打开 `assets/ci-template.yml`，改顶部 `env` 块：

```yaml
env:
  # 后端配置
  BACKEND_DIR: agent-insight-server         # ← 改 1：后端代码目录
  JAVA_VERSION: '21'                        # ← 改 2：JDK 版本
  DB_ROOT_PASSWORD: rootpass                # ← 改 3：MySQL root 密码
  DB_NAME: agent_insight                   # ← 改 4：MySQL 数据库名

  # 前端配置
  FRONTEND_DIR: agent-insight-web          # ← 改 5：前端代码目录
  NODE_VERSION: '22'                       # ← 改 6：Node 版本

  # 服务镜像版本（与部署环境一致）
  MYSQL_IMAGE: mysql:8.4                  # ← 改 7：MySQL 版本
  MONGODB_IMAGE: mongo:8.3               # ← 改 8：MongoDB 版本
  REDIS_IMAGE: redis:8.8.0-alpine        # ← 改 9：Redis 版本

  # SQL / MongoDB 初始化脚本（相对于仓库根）
  SQL_INIT_SCRIPT: fixtures/mysql/init.sql         # ← 改 10：建表 SQL 路径
  MONGODB_INIT_SCRIPT: fixtures/mongodb/init.js    # ← 改 11：MongoDB 初始化脚本

  # E2E 配置
  E2E_PORT: 3010                           # ← 改 12：E2E 测试 Vite dev server 端口
  PLAYWRIGHT_BROWSERS: chromium             # ← 改 13：浏览器（chromium / firefox / webkit）
```

> **CI 不需要配 secret**（不需要 SSH、不需要镜像 token）。只需确保 SQL/MongoDB 初始化脚本路径正确。

### 第 4 步：复制 CD 模板、改 4 个变量

打开 `assets/ci-cd-workflow-template.yml`，只改顶部 `env` 块：

```yaml
env:
  # 镜像相关（公开信息，env 配，不需要 secret）
  IMAGE_REGISTRY: ghcr.io                                      # ← 改 1：或 registry.cn-hangzhou.aliyuncs.com
  IMAGE_NAMESPACE: ${{ github.repository_owner }}              # 留默认即可
  IMAGE_PROJECT: my-app                                        # ← 改 2：项目名

  # 部署相关（DEPLOY_* 通常走 secret，这里多配一份 env 给你选）
  DEPLOY_PATH: /opt/project/my-app                             # ← 改 3：服务器上的项目根目录
  COMPOSE_FILE: docker-compose.yml                             # 留默认即可
  COMPOSE_SERVICES: my-app-backend my-app-frontend           # ← 改 4：compose.yml 里的服务名
  DEPLOY_PRIMARY_BRANCH: master                                # ← 可选：主部署分支（master/main）
```

> 同时把 `assets/compose-stack-template.yml` **手工**放到服务器的对应路径（即上面 `COMPOSE_FILE` 指向的位置），改 service 名/镜像名。CD **不会**自动拷贝这份文件。

### 第 5 步：放到 `.github/workflows/`

```bash
cp assets/ci-template.yml .github/workflows/ci.yml
cp assets/ci-cd-workflow-template.yml .github/workflows/cd.yml
git add .github/workflows/
git commit -m "ci: add CI/CD workflows"
git push
```

> **CI 和 CD 分开两个文件**，PR 阶段跑 `ci.yml`（只 test，不部署），主分支（`master` 或 `main`）合并后才触发 `cd.yml`（build + 部署）。

### 第 5.1 步：Compose 不混淆（必须统一）

推荐固定为“1 主文件 + 1 本地覆盖”：

- `docker-compose.yml`：远程/CD 用（只拉镜像，不在服务器 build）
- `docker-compose.local.yml`：本地开发覆盖（补 `build`，仅本地 `--build` 时叠加）

命令对照：

```bash
# 远程服务器 / CD 脚本（默认）
docker compose --env-file .env -f docker-compose.yml pull
docker compose --env-file .env -f docker-compose.yml up -d

# 本地开发（需要本地构建时）
docker compose --env-file .env -f docker-compose.yml -f docker-compose.local.yml up -d --build
```

`cd.yml` 建议固定：

```yaml
env:
  COMPOSE_FILE: docker-compose.yml
```

CD 远程脚本只 `pull` + `up`，**不要** SCP 覆盖服务器上的 `docker-compose.yml` / `.env`。Demo CD 里 SCP 步骤注释保留，部署时 echo「不拷贝 compose 文件到远程机器」。

### 第 5.2 步：DOCKER_TAG 文件约定（可选）

当项目用 `image: ...:${DOCKER_TAG:-latest}` 时，推荐：

- 运行时生效文件：`.env`（部署机）
- 历史模板文件：`env-docker-tag.example`（仓库）

维护规则：

- `.env` 里只保留 1 行生效 `DOCKER_TAG=...`
- 新版本可按 `env-YYYYMMDD` 或 `env-YYYYMMDD-vN`
- 历史示例放 `env-docker-tag.example`，不要把多行生效值写进 `.env`

### 第 6 步：主分支优先级与变量校验（强烈建议）

```yaml
on:
  push:
    branches: [master, main]

env:
  DEPLOY_PRIMARY_BRANCH: ${{ vars.DEPLOY_PRIMARY_BRANCH }}

jobs:
  deploy:
    steps:
      - name: Resolve primary deploy branch
        id: branch_gate
        run: |
          set -e
          configured_branch="${{ env.DEPLOY_PRIMARY_BRANCH }}"
          if [ -n "${configured_branch}" ]; then
            if [ "${configured_branch}" != "master" ] && [ "${configured_branch}" != "main" ]; then
              echo "::error::DEPLOY_PRIMARY_BRANCH must be 'master' or 'main'"
              exit 1
            fi
            preferred_branch="${configured_branch}"
          elif git ls-remote --exit-code origin refs/heads/master >/dev/null 2>&1; then
            preferred_branch="master"
          else
            preferred_branch="main"
          fi
          [ "${GITHUB_REF_NAME}" = "${preferred_branch}" ] \
            && echo "should_deploy=true" >> "$GITHUB_OUTPUT" \
            || echo "should_deploy=false" >> "$GITHUB_OUTPUT"
```

### 第 7 步：GHCR 登录优先用 `GITHUB_TOKEN`

```yaml
permissions:
  contents: read
  packages: write

steps:
  - uses: docker/login-action@v3
    with:
      registry: ghcr.io
      username: ${{ github.actor }}
      password: ${{ github.token }}
```

---

## 5 个模板分别详解

### 一句话先搞清楚两类文件

| 类 | 文件名以...开头 | 谁用它 | 在哪跑 |
|----|------------------|--------|--------|
| **GitHub Actions workflow**（CI/CD 流程定义） | `ci-cd-*` | GitHub Actions runner | 云端 Ubuntu VM |
| **服务编排**（docker compose 文件） | `compose-stack-*` | docker compose CLI | 你的服务器 |

> 4 个 `ci-cd-*.yml` / `ci-*.yml` 是"流程脚本"，1 个 `compose-stack-*.yml` 是"被它调度的服务定义"。

### 模板 1：`ci-cd-workflow-template.yml`（**最常用**）

**适用场景**：
- Spring Boot 后端 + React/Vue 前端
- 单台 / 少数服务器（VPS、ECS、轻量应用服务器）
- 用 docker compose 管服务编排
- 镜像托管 ghcr.io（GitHub Container Registry，免费）

**核心流程**：

```
git push master   # 若仓库主分支是 main，则改成 git push main
  ↓
Job 1: build (Ubuntu runner)
  ├── checkout
  ├── docker buildx 准备
  ├── login ghcr.io
  ├── build & push backend → ghcr.io/owner/proj/backend:sha
  └── build & push frontend → ghcr.io/owner/proj/frontend:sha
  ↓
Job 2: deploy (Ubuntu runner, depends_on: build)
  ├── SSH 私钥 fingerprint 校验（防呆）
  ├── echo：不拷贝 compose 到远程（SCP 步骤注释保留）
  ├── ssh 到服务器
  ├── docker login ghcr.io
  ├── docker compose pull  <services>
  └── docker compose up -d <services>
```

> **不要**在 Job 2 默认 SCP `docker-compose.yml`。compose 已在服务器，CD 只拉镜像。SCP 步骤在 demo CD 里注释保留，解开前必须确认不会覆盖远程本地配置。

**怎么用**：

1. 复制到 `.github/workflows/cd.yml`
2. 改 `env` 块 4 个变量
3. 在 GitHub 配 4 个 secret
4. 推代码

### 模板 2：`ci-cd-k8s-template.yml`

**适用场景**：已有 K8s 集群（EKS / AKS / 自建 K8s）。

**核心差异**：部署阶段从 `docker compose up` 换成 `kubectl set image`。

```bash
# 用法变化
kubectl set image deployment/my-backend \
  backend=ghcr.io/owner/proj/backend:${{ github.sha }}
```

### 模板 3：`ci-cd-static-template.yml`

**适用场景**：纯静态站（VitePress / Hugo / Next.js SSG / 纯 HTML）。

**核心差异**：没有后端镜像，直接 `rsync` 到 nginx 目录。

### 模板 4：`compose-stack-template.yml`（配套用）

**为什么需要**：模板 1 默认假设服务器上已有 `docker-compose.yml`。本模板是一份**生产级**的 compose 文件范例（健康检查、depends_on condition、卷挂载），**放到服务器上**，不是放到 GitHub Actions 上。

Traefik labels 写在这份 compose 里（Demo 也一样）。路由器必须显式 `service=`，不要靠「和路由器同名」的默认查找。详见下方「坑 2.2」。

---

## 常见坑（避免踩）

### ❌ 坑 1：私钥换行符被截断 → `invalid format` / `Permission denied`

**症状**：
```
ssh: handshake failed: ssh: unable to authenticate
# 或
load pubkey "/root/.ssh/deploy_key": invalid format
```

**根因**：GitHub Secret UI 粘贴时自动 strip 末尾换行符，OpenSSH 私钥规范要求文件以 `\n` 结尾。

**解法（workflow 侧）**：用 `printf '%s\n'` 写文件（模板已含）：

```bash
# ✅ 正确
printf '%s\n' "${{ secrets.DEPLOY_SSH_KEY }}" > ~/.ssh/deploy_key

# ❌ 错误（echo 会追加额外换行）
echo "${{ secrets.DEPLOY_SSH_KEY }}" > ~/.ssh/deploy_key
```

**解法（Secret 侧）**：在私钥末尾手动加一个空行再粘贴——但治本还是 workflow 用 `printf '%s\n'`。

### ❌ 坑 2：`image not found` after push

**症状**：`docker compose pull` 找不到镜像

**原因**：ghcr.io 镜像默认是 **private**，服务器 `docker login` 没权限

**解法**：
1. PAT 必须勾 `write:packages` 权限
2. 或者在 GitHub 仓库 Settings → Packages → 设为 public

### ❌ 坑 2.1：CD 把 compose 拷到服务器 → 覆盖远程配置 / Permission denied

**症状**：
- 远程 `.env` / Traefik labels / 端口被仓库版本覆盖
- 或 `tar: docker-compose.yml: Cannot open: Permission denied`

**根因**：用 SCP 覆盖服务器已维护的 compose。远程目录往往只有运维可写，CD SSH 用户也不该改编排文件。

**解法**：Demo CD 默认 **不拷贝** compose。部署 step 先 echo 说明；SCP 整段注释保留。compose 由运维首次放到 `DEPLOY_PATH`。若 `go-yaml load error ... L10.C3`，在**服务器本地**修 Tab/非法字符，不要靠 CD 覆盖。

### ❌ 坑 2.2：Traefik 路由器没写 service → 按路由名找后端 → 404

**症状**：容器是 Up、域名 DNS 也对，但公网 404。Traefik 日志/API 里路由器在，后端服务名对不上。

**根因**：路由器没有显式 `service` 时，Traefik 默认寻找**和路由器同名**的服务。Demo 里常见：路由器叫 `wifi-tie-admin`，compose 服务叫 `wifi-tie-admin-web`。

**解法**（写在服务器 `docker-compose.yml` 的 labels 里；Demo CD 不拷贝 compose，必须改远程文件）：

```yaml
# 路由器名可以和 compose 服务名不同，但必须写 service
- "traefik.http.services.wifi-tie-admin-web.loadbalancer.server.port=80"
- "traefik.http.routers.wifi-tie-admin.rule=Host(`${DOMAIN:?Set DOMAIN in web.env or .env}`)"
# 使用环境变量，同时匹配裸域和 www（Demo 默认不启用；需要时解开并注释掉上一行）
#- "traefik.http.routers.wifi-tie-admin-web.rule=Host(`${DOMAIN}`) || Host(`www.${DOMAIN}`)"
- "traefik.http.routers.wifi-tie-admin.service=wifi-tie-admin-web"
```

相关约定（Demo / 生产相同）：
- `${DOMAIN:?...}`：没填域名就拒绝启动，避免 `Host(\`\`)`
- 裸域 + www：默认注释保留，需要时再开；同一路由器只能有一条 `rule`
- 业务容器用 `loadbalancer.server.port` 指向容器监听端口（Nginx 一般是 80）
- Traefik **自己的** Dashboard 不要 `loadbalancer.server.port=8080`，用 `service=api@internal`
- Dashboard 子域用 `traefik.${BASE_DOMAIN:?Set BASE_DOMAIN in .env}`（`/opt/docker/.env` 同级，不含 `traefik.` 前缀）
- 登录可先注释；生成：`htpasswd -nbB admin 'your-password'`，输出里的 `$` 改成 `$$`；多人逗号拼接

### ❌ 坑 2.3：Portainer Restricted 用户重建后看不到容器

**症状**：管理员能看到；Restricted 用户看不到。或：Portainer 页面里重启还在，`docker compose up --force-recreate` 后消失。

**根因**：Restricted 权限写在容器元数据里；命令行/CD 重建是新容器。必须在服务器 compose 每个业务服务加：

```yaml
labels:
  # Portainer 权限控制：不配置会导致手动 docker compose 重建后 Restricted 权限丢失
  # （但在 Portainer 页面重启无影响）
  io.portainer.accesscontrol.users: "YOUR_PORTAINER_RESTRICTED_USER"
```

与 Traefik 列表式 labels 混写时用 `"io.portainer.accesscontrol.users=..."`。详见 Cursor `deploy` skill **§5.4**。

### ❌ 坑 3：服务启动后立即被 kill

**症状**：容器起来几秒后退出，healthcheck failed

**解法**：compose 里给后端加 `start_period: 60s`（Spring Boot 启动慢）

### ❌ 坑 4：直接 root 登录被拒

**症状**：`Permission denied` 即使密码对

**解法**：服务器 `/etc/ssh/sshd_config` 改 `PermitRootLogin prohibit-password` 或 `no`，用 deploy 用户 + sudo

### ❌ 坑 5：手动 trigger 时 `inputs.service` 为空

**症状**：`workflow_dispatch` 触发后 `github.event.inputs.service` 是 null，条件判断崩

**解法**：模板里用 `|| == ''` 兜底：

```yaml
if: github.event.inputs.service == 'all' || github.event.inputs.service == '' || github.event.inputs.service == 'backend'
```

### ❌ 坑 6：buildx cache 不生效导致每次全量构建

**解法**：`cache-from: type=gha` + `cache-to: type=gha,mode=max`，第一次 build 慢，第二次起飞

### ❌ 坑 8：静态前端把 localhost 打进镜像 → 公网登录打到访客电脑

**症状**：生产站 `POST http://localhost:8080/api/...` / `ERR_CONNECTION_REFUSED`；本机开后端「又好了」。

**根因**：Nginx/静态托管没有运行时配置。`fetch('http://localhost:8080')` 在浏览器执行，localhost = 访客本机。compose 里的 `NUXT_PUBLIC_*` / `VITE_*` **改不了**已构建的 JS。

**解法**：

- Docker build-arg 写入 API 基址；方案 A（同源 Nginx 反代）生产 **`API_BASE` 为空**，不要 `/api`（路径已含 `/api/v1`）
- 本地 dev 才用 `http://localhost:8080`
- 业务代码禁止写死 localhost；修复后必须重建并部署前端镜像

Cogniforge 细节见 `~/.cursor/skills/deploy/references/cogniforge.md`。

---

## 配套建议

### 必须配套做的事

1. **服务器 hardening**：
   - `ufw` 防火墙，只开 22/80/443
   - `fail2ban` 防爆破
   - `apt update && apt upgrade` 每周

2. **零停机部署**：
   - compose 加 `healthcheck`，配合 `start_period`
   - 升级时先 `pull`，再 `up -d --no-deps`，等 health 通过再继续
   - 或者前置 nginx / traefik 做蓝绿

3. **回滚能力**：
   - 镜像 tag 带 sha（已有），不要只 latest
   - 服务器保留最近 3 个镜像：`docker image prune --filter "until=72h"`
   - 失败时一行回滚：`docker compose up -d --force-recreate backend`

4. **可观测性**：
   - GitHub Actions 自带日志
   - 服务器 `docker compose logs --tail 100 > /var/log/deploy.log`
   - 失败时发邮件 / Slack 通知（`slack-webhook-action`）

---

## 升级路径

项目规模变大时，按这个顺序升级：

```
单机 docker compose  ←── 你现在
  ↓
单机 + Traefik（自动 HTTPS）
  ↓
多机 + Swarm
  ↓
K8s（用 ci-cd-k8s-template.yml）
  ↓
ArgoCD / Flux（GitOps）
```

**不要过早上 K8s**。一台 4C8G 的 ECS + docker compose 能扛 80% 的中小项目。

---

## 配套 skill

| Skill | 用途 |
|-------|------|
| `babysit` | PR/CI 持续修复 |
| `create-rule` | 在仓库固化 CI 规约 |

---

## 附录：完整变量清单

### env（写在 workflow 顶部）

| 变量 | 必填 | 默认 | 说明 |
|------|------|------|------|
| `IMAGE_REGISTRY` | 否 | `ghcr.io` | 镜像仓库地址（ghcr.io / 阿里云 / 自建） |
| `IMAGE_NAMESPACE` | 否 | `${{ github.repository_owner }}` | 镜像命名空间（ghcr.io = owner，阿里云 = 命名空间） |
| `IMAGE_PROJECT` | **是** | `YOUR_PROJECT_NAME` | 项目名，决定镜像路径：`/IMAGE_NAMESPACE/IMAGE_PROJECT/backend:tag` |
| `DEPLOY_PATH` | **是** | `/opt/project/<repo>` | 服务器上项目根目录 |
| `COMPOSE_FILE` | 否 | `docker-compose.yml` | 相对 `DEPLOY_PATH` 的 compose 文件名 |
| `COMPOSE_SERVICES` | **是** | `<service1> <service2>` | 要部署的服务名，空格分隔 |

### secret（配在 GitHub Repository Secrets）

| 变量 | 必填 | 说明 |
|------|------|------|
| `DEPLOY_HOST` | **是** | 服务器 IP/域名 |
| `DEPLOY_USER` | **是** | SSH 用户 |
| `DEPLOY_SSH_KEY` | **是** | SSH 私钥全文（含 BEGIN/END 行） |
| `DEPLOY_SSH_PORT` | 否 | SSH 端口，默认 22 |
| `IMAGE_REGISTRY_TOKEN` | 否 | PAT 兜底（仅 `GITHUB_TOKEN` 权限受限时使用） |

### variables（配在 GitHub Repository Variables）

| 变量 | 必填 | 默认 | 说明 |
|------|------|------|------|
| `DEPLOY_PRIMARY_BRANCH` | 否 | 自动判定：有 `master` 用 `master`，否则 `main` | 显式指定主部署分支，仅允许 `master` / `main` |

---

## 附录：CD 文件包含的所有 GitHub Actions 高级特性

| 特性 | 在哪 | 作用 |
|------|------|------|
| `concurrency` | 顶部 | 防止并发部署 |
| `environment: production` | job 级 | 需要人工审批 |
| `workflow_dispatch` | trigger | 手动触发 + 选择 service |
| `branch gate (master/main)` | step 级 | `master` 优先，支持 `DEPLOY_PRIMARY_BRANCH` 覆盖 |
| `needs: build` | job 级 | 串行依赖 |
| `cache-from: type=gha` | docker build | 利用 GitHub Actions cache |
| `tags: ${{ github.sha }} + :latest` | docker build | 不可变 + 可变双 tag |
| `appleboy/ssh-action@v1.2.5` | deploy | 稳定的 SSH action（Node 24 兼容） |
| `docker login ... --password-stdin` | deploy | 不暴露 token 到日志 |
| `echo 不拷贝 compose` + 注释保留 SCP | deploy | 避免覆盖服务器本地 compose / `.env` |
| `docker compose pull + up -d` | deploy | 滚动升级（只拉镜像，不传编排文件） |