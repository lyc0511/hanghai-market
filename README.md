# 校内二手交易与社团活动一体化平台

本科毕业设计项目，面向本校学生，包含三个板块：二手物品交易、社团目录与招募、社团活动。

当前进度：
- **T01 工程骨架与数据库**（14 张表、种子数据、FastAPI 骨架、字典接口）
- **T02 登录认证**（注册、学号密码登录、JWT、当前用户、修改密码）
- **T03 发布二手物品**（图片上传、发布物品进入待审核、物品详情；校区限定为黄埔 / 琶洲）
- **T04 物品审核**（管理员审核列表、通过上架、驳回并附原因；通知卖家、记录管理日志）
- **T05 物品列表与搜索**（关键词搜索、分类 / 校区 / 成色 / 价格筛选、四种排序、分页；我发布的物品）
- **T06 个人资料与交易意向**（微信号 AES-GCM 加密存储；发起 / 接受 / 拒绝 / 取消 / 成交，接受后双方互看微信号）
- **F01 前端框架**（海蓝色设计规范、请求封装、登录状态、手机端布局；登录注册、首页列表搜索、物品详情、发起意向、个人中心）
- **F02 二手交易页面**（发布物品、我发布的、我的意向（接受 / 拒绝 / 取消 / 成交 / 复制微信号）、电脑端管理后台物品审核）
- **F03 网站改版**（电脑网站布局：顶部导航 + 右上角登录弹窗；首页横幅 + 二手 / 社团 / 活动三大板块；二手交易页宽屏筛选与分页；详情页左右两栏；手机端自动单列）
- **F04 前端重做（shadcn-vue）**（「港口公告牌」设计：港口色板 + 得意黑标题字体；首页到港公告牌翻牌动画；二手市场筛选网格重排动画；全站 shadcn 组件，移除 Vant）
- **T07 物品管理**（卖家编辑（重新审核）、下架、重新上架、软删除；进行中的意向自动关闭并通知买家；前后端同步）

## 技术栈

| 层 | 选型 |
|---|---|
| 后端 | Python 3.14 · FastAPI 0.162 · SQLAlchemy 2.1（同步 Session）· psycopg 3 |
| 数据库 | PostgreSQL 17（不使用 pgvector，向量以 JSON 文本存放在 `contents.embedding_text`） |
| 安全 | bcrypt 5（直接调用，不用 passlib）· PyJWT |
| 包管理 | uv（后端）· npm（前端） |
| 前端 | Vue 3 · Vite · Vue Router · Pinia · Axios · Tailwind CSS 4 · shadcn-vue（reka-ui）· motion-v 动画 · Element Plus（仅管理后台） |

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
        └── api/                 # 路由（meta 字典、auth 认证、upload 上传、items 物品、intents 交易意向、admin 管理后台；deps.py 放登录依赖）
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

> `.env` 中的 `WECHAT_AES_KEY` 必须是 64 位十六进制，否则服务和种子脚本都会拒绝启动。生成方法同 JWT_SECRET。

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

### 7. 启动前端（另开一个终端，后端需保持运行）

```powershell
cd C:\dev\campus-platform\frontend
npm install      # 只需第一次
npm run dev
```

打开 http://localhost:5173 。开发服务器会把 `/api` 和 `/uploads` 请求转发给后端的 8000 端口。

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
| 40401 | 物品不存在（或无权查看未上架的物品） |
| 41301 | 图片超过大小限制 |
| 41501 | 图片格式不支持 |
| 42201 | 类目不存在或不是物品类目 |
| 42901 | 今日发布数量已达上限 |
| 40902 | 物品当前状态不能审核（只有待审核的物品能审核） |
| 40402 | 意向不存在 |
| 40301 | 无权操作该意向 |
| 40903 | 已对该物品发起过意向 |
| 40904 | 意向当前状态不能执行此操作 |
| 40302 | 无权操作该物品（不是自己发布的） |
| 40905 | 物品当前状态不能执行此操作（如已售出不能编辑） |
| 42202 | 需要先在个人资料中填写微信号 |
| 42203 | 不能对自己的物品发起意向 |
| 42204 | 物品不在售 |
| 4xxxx | 其他业务错误（由 `BizError` 抛出，HTTP 200） |
| 50000 | 服务器内部错误（控制台打印堆栈） |

