<script setup>
import { ElMessage, ElMessageBox } from 'element-plus'
import 'element-plus/es/components/message/style/css'
import 'element-plus/es/components/message-box/style/css'
import { onMounted, reactive, ref } from 'vue'

import { adminApi } from '@/api'
import { timeRange } from '@/lib/activity'
import { formatDateTime } from '@/lib/time'

const TABS = [
  { name: 'pending', label: '待审核' },
  { name: 'online', label: '已上架' },
  { name: 'rejected', label: '已驳回' },
]
// 常用驳回原因，点一下就能填进输入框
const QUICK_REASONS = ['活动时间或地点不明确，请补充', '活动内容与社团宗旨不符', '涉及校外商业推广，不予发布', '名额设置不合理，请核实场地容量']

const query = reactive({ status: 'pending', page: 1, page_size: 10 })
const rows = ref([])
const total = ref(0)
const loading = ref(false)
const busyId = ref(null)
const rejectDialog = reactive({ visible: false, row: null, reason: '', submitting: false })

async function load() {
  loading.value = true
  try {
    const data = await adminApi.activities(query)
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
    await ElMessageBox.confirm(`通过后「${row.title}」将对全校同学开放报名。`, '审核通过', {
      confirmButtonText: '通过',
      cancelButtonText: '取消',
      type: 'success',
    })
  } catch {
    return
  }
  busyId.value = row.id
  try {
    await adminApi.approveActivity(row.id)
    ElMessage.success('已通过，活动已上架')
    load()
  } finally {
    busyId.value = null
  }
}

function openReject(row) {
  Object.assign(rejectDialog, { visible: true, row, reason: '', submitting: false })
}

async function submitReject() {
  const reason = rejectDialog.reason.trim()
  if (reason.length < 2 || reason.length > 200) {
    ElMessage.warning('驳回原因 2–200 个字')
    return
  }
  rejectDialog.submitting = true
  try {
    await adminApi.rejectActivity(rejectDialog.row.id, reason)
    ElMessage.success('已驳回，已通知会长')
    rejectDialog.visible = false
    load()
  } finally {
    rejectDialog.submitting = false
  }
}

onMounted(load)
</script>

<template>
  <el-card shadow="never" class="panel">
    <el-tabs v-model="query.status" @tab-change="onTab">
      <el-tab-pane v-for="t in TABS" :key="t.name" :name="t.name" :label="t.label" />
    </el-tabs>

    <el-table v-loading="loading" :data="rows" row-key="id" empty-text="暂无数据">
      <el-table-column label="活动" min-width="240">
        <template #default="{ row }">
          <div class="title">{{ row.title }}</div>
          <div class="summary">{{ row.summary || '（无介绍）' }}</div>
        </template>
      </el-table-column>
      <el-table-column label="主办社团" width="140">
        <template #default="{ row }">{{ row.club.title }}</template>
      </el-table-column>
      <el-table-column label="时间 / 地点" min-width="220">
        <template #default="{ row }">
          <div>{{ timeRange(row.start_time, row.end_time) }}</div>
          <div class="muted">{{ row.location }}</div>
        </template>
      </el-table-column>
      <el-table-column label="名额" width="90">
        <template #default="{ row }">{{ row.enrolled_count }}/{{ row.capacity }}</template>
      </el-table-column>
      <el-table-column label="提交时间" width="170">
        <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column :label="query.status === 'pending' ? '操作' : '备注'" width="180" fixed="right">
        <template #default="{ row }">
          <template v-if="row.status === 'pending'">
            <el-button type="primary" size="small" :loading="busyId === row.id" @click="approve(row)">通过</el-button>
            <el-button type="danger" size="small" plain :disabled="busyId === row.id" @click="openReject(row)">驳回</el-button>
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

  <el-dialog v-model="rejectDialog.visible" title="驳回活动" width="480px">
    <p class="dialog-item">「{{ rejectDialog.row?.title }}」</p>
    <div class="quick">
      <el-tag v-for="r in QUICK_REASONS" :key="r" class="quick-tag" effect="plain" @click="rejectDialog.reason = r">{{ r }}</el-tag>
    </div>
    <el-input v-model="rejectDialog.reason" type="textarea" :rows="3" maxlength="200" show-word-limit placeholder="驳回原因会通知给会长，2–200 字" />
    <template #footer>
      <el-button @click="rejectDialog.visible = false">取消</el-button>
      <el-button type="danger" :loading="rejectDialog.submitting" @click="submitReject">确认驳回</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.panel {
  border-radius: var(--r);
}
.title {
  font-weight: 500;
  color: var(--text-1);
}
.summary {
  margin-top: 2px;
  color: var(--text-2);
  font-size: 12px;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.muted {
  color: var(--text-3);
  font-size: 12px;
}
.reason {
  color: var(--danger);
  font-size: 12px;
}
.pager {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
.dialog-item {
  margin: 0 0 12px;
  font-weight: 500;
}
.quick {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 10px;
}
.quick-tag {
  cursor: pointer;
}
</style>
