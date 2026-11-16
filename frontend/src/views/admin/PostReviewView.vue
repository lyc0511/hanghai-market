<!--
  墙审核：先审后发的「审」。这里是唯一能看到真实投稿人的地方。
  AI 预审结果只是参考，通过与否由管理员决定。
-->
<script setup>
import { ElMessage, ElMessageBox } from 'element-plus'
import 'element-plus/es/components/message/style/css'
import 'element-plus/es/components/message-box/style/css'
import { onMounted, reactive, ref } from 'vue'

import { adminApi } from '@/api'
import { useMetaStore } from '@/stores/meta'
import { formatDateTime } from '@/lib/time'

const meta = useMetaStore()

const TABS = [
  { name: 'pending', label: '待审核' },
  { name: 'online', label: '已上墙' },
  { name: 'rejected', label: '已退回' },
  { name: 'offline', label: '已下架' },
]
// 常用退回原因，点一下就能填进输入框
const QUICK_REASONS = [
  '包含他人隐私（姓名、宿舍、联系方式等），请去掉后重新投稿',
  '内容针对具体个人，不适合公开发布',
  '图片里有他人的头像或名字，请打码后重新投稿',
  '疑似广告或引流信息',
  '内容不完整，请补充时间、地点等信息',
]
const AI_LABELS = { ok: ['未发现问题', 'success'], attention: ['需要留意', 'warning'] }

const query = reactive({ status: 'pending', page: 1, page_size: 10 })
const rows = ref([])
const total = ref(0)
const loading = ref(false)
const busyId = ref(null)

// 退回（待审核的帖子）和下架（已上墙的帖子）共用一个弹窗，用 mode 区分
const rejectDialog = reactive({ visible: false, mode: 'reject', post: null, reason: '', submitting: false })
const DIALOG_TEXT = {
  reject: { title: '退回投稿', confirm: '确认退回', done: '已退回，已通知投稿人', hint: '退回原因会通知给投稿人，对方可以修改后重新投稿，2–200 字' },
  offline: { title: '下架帖子', confirm: '确认下架', done: '已下架，已通知投稿人', hint: '下架原因会通知给投稿人，2–200 字' },
}

