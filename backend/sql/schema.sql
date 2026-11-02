-- 校园二手交易与社团活动一体化平台 · 建表脚本（T01）
-- 用法：在 DataGrip 中以 campus_app 身份连接 campus 库，整体执行本文件。
-- 本文件只建表，不含 CREATE DATABASE / CREATE EXTENSION。

-- ① 用户
CREATE TABLE users (
  id            BIGSERIAL PRIMARY KEY,
  student_no    VARCHAR(20)  NOT NULL UNIQUE,
  nickname      VARCHAR(30)  NOT NULL,
  password_hash VARCHAR(100) NOT NULL,
  avatar_url    TEXT,
  campus_area   VARCHAR(32),
  wechat_id_enc TEXT,
  wechat_visible BOOLEAN     NOT NULL DEFAULT TRUE,
  role          VARCHAR(16)  NOT NULL DEFAULT 'student',
  auth_source   VARCHAR(16)  NOT NULL DEFAULT 'open',
  status        VARCHAR(16)  NOT NULL DEFAULT 'active',
  created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- ② 类目
CREATE TABLE categories (
  id SERIAL PRIMARY KEY,
  type VARCHAR(16) NOT NULL,
  name VARCHAR(32) NOT NULL,
  slug VARCHAR(32) NOT NULL,
  sort_order SMALLINT NOT NULL DEFAULT 0,
  UNIQUE (type, slug)
);

-- ③ 统一内容表
CREATE TABLE contents (
  id BIGSERIAL PRIMARY KEY,
  type VARCHAR(16)  NOT NULL,
  owner_id BIGINT   NOT NULL REFERENCES users(id),
  title VARCHAR(120) NOT NULL,
  summary VARCHAR(300),
  category_id INT   REFERENCES categories(id),
  tags TEXT[]       NOT NULL DEFAULT '{}',
  campus_area VARCHAR(32),
  status VARCHAR(16) NOT NULL DEFAULT 'online',
  reject_reason VARCHAR(200),
  view_count INT    NOT NULL DEFAULT 0,
  search_text TEXT,
  embedding_text TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_contents_type_status ON contents(type, status);
CREATE INDEX idx_contents_owner ON contents(owner_id);
CREATE INDEX idx_contents_created ON contents(created_at DESC);
CREATE INDEX idx_contents_tags ON contents USING GIN(tags);

-- ④ 二手物品
CREATE TABLE items (
  content_id BIGINT PRIMARY KEY REFERENCES contents(id) ON DELETE CASCADE,
  price NUMERIC(10,2) NOT NULL DEFAULT 0,
  original_price NUMERIC(10,2),
  condition VARCHAR(16) NOT NULL DEFAULT 'good',
  images TEXT[] NOT NULL DEFAULT '{}',
  sold_at TIMESTAMPTZ
);
CREATE INDEX idx_items_price ON items(price);

-- ⑤ 社团
CREATE TABLE clubs (
  content_id BIGINT PRIMARY KEY REFERENCES contents(id) ON DELETE CASCADE,
  logo_url TEXT,
  club_type VARCHAR(32) NOT NULL,
  founded_year SMALLINT,
  president_id BIGINT REFERENCES users(id),
  member_count INT NOT NULL DEFAULT 0,
  recruit_status VARCHAR(16) NOT NULL DEFAULT 'closed',
  recruit_start DATE,
  recruit_end DATE,
  recruit_note VARCHAR(300)
);

-- ⑥ 活动
CREATE TABLE activities (
  content_id BIGINT PRIMARY KEY REFERENCES contents(id) ON DELETE CASCADE,
  club_id BIGINT NOT NULL REFERENCES clubs(content_id) ON DELETE CASCADE,
  start_time TIMESTAMPTZ NOT NULL,
  end_time TIMESTAMPTZ NOT NULL,
  location VARCHAR(128) NOT NULL,
  capacity INT NOT NULL CHECK (capacity > 0),
  enrolled_count INT NOT NULL DEFAULT 0,
  signup_deadline TIMESTAMPTZ
);
CREATE INDEX idx_activities_start ON activities(start_time);

-- ⑦ 交易意向
CREATE TABLE trade_intents (
  id BIGSERIAL PRIMARY KEY,
  item_id BIGINT NOT NULL REFERENCES items(content_id),
  buyer_id BIGINT NOT NULL REFERENCES users(id),
  seller_id BIGINT NOT NULL REFERENCES users(id),
  message VARCHAR(200),
  status VARCHAR(16) NOT NULL DEFAULT 'pending',
  contact_revealed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uq_intent_active ON trade_intents(item_id, buyer_id)
  WHERE status IN ('pending','accepted','completed');
CREATE INDEX idx_intents_buyer ON trade_intents(buyer_id, status);
CREATE INDEX idx_intents_seller ON trade_intents(seller_id, status);

-- ⑧ 社团成员
CREATE TABLE club_members (
  club_id BIGINT NOT NULL REFERENCES clubs(content_id) ON DELETE CASCADE,
  user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role VARCHAR(16) NOT NULL DEFAULT 'member',
  joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (club_id, user_id)
);

-- ⑨ 入社申请
CREATE TABLE club_applications (
  id BIGSERIAL PRIMARY KEY,
  club_id BIGINT NOT NULL REFERENCES clubs(content_id) ON DELETE CASCADE,
  user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  reason VARCHAR(300) NOT NULL,
  status VARCHAR(16) NOT NULL DEFAULT 'pending',
  reviewed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uq_club_app_pending ON club_applications(club_id, user_id)
  WHERE status = 'pending';

-- ⑩ 活动报名
CREATE TABLE activity_signups (
  id BIGSERIAL PRIMARY KEY,
  activity_id BIGINT NOT NULL REFERENCES activities(content_id) ON DELETE CASCADE,
  user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  status VARCHAR(16) NOT NULL DEFAULT 'signed',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (activity_id, user_id)
);

-- ⑪ 通知
CREATE TABLE notifications (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  type VARCHAR(32) NOT NULL,
  title VARCHAR(80) NOT NULL,
  body VARCHAR(300),
  link VARCHAR(200),
  is_read BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_notif_user ON notifications(user_id, is_read, created_at DESC);

-- ⑫ 举报
CREATE TABLE reports (
  id BIGSERIAL PRIMARY KEY,
  target_type VARCHAR(16) NOT NULL,
  target_id BIGINT NOT NULL,
  reporter_id BIGINT NOT NULL REFERENCES users(id),
  reason VARCHAR(32) NOT NULL,
  description VARCHAR(300),
  status VARCHAR(16) NOT NULL DEFAULT 'pending',
  handled_by BIGINT REFERENCES users(id),
  handle_note VARCHAR(300),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ⑬ AI 对话记录
CREATE TABLE ai_messages (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT REFERENCES users(id),
  session_id VARCHAR(64) NOT NULL,
  query VARCHAR(300) NOT NULL,
  intent VARCHAR(32),
  slots JSONB,
  result_ids BIGINT[] NOT NULL DEFAULT '{}',
  fallback BOOLEAN NOT NULL DEFAULT FALSE,
  latency_ms INT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_ai_session ON ai_messages(session_id, created_at);

-- ⑭ 管理操作日志
CREATE TABLE audit_logs (
  id BIGSERIAL PRIMARY KEY,
  admin_id BIGINT NOT NULL REFERENCES users(id),
  action VARCHAR(64) NOT NULL,
  target_type VARCHAR(16),
  target_id BIGINT,
  detail JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
