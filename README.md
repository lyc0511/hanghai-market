# 校内二手交易与社团活动一体化平台

本科毕业设计项目，面向本校学生，包含三个板块：二手物品交易、社团目录与招募、社团活动。

当前进度：
- **T01 工程骨架与数据库**（14 张表、种子数据、FastAPI 骨架、字典接口）
- **T02 登录认证**（注册、学号密码登录、JWT、当前用户、修改密码）

## 技术栈

| 层 | 选型 |
|---|---|
| 后端 | Python 3.14 · FastAPI 0.162 · SQLAlchemy 2.1（同步 Session）· psycopg 3 |
| 数据库 | PostgreSQL 17（不使用 pgvector，向量以 JSON 文本存放在 `contents.embedding_text`） |
| 安全 | bcrypt 5（直接调用，不用 passlib）· PyJWT |
| 包管理 | uv |

## 目录结构

```
campus-platform/
├── README.md
├── .gitignore
└── backend/
    ├── requirements.txt
    ├── .env.example / .env      # 配置（.env 不入库）
    ├── run.py                   # python run.py 启动开发服务器
    ├── sql/schema.sql           # 建表脚本（14 张表）
    ├── scripts/seed.py          # 幂等种子数据
    └── app/
        ├── main.py              # FastAPI 入口
        ├── core/                # 配置、密码哈希、异常处理
        ├── db/                  # 声明基类、Session
        ├── models/              # 14 个 ORM 模型
        ├── schemas/             # Pydantic 模型
        └── api/                 # 路由（meta 字典、auth 认证；deps.py 放登录依赖）
```

## 快速开始（Windows PowerShell）

### 1. 准备数据库（只做一次）

用 `postgres` 超级用户在 DataGrip 中执行：

```sql
-- 账号已存在可跳过这一句
CREATE ROLE campus_app LOGIN PASSWORD 'Campus2027Dev';
-- 关键：库的 owner 必须是 campus_app，否则 PG15+ 下 campus_app 无权在 public 中建表
CREATE DATABASE campus OWNER campus_app;
```

如果 `campus` 库已经存在但 owner 不是 `campus_app`：

```sql
ALTER DATABASE campus OWNER TO campus_app;
-- 然后连到 campus 库再执行：
ALTER SCHEMA public OWNER TO campus_app;
```

### 2. 建表

在 DataGrip 中**以 `campus_app` 身份**连接 `campus` 库，打开 `backend/sql/schema.sql` 整体执行。

> 务必用 campus_app 连接执行。若用 postgres 执行，表的 owner 会是 postgres，后端和种子脚本都会报 `permission denied`。

需要重建全部表时，先在 campus 库中执行下面两行，再重新执行 schema.sql：

```sql
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
```

### 3. 安装依赖

```powershell
cd C:\dev\campus-platform\backend
uv venv --python 3.14 .venv
uv pip install -r requirements.txt --python .venv\Scripts\python.exe
```

### 4. 配置

`.env` 已生成好（含随机的 64 位十六进制 JWT_SECRET）。如需重新生成密钥：

```powershell
.venv\Scripts\python -c "import secrets; print(secrets.token_hex(32))"
```

### 5. 写入种子数据（可反复执行）

```powershell
.venv\Scripts\python scripts\seed.py
```

### 6. 启动

```powershell
.venv\Scripts\python run.py
# 或
.venv\Scripts\uvicorn app.main:app --reload
```

打开 http://127.0.0.1:8000/docs 查看接口文档。

## 演示账号（密码均为 `Test1234`）

| 学号 | 昵称 | 用途 |
|---|---|---|
| 20230001 | 管理员 | 后台管理（role=admin） |
| 20230002 | 卖家小王 | 发布物品、处理意向 |
| 20230003 | 买家小李 | 发起意向；有一条摄影协会的待审入社申请 |
| 20230004 | 摄影协会会长 | 社团负责人，可审批小李的申请 |
| 20230005 | 新生小张 | 普通用户；已通过吉他社入社申请 |
| 20230006 | 卖家阿强 | 发布物品；有 1 件被驳回的物品 |
| 20230101–20230114 | 社团会长01–14 | 其余社团负责人（01–05 各兼任两个社团） |

## 统一响应格式

```json
{"code": 0, "message": "ok", "data": ...}
```

| code | 含义 |
|---|---|
| 0 | 成功 |
| 40000 | 参数校验失败 |
| 40400 | 路由或资源不存在 |
| 40100 | 未登录或令牌失效（HTTP 401，前端应跳转登录页） |
| 40300 | 无权限 / 账号被封禁（HTTP 403） |
| 40101 | 学号或密码错误 |
| 40102 | 账号已被封禁（登录时） |
| 40103 | 原密码错误 |
| 40901 | 学号已注册 |
| 4xxxx | 其他业务错误（由 `BizError` 抛出，HTTP 200） |
| 50000 | 服务器内部错误（控制台打印堆栈） |

## 已实现接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/` | 服务信息 |
| GET | `/api/meta/enums` | 6 组枚举中文映射 |
| GET | `/api/meta/categories?type=item\|club` | 类目列表 |
| POST | `/api/auth/register` | 注册，成功后直接返回令牌 |
| POST | `/api/auth/login` | 学号 + 密码登录 |
| GET | `/api/auth/me` | 当前登录用户（需登录） |
| POST | `/api/auth/password` | 修改密码（需登录） |

## 登录与鉴权

登录 / 注册成功返回：

```json
{"code": 0, "message": "登录成功", "data": {
  "access_token": "eyJ...", "token_type": "bearer", "expires_in": 86400,
  "user": {"id": 2, "student_no": "20230002", "nickname": "卖家小王", "role": "student", ...}
}}
```

之后请求需要登录的接口时带上请求头 `Authorization: Bearer <access_token>`。令牌有效期由 `.env` 的 `JWT_EXPIRE_HOURS` 控制（默认 24 小时），令牌里只存用户 id，角色和封禁状态每次请求从数据库读取，所以封号立即生效。

在 `/docs` 中调试：先调用登录接口复制 `access_token`，点右上角 **Authorize** 粘贴进去即可。

校验规则：学号 6–20 位数字；密码 8–32 位可见 ASCII 字符，且必须同时包含字母和数字。

后端写新接口时：

```python
from app.api.deps import get_current_user, require_admin

@router.get("/xxx")
def handler(user: User = Depends(get_current_user)): ...   # 需要登录

@router.get("/admin/xxx")
def handler(admin: User = Depends(require_admin)): ...     # 需要管理员
```
