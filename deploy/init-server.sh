#!/usr/bin/env bash
# 第一次上线时在服务器上运行（可以重复运行，不会覆盖已有的 .env，也不会清空已有数据）
#   1. 没有 .env 时，按模板生成并填入随机密钥
#   2. 构建镜像、启动三个容器
#   3. 数据库里还没有用户时，导入演示数据
# 用法：在项目根目录执行  bash deploy/init-server.sh
set -euo pipefail
cd "$(dirname "$0")/.."

# ---------- 1. 生成 .env ----------
if [ ! -f .env ]; then
    cp .env.production.example .env
    chmod 600 .env   # 只有当前用户能读写
    set_value() { sed -i "s|^$1=.*|$1=$2|" .env; }
    set_value DB_PASSWORD    "$(openssl rand -hex 24)"
    set_value JWT_SECRET     "$(openssl rand -hex 32)"
    set_value WECHAT_AES_KEY "$(openssl rand -hex 32)"
    set_value SEED_PASSWORD  "Hh$(openssl rand -hex 4)"   # 例如 Hh3f9a1c2b：同时有字母和数字
    echo "已生成 .env（数据库密码、JWT 密钥、微信号加密密钥、演示账号密码都是随机的）"
    echo "请现在编辑 .env 填写 LLM_API_KEY（DeepSeek 的 Key），然后重新运行本脚本："
    echo "    nano .env"
    exit 0
fi

# 检查必填项
for key in DB_PASSWORD JWT_SECRET WECHAT_AES_KEY SEED_PASSWORD; do
    if ! grep -qE "^${key}=.+" .env; then
        echo "错误：.env 里的 ${key} 还没有填写" >&2
        exit 1
    fi
done
if ! grep -qE "^LLM_API_KEY=.+" .env; then
    echo "提示：LLM_API_KEY 为空，AI 助手小航将只使用关键词搜索（以后填上再运行 deploy/update.sh 即可）"
fi

# ---------- 2. 构建并启动 ----------
echo "==> 构建镜像并启动容器（第一次需要几分钟）"
docker compose up -d --build

echo "==> 等待后端就绪"
for _ in $(seq 1 30); do
    if docker compose exec -T backend python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/', timeout=3)" 2>/dev/null; then
        break
    fi
    sleep 2
done

# ---------- 3. 导入演示数据（只在数据库为空时） ----------
users=$(docker compose exec -T db psql -U campus_app -d campus -tAc "SELECT count(*) FROM users")
if [ "$users" = "0" ]; then
    echo "==> 数据库为空，导入演示数据"
    docker compose exec -T backend python scripts/seed.py
    echo "演示账号见 README（学号 20230001 等），密码是 .env 里的 SEED_PASSWORD"
else
    echo "==> 数据库里已有 ${users} 个用户，跳过导入演示数据"
fi

echo
docker compose ps
echo
echo "完成。用浏览器打开 http://服务器公网IP 访问网站"
