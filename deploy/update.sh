#!/usr/bin/env bash
# 更新网站：备份 → 拉取最新代码 → 执行数据库升级脚本 → 重新构建镜像 → 重启容器。
# 数据库和上传的图片在数据卷里，不受影响。
# 用法：在服务器的项目根目录执行  bash deploy/update.sh
set -euo pipefail
cd "$(dirname "$0")/.."

# 整个流程写在一个函数里，文件最后一行才调用它：bash 会先把函数完整读进内存，再开始执行。
# 如果不这样做，git pull 把本脚本换成新版本后，bash 会从新文件的同一位置接着往下读，行为不可预料。
main() {
    echo "==> 更新前先备份一次"
    bash deploy/backup.sh

    echo "==> 拉取最新代码"
    local before after
    before=$(git rev-parse --short HEAD)
    git pull --ff-only
    after=$(git rev-parse --short HEAD)
    echo "版本：${before} -> ${after}"

    # 数据库升级：backend/sql/upgrade_*.sql 按文件名顺序全部执行一遍。
    # 约定：升级脚本必须可以重复执行（CREATE TABLE IF NOT EXISTS、ON CONFLICT DO NOTHING……），
    # 所以这里不记录「哪些已经跑过」，每次更新都从头跑，已经存在的会自动跳过。
    # 放在重新构建之前：新代码启动时，它需要的表已经在了。
    echo "==> 执行数据库升级脚本"
    local f found=0
    for f in backend/sql/upgrade_*.sql; do
        [ -e "$f" ] || continue
        found=1
        echo "    $f"
        docker compose exec -T db psql -v ON_ERROR_STOP=1 -q -U campus_app -d campus < "$f"
    done
    [ "$found" = 1 ] || echo "    （没有升级脚本）"

    echo "==> 重新构建并启动（没变化的部分会直接用缓存）"
    docker compose up -d --build

    echo "==> 清理不再使用的旧镜像，释放硬盘空间"
    docker image prune -f

    echo
    docker compose ps
    echo
    echo "更新完成。"
    echo "出问题想退回上一个版本：git reset --hard ${before} && docker compose up -d --build"
    echo "（退回代码不会撤销数据库升级；升级脚本只新增表和数据，旧代码不受影响）"
}

main "$@"
