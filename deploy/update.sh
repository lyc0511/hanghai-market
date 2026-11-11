#!/usr/bin/env bash
# 更新网站：拉取最新代码 → 重新构建镜像 → 重启容器。数据库和上传的图片在数据卷里，不受影响。
# 用法：在服务器的项目根目录执行  bash deploy/update.sh
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> 更新前先备份一次"
bash deploy/backup.sh

echo "==> 拉取最新代码"
before=$(git rev-parse --short HEAD)
git pull --ff-only
after=$(git rev-parse --short HEAD)
echo "版本：${before} -> ${after}"

echo "==> 重新构建并启动（没变化的部分会直接用缓存）"
docker compose up -d --build

echo "==> 清理不再使用的旧镜像，释放硬盘空间"
docker image prune -f

echo
docker compose ps
echo
echo "更新完成。如果改了数据库表结构，还需要另外执行升级 SQL（见 docs/部署指南.md）"
echo "出问题想退回上一个版本：git reset --hard ${before} && docker compose up -d --build"