## 已实现接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/` | 服务信息 |
| GET | `/api/meta/enums` | 枚举中文映射 + 校区列表（前端下拉框用） |
| GET | `/api/meta/categories?type=item\|club` | 类目列表 |
| POST | `/api/auth/register` | 注册，成功后直接返回令牌 |
| POST | `/api/auth/login` | 学号 + 密码登录 |
| GET | `/api/auth/me` | 当前登录用户（需登录） |
| PATCH | `/api/auth/me` | 修改个人资料：昵称、校区、头像、微信号（需登录） |
| POST | `/api/auth/password` | 修改密码（需登录） |
| POST | `/api/upload/image` | 上传图片（需登录，jpg/png/webp，≤5MB） |
| GET | `/api/items` | 物品列表 / 搜索（只返回已上架，分页） |
| GET | `/api/items/mine` | 我发布的物品，含待审核 / 已驳回（需登录） |
| POST | `/api/items` | 发布物品（需登录，提交后为待审核） |
| GET | `/api/items/{id}` | 物品详情（游客可看已上架的；卖家本人和管理员可看全部状态） |
| PUT | `/api/items/{id}` | 编辑物品（本人，提交后重新审核） |
| POST | `/api/items/{id}/offline` | 下架（本人） |
| POST | `/api/items/{id}/relist` | 重新上架（本人，需重新审核；已售出的不行） |
| DELETE | `/api/items/{id}` | 删除（本人，软删除） |
| POST | `/api/intents` | 发起交易意向（买家） |
| GET | `/api/intents/mine?role=buyer\|seller` | 我的意向（我发起的 / 我收到的） |
| POST | `/api/intents/{id}/accept` | 接受意向（卖家），双方可见微信号 |
| POST | `/api/intents/{id}/reject` | 拒绝意向（卖家） |
| POST | `/api/intents/{id}/cancel` | 取消意向（买家，待处理或已接受时） |
| POST | `/api/intents/{id}/complete` | 标记成交（卖家），物品自动下架 |
| GET | `/api/admin/items?status=pending` | 物品审核列表（管理员，分页；待审核按提交时间先到先审） |
| POST | `/api/admin/items/{id}/approve` | 审核通过，物品上架（管理员） |
| POST | `/api/admin/items/{id}/reject` | 审核驳回，需填写原因（管理员） |

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

## 发布物品流程

1. 调用 `/api/upload/image` 逐张上传图片，返回 `path`（存库用）和 `url`（预览用）
2. 调用 `/api/items`，`images` 字段填上一步返回的 `path` 数组
3. 物品状态为 `pending`（待审核），只有卖家本人和管理员能看到；管理员审核通过后变为 `online`，所有人可见

规则：
- 标题 2–60 字；价格 0–99999（0 表示免费送）；成色 `new/like_new/good/fair`；图片 1–9 张；标签最多 5 个
- 类目必须是物品类目（`/api/meta/categories?type=item`）
- 每人每天（北京时间）最多发布 `DAILY_PUBLISH_LIMIT` 件，默认 10
- 上传时按文件头判断真实格式，不信任扩展名；文件名随机生成，按年月分目录存放在 `UPLOAD_DIR`

> 种子数据中的物品图片路径 `/uploads/demo/itemN.jpg` 只是占位，实际文件不存在，页面上会显示为裂图。

## 物品审核流程

```
pending（待审核）──通过──▶ online（已上架，所有人可见）
                └─驳回──▶ rejected（已驳回，卖家可看到驳回原因）
```

- 只有 `pending` 的物品可以审核，重复审核返回 40902
- 每次审核在同一个事务中完成：修改物品状态、写入 `notifications` 通知卖家、写入 `audit_logs` 管理日志
- 审核前对物品行加锁（`SELECT ... FOR UPDATE`），两个管理员同时审核同一件物品时只有一个会成功
- 分页接口统一返回 `{"items": [...], "total": 总条数, "page": 页码, "page_size": 每页条数}`

