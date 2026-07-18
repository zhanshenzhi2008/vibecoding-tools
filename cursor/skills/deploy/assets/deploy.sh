#!/bin/bash
# =====================================================================
# 通用一键部署脚本
# 模板变量：{{PROJECT_NAME}} {{DOMAIN}} {{APP_NETWORK}} {{VOLUME_UPLOADS}}
#
# 用法：
#   bash deploy.sh                    # 部署所有服务
#   bash deploy.sh pull               # 仅拉取最新镜像
#   bash deploy.sh logs               # 查看日志
#   bash deploy.sh restart            # 重启所有服务
# =====================================================================

set -e

SERVICE="${1:-all}"
COMPOSE_FILE="docker-compose.yml"
COMPOSE_PROJECT="{{PROJECT_NAME}}"

info()  { echo -e "\033[0;32m[INFO]\033[0m  $1"; }
warn()  { echo -e "\033[1;33m[WARN]\033[0m  $1"; }
error() { echo -e "\033[0;31m[ERROR]\033[0m $1"; exit 1; }

# 确认 .env 存在
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        error "已从 .env.example 创建 .env，请先编辑填写真实值后再运行。"
    else
        error ".env 文件不存在，也找不到 .env.example。"
    fi
fi

# 检查外部网络
NETWORK="{{APP_NETWORK}}"
docker network inspect "$NETWORK" >/dev/null 2>&1 || {
    warn "网络 $NETWORK 不存在，正在创建..."
    docker network create "$NETWORK"
}

# 检查上传卷
VOLUME="{{VOLUME_UPLOADS}}"
docker volume inspect "$VOLUME" >/dev/null 2>&1 || {
    info "创建卷 $VOLUME..."
    docker volume create "$VOLUME"
}

# 检查 compose 文件
if [ ! -f "$COMPOSE_FILE" ]; then
    error "找不到 $COMPOSE_FILE，请确认在项目根目录运行。"
fi

case "$SERVICE" in
    all)
        info "🚀 拉取最新镜像并部署 $COMPOSE_PROJECT..."
        docker compose -f "$COMPOSE_FILE" pull
        docker compose -f "$COMPOSE_FILE" up -d
        ;;

    pull)
        info "📦 拉取最新镜像..."
        docker compose -f "$COMPOSE_FILE" pull
        ;;

    up|start)
        info "▶️  启动服务..."
        docker compose -f "$COMPOSE_FILE" up -d
        ;;

    down|stop)
        info "⏹  停止服务..."
        docker compose -f "$COMPOSE_FILE" down
        ;;

    restart)
        info "🔄 重启服务..."
        docker compose -f "$COMPOSE_FILE" restart
        ;;

    logs)
        info "📋 查看日志（Ctrl+C 退出）..."
        docker compose -f "$COMPOSE_FILE" logs -f
        ;;

    ps)
        docker compose -f "$COMPOSE_FILE" ps
        ;;

    health)
        info "🏥 健康检查..."
        docker compose -f "$COMPOSE_FILE" ps
        echo ""
        for svc in $(docker compose -f "$COMPOSE_FILE" config --services); do
            status=$(docker inspect "{{PROJECT_NAME}}-$svc" --format '{{.State.Health.Status}}' 2>/dev/null \
                     || docker inspect "{{PROJECT_NAME}}-$svc" --format '{{.State.Status}}' 2>/dev/null)
            printf "  %-20s %s\n" "$svc" "$status"
        done
        ;;

    db-backup)
        info "💾 备份数据库..."
        BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).sql"
        docker exec db-postgres pg_dump -U postgres "{{PROJECT_NAME}}" > "$BACKUP_FILE" \
            && info "备份已保存：$BACKUP_FILE" \
            || error "数据库备份失败"
        ;;

    *)
        error "未知命令: $SERVICE
用法: bash deploy.sh [all|pull|up|down|restart|logs|ps|health|db-backup]"
        ;;
esac

info "✅ 完成"
docker compose -f "$COMPOSE_FILE" ps
