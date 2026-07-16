---
name: github-cicd-template
description: 生成 GitHub Actions CI/CD 工作流模板，覆盖 Spring Boot + React/Vue/Angular + Docker + 远程服务器部署场景。当用户需要"建 CI/CD"、"配 GitHub Actions 部署"、"自动部署到服务器"、"写 docker-compose + workflow" 时使用本 skill。
---

# GitHub Actions CI/CD 模板生成器

> 一套**参数化**的 CI/CD 模板，适配任何 Spring Boot + 前端 + Docker + 远程服务器项目。
> 用法和 `package.json` 模板类似：复制 → 改变量 → 用。

---

## 何时使用

| 用户说 | 用本 skill |
|--------|-----------|
| "帮我建 GitHub Actions 部署" | ✅ |
| "配一下 CI/CD，push 到 main 自动部署" | ✅ |
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
| Registry token | `IMAGE_REGISTRY_TOKEN` | **是** | PAT with `write:packages` 权限 |

---

## 模板清单（5 个）

| 文件 | 是什么 | 放哪里 | 用途 |
|------|--------|--------|------|
| `assets/ci-template.yml` | **GitHub Actions workflow**（CI 流程，测试验证） | 本地 → `.github/workflows/ci.yml` | **必选**：后端单元测试 + 前端单元测试 + 前端 E2E 测试。**CI 和 CD 必须分开**，职责单一、状态清晰 |
| `assets/ci-cd-workflow-template.yml` | **GitHub Actions workflow**（CD 流程，部署上线） | 本地 → `.github/workflows/cd.yml` | **推荐**：build 镜像 → SSH 拉镜像 → `docker compose up`。90% 项目首选 |
| `assets/compose-stack-template.yml` | **服务编排定义**（docker compose 文件） | 服务器 → `/opt/project/<repo>/docker-compose.yml` | 给 CD 模板配套（健康检查 / depends_on / 卷挂载） |
| `assets/ci-cd-k8s-template.yml` | **GitHub Actions workflow** | 本地 → `.github/workflows/cd-k8s.yml` | build 镜像 → `kubectl set image`。有 K8s 集群时用 |
| `assets/ci-cd-static-template.yml` | **GitHub Actions workflow** | 本地 → `.github/workflows/cd-static.yml` | build 前端 → rsync 到 nginx。纯前端静态站用 |

> **CI 和 CD 必须分开**，不要把 test 塞进 CD workflow 里。分开的好处：PR 阶段只跑 test（快，不触发构建），main 阶段才 build + 部署；状态页上 CI 和 CD 的通过/失败独立显示，不会互相干扰。

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

### 第 2 步：准备 5 个 GitHub Secret

进仓库 → Settings → Secrets and variables → Actions → New repository secret：

| Secret 名 | 内容 | 怎么获取 |
|-----------|------|----------|
| `DEPLOY_HOST` | 服务器公网 IP / 域名 | `ip addr` 或服务商控制台 |
| `DEPLOY_USER` | SSH 用户名（推荐非 root） | 服务器新建 `deploy` 用户 |
| `DEPLOY_SSH_PORT` | SSH 端口（默认 22，可选） | 服务端 sshd 配置 |
| `DEPLOY_SSH_KEY` | 私钥全文 | `ssh-keygen -t ed25519 -C "github-deploy"` |
| `DEPLOY_PATH` | 服务器项目根目录 | `/opt/docker/<project>` 这种 |
| `IMAGE_REGISTRY_TOKEN` | PAT with `write:packages` | GitHub Settings → Developer settings → PAT |

**或者用 `gh` CLI 一把梭**：

```bash
gh secret set DEPLOY_HOST          --body "156.226.176.141"     --env production
gh secret set DEPLOY_USER          --body "deploy"              --env production
gh secret set DEPLOY_SSH_PORT      --body "22000"               --env production
gh secret set DEPLOY_SSH_KEY       < ~/.ssh/github_actions      --env production
gh secret set DEPLOY_PATH          --body "/opt/docker/<project>" --env production
gh secret set IMAGE_REGISTRY_TOKEN --body "ghp_xxxxxxxxxxxx"     --env production
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
```

> 同时把 `assets/compose-stack-template.yml` 放到服务器的对应路径（即上面 `COMPOSE_FILE` 指向的位置），改 service 名/镜像名。

### 第 5 步：放到 `.github/workflows/`

```bash
cp assets/ci-template.yml .github/workflows/ci.yml
cp assets/ci-cd-workflow-template.yml .github/workflows/cd.yml
git add .github/workflows/
git commit -m "ci: add CI/CD workflows"
git push
```

> **CI 和 CD 分开两个文件**，PR 阶段跑 `ci.yml`（只 test，不部署），main 合并后才触发 `cd.yml`（build + 部署）。

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
git push main
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
  ├── ssh 到服务器
  ├── docker login ghcr.io
  ├── docker compose pull  <services>
  └── docker compose up -d <services>
```

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

### ❌ 坑 7：镜像体积太大（>2GB）

**解法**：用 multi-stage build，前端 `nginx:alpine`，后端 `eclipse-temurin:21-jre-alpine`

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
| `IMAGE_REGISTRY_TOKEN` | **是** | PAT with `write:packages` 权限 |

---

## 附录：CD 文件包含的所有 GitHub Actions 高级特性

| 特性 | 在哪 | 作用 |
|------|------|------|
| `concurrency` | 顶部 | 防止并发部署 |
| `environment: production` | job 级 | 需要人工审批 |
| `workflow_dispatch` | trigger | 手动触发 + 选择 service |
| `if: github.ref == 'refs/heads/main'` | job 级 | 只 main 触发部署 |
| `needs: build` | job 级 | 串行依赖 |
| `cache-from: type=gha` | docker build | 利用 GitHub Actions cache |
| `tags: ${{ github.sha }} + :latest` | docker build | 不可变 + 可变双 tag |
| `appleboy/ssh-action@v1` | deploy | 稳定的 SSH action |
| `docker login ... --password-stdin` | deploy | 不暴露 token 到日志 |
| `docker compose pull + up -d` | deploy | 滚动升级 |