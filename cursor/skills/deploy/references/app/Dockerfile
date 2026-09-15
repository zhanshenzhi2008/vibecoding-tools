# =============================================================================
# Go 应用 Dockerfile 模板
# 用途：构建生产镜像
#
# 特性：
#   - 多阶段构建，体积最小化
#   - 非 root 用户运行
#   - 静态编译，无 CGO
# =============================================================================

# ─── 构建阶段 ───────────────────────────────────────────────────────────────
FROM golang:1.23-alpine AS builder

WORKDIR /app

# 安装依赖
COPY go.mod go.sum ./
RUN go mod download

# 复制源码
COPY . .

# 构建（静态编译）
ENV CGO_ENABLED=0 GOOS=linux GOARCH=amd64
RUN go build -ldflags="-w -s" -o server .

# ─── 运行阶段 ───────────────────────────────────────────────────────────────
FROM alpine:3.20

# 安装运行时依赖
RUN apk add --no-cache ca-certificates tzdata

# 创建非 root 用户
RUN addgroup -g 1000 appgroup && \
    adduser -u 1000 -G appgroup -s /bin/sh -D appuser

WORKDIR /app

# 复制二进制和静态资源
COPY --from=builder /app/server .
COPY --from=builder /app/migrations ./migrations
COPY --from=builder /app/templates ./templates 2>/dev/null || true

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://127.0.0.1:${APP_PORT:-8080}/health || exit 1

# 切换非 root
USER appuser

# 暴露端口
EXPOSE ${APP_PORT:-8080}

# 启动命令
CMD ["./server"]
