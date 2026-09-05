# Cogniforge 前端 API 基址（方案 A）

> 本文件是 `deploy` skill 的 Cogniforge 特化附录。通用流程见 `SKILL.md`。
> 源码真相以 `cogniforge-web` 仓库为准。

---

## 1. 同一套代码如何兼容本地 / 公网

接口路径本身已带 `/api/v1/...`。`API_BASE` 只表示**前面的源**（协议+主机），不含 `/api`。

| 环境 | 怎么启动 | `API_BASE` | 浏览器实际请求 |
|------|----------|------------|----------------|
| 本地开发 | `pnpm dev`（:3000） | `http://localhost:8080` | `http://localhost:8080/api/v1/...`（本机 Go） |
| 生产镜像 | Dockerfile 构建 | **空字符串** | `https://{{DOMAIN}}/api/v1/...`（当前域名） |

生产链路（方案 A）：

```
浏览器 → Traefik → cogniforge-web:80（Nginx）
                         └─ location /api/ → cogniforge:8080（Go，cogniforge-net）
```

本地 `pnpm dev` 没有这层 Nginx，所以必须显式指向本机 8080。

---

## 2. 构建时写入，不是容器运行时

`cogniforge-web` 生产镜像是 **Nginx 静态托管**（`pnpm build` 产物）。  
浏览器里的 JS **没有**运行时 Nuxt 配置。`API_BASE` 必须在 **Docker build** 时写入：

```dockerfile
# cogniforge-web/Dockerfile
ARG API_BASE=
ENV API_BASE=$API_BASE
RUN pnpm build
```

| 错误做法 | 为什么不行 |
|----------|------------|
| compose `environment: NUXT_PUBLIC_API_BASE=/api` | 静态镜像读不到；改 env 不改变已构建的 JS |
| `ARG API_BASE=/api` 或 `API_BASE=/api` | 接口已是 `/api/v1/...`，会拼成 `/api/api/v1/...` |
| JS 写死 `http://localhost:8080` | 公网页在**用户电脑**上跑；`localhost` = 访客本机，不是服务器 |

`docker-compose-web.yml` **不要**再写 `NUXT_PUBLIC_API_BASE`。  
Traefik 只需要部署目录 `.env` 里的 `DOMAIN`。

---

## 3. 故障：公网登录打到本机 8080

**症状**：浏览器控制台

```
POST http://localhost:8080/api/v1/auth/login  net::ERR_CONNECTION_REFUSED
```

本机一开后端「公网又能用了」，一关又失败。

**根因**：页面 JS 从远程下载，但 `fetch('http://localhost:8080/...')` 在**浏览器所在电脑**执行。  
SSH / 远程 compose / 公网域名都管不到这一步。

**修复**：

1. 所有 `createApiClient` 走 `useRuntimeConfig().public.apiBase`（见 `composables/useApi.ts` + `utils/apiBase.ts`）
2. 生产构建 `API_BASE` 为空；`resolveApiBase('/api')` 也当成空，避免历史配置双写 `/api`
3. 重新构建并部署 `cogniforge-web` 镜像
4. 用无痕窗口打开域名，确认请求是 `https://{{DOMAIN}}/api/v1/...`

---

## 4. 本地开发与公网互不影响（部署修复后）

| 你打开的地址 | 接口打到哪 |
|--------------|------------|
| `https://{{DOMAIN}}` | 远程 Nginx → 远程 Go |
| `http://localhost:3000` | 本机 Go :8080 |

两套入口，同一套源码。测公网请打开域名，不要用 localhost:3000。

---

## 5. Redis 键（与 Go / Python 共用）

公用 Redis 用 **db0** + 前缀隔离，不要给 Cogniforge 单独 `SELECT 1`。

格式：`cogniforge:{模块}:{名字}`。禁止 `cf:`、禁止无前缀。

| 键 | 用途 |
|----|------|
| `cogniforge:modelcfg:rev` | 模型配置版本；`ai_providers` 变更后 INCR |
| `cogniforge:modelcfg:snapshot` | 当前启用供应商 JSON；只含 `encrypted_key`，明文 Key 只在 Go 内存 |

Go：`internal/modelcache/snapshot.go` 常量。Python：`llm/model_config.py` 必须用同一对键。  
新键先记 `cogniforge/docs/04-database/01-database-design.md` §5.1，再改代码。

---

## 6. Portainer Restricted（命令行 / CD 拉起的容器）

Cogniforge 若用 Portainer Stack 创建，Restricted 权限跟 Stack 走。若改成 **命令行 / CD `compose up`**，每个业务服务都要加：

```yaml
labels:
  # Portainer 权限控制：不配置会导致手动 docker compose 重建后 Restricted 权限丢失
  # （但在 Portainer 页面重启无影响）
  io.portainer.accesscontrol.users: "{{PORTAINER_RESTRICTED_USER}}"
```

与 Traefik 列表式 labels 混写时用字符串形式。通用说明见 `SKILL.md` **§5.4**。
