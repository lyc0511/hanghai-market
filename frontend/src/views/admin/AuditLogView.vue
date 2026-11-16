<!-- 操作日志：所有管理员操作（审核、举报处理、封禁）都有记录，只读 -->
<script setup>
import { onMounted, reactive, ref } from 'vue'

import { adminApi } from '@/api'
import { formatDateTime } from '@/lib/time'

const ACTIONS = {
  approve_item: { label: '物品审核通过', type: 'success' },
  reject_item: { label: '物品审核驳回', type: 'warning' },
  approve_activity: { label: '活动审核通过', type: 'success' },
  reject_activity: { label: '活动审核驳回', type: 'warning' },
  approve_post: { label: '投稿审核通过', type: 'success' },
  reject_post: { label: '投稿审核退回', type: 'warning' },
  offline_post: { label: '下架帖子', type: 'danger' },
  official_post: { label: '发布官方帖', type: 'success' },
  pin_post: { label: '置顶帖子', type: 'info' },
  unpin_post: { label: '取消置顶', type: 'info' },
  offline_comment: { label: '下架评论', type: 'danger' },
  resolve_report: { label: '举报属实', type: 'danger' },
  dismiss_report: { label: '驳回举报', type: 'info' },
  ban_user: { label: '封禁用户', type: 'danger' },
  unban_user: { label: '解除封禁', type: 'success' },
}
const TARGET_PATH = { item: '/items/', activity: '/activities/', club: '/clubs/', post: '/wall/' }
const TYPE_LABELS = { item: '物品', club: '社团', activity: '活动', post: '帖子', comment: '评论', report: '举报', user: '用户' }

const query = reactive({ action: '', page: 1, page_size: 20 })
const rows = ref([])
const total = ref(0)
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const data = await adminApi.auditLogs({ ...query, action: query.action || undefined })
    rows.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function reset() {
  query.page = 1
  load()
}

/** 把 detail 里的关键信息翻成一句话 */
function describe(row) {
  const d = row.detail || {}
  const parts = []
  if (d.reason) parts.push(`原因：${d.reason}`)
  if (d.note) parts.push(`说明：${d.note}`)
  if (d.content_type) parts.push(`${TYPE_LABELS[d.content_type]} #${d.content_id}`)
  if (d.takedown) parts.push('已下架内容')
  if (d.also_resolved?.length) parts.push(`一并办结 ${d.also_resolved.length} 条举报`)
  if (d.offline_items?.length) parts.push(`下架物品 ${d.offline_items.length} 件`)
  return parts.join('；') || '—'
}

onMounted(load)
</script>

<template>
  <el-card shadow="never" class="panel">
    <div class="toolbar">
      <el-select v-model="query.action" placeholder="全部操作" clearable style="width: 180px" @change="reset">
        <el-option v-for="(a, key) in ACTIONS" :key="key" :value="key" :label="a.label" />
      </el-select>
      <span class="muted">共 {{ total }} 条记录，最新在前</span>
    </div>

    <el-table v-loading="loading" :data="rows" row-key="id" empty-text="暂无操作记录">
      <el-table-column label="时间" width="170">
        <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="管理员" width="110" prop="admin_nickname" />
      <el-table-column label="操作" width="140">
        <template #default="{ row }">
          <el-tag :type="ACTIONS[row.action]?.type || 'info'" size="small">{{ ACTIONS[row.action]?.label || row.action }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="对象" width="130">
        <template #default="{ row }">
          <a v-if="TARGET_PATH[row.target_type]" :href="TARGET_PATH[row.target_type] + row.target_id" target="_blank" rel="noopener" class="link">
            {{ TYPE_LABELS[row.target_type] }} #{{ row.target_id }}
          </a>
          <span v-else>{{ TYPE_LABELS[row.target_type] || row.target_type }} #{{ row.target_id }}</span>
        </template>
      </el-table-column>
      <el-table-column label="详情" min-width="260">
        <template #default="{ row }"><span class="detail">{{ describe(row) }}</span></template>
      </el-table-column>
    </el-table>

    <div class="pager">
      <el-pagination
        v-model:current-page="query.page"
        v-model:page-size="query.page_size"
        :total="total"
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        background
        @current-change="load"
        @size-change="reset"
      />
    </div>
  </el-card>
</template>

<style scoped>
.panel {
  border-radius: var(--r);
}
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
.muted {
  color: var(--text-3);
  font-size: 12px;
}
.link {
  color: var(--brand);
}
.detail {
  font-size: 12px;
  color: var(--text-2);
}
.pager {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
