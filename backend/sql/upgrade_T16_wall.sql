-- T16 校园墙 · 升级脚本
-- 给「已经在运行」的数据库用：新增 3 张表和 6 个帖子标签。全新安装不需要它（schema.sql 和 seed.py 已包含）。
-- 可以重复执行：表、索引、标签已存在时自动跳过，不会影响已有数据。
--
-- 本地：  .venv\Scripts\python scripts\apply_sql.py sql\upgrade_T16_wall.sql
-- 服务器：docker compose exec -T db psql -U campus_app -d campus < backend/sql/upgrade_T16_wall.sql

-- ⑮ 帖子（校园墙）：公共字段在 contents（type='post'），这里是帖子特有的字段
CREATE TABLE IF NOT EXISTS posts (
  content_id BIGINT PRIMARY KEY REFERENCES contents(id) ON DELETE CASCADE,
  body TEXT NOT NULL,
  images TEXT[] NOT NULL DEFAULT '{}',
  is_official BOOLEAN NOT NULL DEFAULT FALSE,
  pinned_at TIMESTAMPTZ,
  resolved_at TIMESTAMPTZ,
  published_at TIMESTAMPTZ,
  like_count INT NOT NULL DEFAULT 0,
  comment_count INT NOT NULL DEFAULT 0,
  ai_level VARCHAR(16),
  ai_note VARCHAR(200)
);
CREATE INDEX IF NOT EXISTS idx_posts_published ON posts(published_at DESC);

-- ⑯ 帖子评论
CREATE TABLE IF NOT EXISTS post_comments (
  id BIGSERIAL PRIMARY KEY,
  post_id BIGINT NOT NULL REFERENCES posts(content_id) ON DELETE CASCADE,
  user_id BIGINT NOT NULL REFERENCES users(id),
  reply_to_id BIGINT REFERENCES post_comments(id),
  body VARCHAR(300) NOT NULL,
  status VARCHAR(16) NOT NULL DEFAULT 'online',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_post_comments_post ON post_comments(post_id, created_at);

-- ⑰ 帖子点赞：一人对一条帖子只能点一次（联合主键保证）
CREATE TABLE IF NOT EXISTS post_likes (
  post_id BIGINT NOT NULL REFERENCES posts(content_id) ON DELETE CASCADE,
  user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (post_id, user_id)
);

-- 帖子标签：和物品类目、社团类目放在同一张 categories 表里，type='post'
-- 以后想改名或增减标签，直接改这张表的数据即可，不用改代码
INSERT INTO categories (type, name, slug, sort_order) VALUES
  ('post', '失物招领', 'lost_found', 1),
  ('post', '求助',     'help',       2),
  ('post', '搭子',     'buddy',      3),
  ('post', '表白',     'confession', 4),
  ('post', '吐槽',     'rant',       5),
  ('post', '其他',     'other',      6)
ON CONFLICT (type, slug) DO NOTHING;