async function load() {
  loading.value = true
  try {
    const data = await adminApi.posts(query)
    rows.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function onTab() {
  query.page = 1
  load()
}

async function approve(row) {
  try {
    await ElMessageBox.confirm('通过后这条帖子会匿名出现在墙上，所有登录的同学都能看到。', '审核通过', {
      confirmButtonText: '通过',
      cancelButtonText: '取消',
      type: 'success',
    })
  } catch {
    return
  }
  busyId.value = row.id
  try {
    await adminApi.approvePost(row.id)
    ElMessage.success('已通过，帖子已上墙')
    load()
  } finally {
    busyId.value = null
  }
}

// 发布官方帖：不用审核，直接上墙
const official = reactive({ visible: false, tagId: null, body: '', pinned: true, submitting: false })

function openOfficial() {
  Object.assign(official, { visible: true, tagId: meta.postTags.find((t) => t.slug === 'other')?.id ?? null, body: '', pinned: true })
}

async function submitOfficial() {
  const body = official.body.trim()
  if (!official.tagId) return ElMessage.warning('请选择标签')
  if (body.length < 2 || body.length > 500) return ElMessage.warning('正文 2–500 个字')
  official.submitting = true
  try {
    await adminApi.createOfficialPost({ tag_id: official.tagId, body, pinned: official.pinned })
    ElMessage.success('已发布')
    official.visible = false
    query.status = 'online'
    onTab()
  } finally {
    official.submitting = false
  }
}

async function togglePin(row) {
  busyId.value = row.id
  try {
    await (row.pinned ? adminApi.unpinPost(row.id) : adminApi.pinPost(row.id))
    ElMessage.success(row.pinned ? '已取消置顶' : '已置顶')
    load()
  } finally {
    busyId.value = null
  }
}

function openReject(row, mode = 'reject') {
  Object.assign(rejectDialog, { visible: true, mode, post: row, reason: '', submitting: false })
}

async function submitReject() {
  const reason = rejectDialog.reason.trim()
  if (reason.length < 2 || reason.length > 200) {
    ElMessage.warning('原因 2–200 个字')
    return
  }
  rejectDialog.submitting = true
  try {
    const api = rejectDialog.mode === 'offline' ? adminApi.offlinePost : adminApi.rejectPost
    await api(rejectDialog.post.id, reason)
    ElMessage.success(DIALOG_TEXT[rejectDialog.mode].done)
    rejectDialog.visible = false
    load()
  } finally {
    rejectDialog.submitting = false
  }
}

onMounted(() => {
  meta.load().catch(() => {})
  load()
})
</script>

<template>
  <el-card shadow="never" class="panel">
    <div class="top">
      <el-tabs v-model="query.status" class="tabs" @tab-change="onTab">
        <el-tab-pane v-for="t in TABS" :key="t.name" :name="t.name" :label="t.label" />
      </el-tabs>
      <el-button type="primary" plain @click="openOfficial">发布官方帖</el-button>
    </div>

    <el-table v-loading="loading" :data="rows" row-key="id" empty-text="暂无数据">
      <el-table-column label="内容" min-width="360">
        <template #default="{ row }">
          <div class="marks">
            <el-tag v-if="row.is_official" size="small" type="primary">官方</el-tag>
            <el-tag v-if="row.pinned" size="small" type="warning">置顶</el-tag>
          </div>
          <div class="body">{{ row.body }}</div>
          <div v-if="row.images.length" class="images">
            <el-image
              v-for="(src, i) in row.images"
              :key="src"
              :src="src"
              :preview-src-list="row.images"
              :initial-index="i"
              fit="cover"
              class="thumb"
              preview-teleported
            >
              <template #error><div class="ph">无图</div></template>
            </el-image>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="标签" width="100">
        <template #default="{ row }">
          <el-tag v-if="row.tag" size="small" effect="plain">{{ row.tag.name }}</el-tag>
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
      <el-table-column label="AI 预审" width="170">
        <template #default="{ row }">
          <template v-if="AI_LABELS[row.ai_level]">
            <el-tag size="small" :type="AI_LABELS[row.ai_level][1]">{{ AI_LABELS[row.ai_level][0] }}</el-tag>
            <div v-if="row.ai_note" class="muted note">{{ row.ai_note }}</div>
          </template>
          <span v-else class="muted">未预审</span>
          <div v-if="row.images.length" class="muted note">AI 只看文字，图片请自己检查</div>
        </template>
      </el-table-column>
      <el-table-column label="投稿人（仅管理员可见）" width="170">
        <template #default="{ row }">
          <div>{{ row.author.nickname }}</div>
          <div class="muted">学号 {{ row.author.student_no }}</div>
        </template>
      </el-table-column>
      <el-table-column label="投稿时间" width="160">
        <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column :label="['pending', 'online'].includes(query.status) ? '操作' : '备注'" width="190" fixed="right">
        <template #default="{ row }">
          <template v-if="row.status === 'pending'">
            <el-button type="primary" size="small" :loading="busyId === row.id" @click="approve(row)">通过</el-button>
            <el-button type="danger" size="small" plain :disabled="busyId === row.id" @click="openReject(row)">退回</el-button>
          </template>
          <template v-else-if="row.status === 'online'">
            <div class="muted">{{ formatDateTime(row.published_at) }} 上墙</div>
            <div class="mt">
              <el-button size="small" :loading="busyId === row.id" @click="togglePin(row)">{{ row.pinned ? '取消置顶' : '置顶' }}</el-button>
              <el-button type="danger" size="small" plain @click="openReject(row, 'offline')">下架</el-button>
            </div>
          </template>
          <span v-else-if="row.reject_reason" class="reason">{{ row.reject_reason }}</span>
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
    </el-table>

    <div class="pager">
      <el-pagination
        v-model:current-page="query.page"
        v-model:page-size="query.page_size"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        background
        @current-change="load"
        @size-change="onTab"
      />
    </div>
  </el-card>

  <el-dialog v-model="official.visible" title="发布官方帖" width="520px">
    <p class="muted hint">官方帖不用审核，发布后立刻出现在墙上，显示为「官方」。适合发规则说明和通知。</p>
    <el-select v-model="official.tagId" placeholder="选择标签" style="width: 160px; margin-bottom: 10px">
      <el-option v-for="t in meta.postTags" :key="t.id" :value="t.id" :label="t.name" />
    </el-select>
    <el-input v-model="official.body" type="textarea" :rows="6" maxlength="500" show-word-limit placeholder="正文，2–500 字" />
    <el-checkbox v-model="official.pinned" class="mt">同时置顶</el-checkbox>
    <template #footer>
      <el-button @click="official.visible = false">取消</el-button>
      <el-button type="primary" :loading="official.submitting" @click="submitOfficial">发布</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="rejectDialog.visible" :title="DIALOG_TEXT[rejectDialog.mode].title" width="520px">
    <p class="dialog-body">{{ rejectDialog.post?.body }}</p>
    <div class="quick">
      <el-tag v-for="r in QUICK_REASONS" :key="r" class="quick-tag" effect="plain" @click="rejectDialog.reason = r">
        {{ r }}
      </el-tag>
    </div>
    <el-input
      v-model="rejectDialog.reason"
      type="textarea"
      :rows="3"
      maxlength="200"
      show-word-limit
      :placeholder="DIALOG_TEXT[rejectDialog.mode].hint"
    />
    <template #footer>
      <el-button @click="rejectDialog.visible = false">取消</el-button>
      <el-button type="danger" :loading="rejectDialog.submitting" @click="submitReject">{{ DIALOG_TEXT[rejectDialog.mode].confirm }}</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.panel {
  border-radius: var(--r);
}
.top {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}
.tabs {
  flex: 1;
  min-width: 0;
}
.marks {
  display: flex;
  gap: 4px;
  margin-bottom: 4px;
}
.marks:empty {
  display: none;
}
.hint {
  margin: 0 0 12px;
  line-height: 1.6;
}
.body {
  color: var(--text-1);
  line-height: 1.6;
  white-space: pre-line;
  word-break: break-word;
}
.images {
  margin-top: 8px;
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.thumb {
  width: 60px;
  height: 60px;
  border-radius: 8px;
  background: var(--brand-soft);
}
.ph {
  width: 100%;
  height: 100%;
  display: grid;
  place-items: center;
  font-size: 12px;
  color: var(--text-3);
}
.muted {
  color: var(--text-3);
  font-size: 12px;
}
.note {
  margin-top: 4px;
  line-height: 1.5;
}
.reason {
  color: var(--danger);
  font-size: 12px;
}
.mt {
  margin-top: 6px;
}
.pager {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
.dialog-body {
  margin: 0 0 12px;
  max-height: 120px;
  overflow: auto;
  padding: 10px 12px;
  border-radius: 8px;
  background: var(--brand-soft);
  white-space: pre-line;
  word-break: break-word;
}
.quick {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 10px;
}
.quick-tag {
  cursor: pointer;
  height: auto;
  white-space: normal;
  padding: 4px 8px;
  line-height: 1.4;
}
</style>