## 物品列表与搜索

`GET /api/items` 的查询参数（都可不填，填了才参与筛选）：

| 参数 | 说明 |
|---|---|
| `keyword` | 关键词，在标题 + 描述 + 标签中模糊匹配；空格分隔多个词时需全部命中 |
| `category_id` | 物品类目 id |
| `campus_area` | `黄埔校区` / `琶洲校区` |
| `condition` | `new` / `like_new` / `good` / `fair` |
| `price_min` / `price_max` | 价格区间，0~0 即「免费送」 |
| `sort` | `latest` 最新（默认）/ `price_asc` / `price_desc` / `popular` 最热 |
| `page` / `page_size` | 页码 / 每页条数（最多 50） |

- 搜索基于 `contents.search_text`（发布时由标题、描述、标签拼接），使用 `ILIKE`；用户输入的 `%`、`_` 会被转义，按普通字符匹配
- 列表返回精简的「卡片」字段（封面为第一张图），完整信息走详情接口

## 交易意向与微信号

```
pending ──卖家接受──▶ accepted ──卖家标记成交──▶ completed（物品下架、记录售出时间）
   │  └─卖家拒绝──▶ rejected
   └──────┴─买家取消──▶ cancelled
```

- 发起和接受意向前，双方都必须在个人资料中填写微信号
- 卖家可以同时接受多个意向；某一单成交后，同一物品其余进行中的意向自动关闭并通知买家
- 只有 `accepted` / `completed` 状态下，接口才返回对方的微信号
- 每一步都会给对方写一条站内通知
- 成交时先锁物品行，同一物品的两个意向同时成交只有一个会成功

微信号用 **AES-256-GCM** 加密后存入 `users.wechat_id_enc`（格式 `v1:<base64>`），只在本人查看资料或交易意向被接受时解密。与密码的区别：密码用 bcrypt 哈希（不可逆，只需比对），微信号需要展示给对方，所以用可解密的对称加密。

旧数据中的明文微信号可用 `scripts/encrypt_wechat.py` 一次性加密（可重复执行）。

## 前端结构

```
frontend/src/
├── styles/main.css      # 设计规范：港口色板 6 色 + 字体，映射为 shadcn 语义变量和 Tailwind 工具类（bg-ocean、text-buoy、font-display）
├── styles/theme.css     # 旧变量，仅管理后台（Element Plus）使用
├── components/ui/       # shadcn-vue 组件（代码属于项目，可直接修改）
├── composables/confirm.js # 全站共用确认弹窗：await confirm({...})
├── api/http.js          # 请求封装：自动带令牌、统一处理 code、401 跳登录
├── api/index.js         # 接口清单：一个函数对应一个后端接口
├── stores/              # Pinia：user（登录状态）、meta（字典数据）
├── router/index.js      # 路由与登录守卫（meta.auth）
├── layouts/             # SiteLayout：网站外壳（顶部导航、右上角登录、页脚，响应式）；AdminLayout：管理后台
├── components/          # AppHeader 顶部导航、LoginForm 登录表单（弹窗与登录页共用）、PageHeader、ItemCard
└── views/               # 页面；views/admin/ 为管理后台页面（/admin，仅管理员）
```

## 卖家管理物品

```
编辑       待审核 / 在售 / 已驳回 / 已下架(未售出) ──▶ 待审核（内容变了必须重新审核）
下架       待审核 / 在售 / 已驳回 ──▶ 已下架
重新上架   已下架(未售出) ──▶ 待审核
删除       任意状态 ──▶ deleted（软删除）
```

- 任何编辑都回到待审核，防止「先发正常内容过审、再改成违规内容」
- 编辑、下架、删除时，该物品上待处理和已接受的意向自动关闭并通知买家
- 删除是软删除：只把状态改为 `deleted`，数据和成交记录保留，便于追溯纠纷
