#!/usr/bin/env bash
# 备份数据库和上传的图片到 ~/backups，保留最近 7 天。
# 用法：bash deploy/backup.sh        （部署指南里会把它设成每天凌晨 3 点自动运行）
# 恢复方法见 docs/部署指南.md
set -euo pipefail
cd "$(dirname "$0")/.."

BACKUP_DIR="${BACKUP_DIR:-$HOME/backups}"
KEEP_DAYS=7
stamp=$(date +%Y%m%d-%H%M%S)
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"   # 备份里有用户数据，只有当前用户能访问

# 数据库没在运行时（比如第一次部署之前）直接跳过
if ! docker compose ps --status running --services 2>/dev/null | grep -qx db; then
    echo "数据库容器没有运行，跳过备份"
    exit 0
fi

# 数据库：pg_dump 导出成 SQL 文本并压缩；先写临时文件，成功后再改名，避免留下半截的备份
db_file="$BACKUP_DIR/db-$stamp.sql.gz"
docker compose exec -T db pg_dump -U campus_app -d campus --no-owner | gzip > "$db_file.tmp"
mv "$db_file.tmp" "$db_file"

# 上传的图片：把数据卷里的 uploads 目录打包
up_file="$BACKUP_DIR/uploads-$stamp.tar.gz"
docker compose exec -T backend tar -czf - -C /app uploads > "$up_file.tmp"
mv "$up_file.tmp" "$up_file"

# 删除 7 天前的备份和没写完的临时文件
find "$BACKUP_DIR" -maxdepth 1 -type f \( -name 'db-*.sql.gz' -o -name 'uploads-*.tar.gz' -o -name '*.tmp' \) -mtime +$KEEP_DAYS -delete

echo "备份完成：$(du -h "$db_file" | cut -f1) 数据库，$(du -h "$up_file" | cut -f1) 图片 -> $BACKUP_DIR"
