<!--
  举报处理：待处理 / 已处理 / 已驳回。
  处理时二选一：「举报属实」（可勾选同时下架内容）或「驳回举报」，处理说明会通知举报人。
-->
<script setup>
import { ElMessage } from 'element-plus'
import 'element-plus/es/components/message/style/css'
import { computed, onMounted, reactive, ref } from 'vue'

import { adminApi } from '@/api'
import { formatDateTime } from '@/lib/time'

const TABS = [
  { name: 'pending', label: '待处理' },
  { name: 'resolved', label: '举报属实' },
  { name: 'dismissed', label: '已驳回' },
]
const TYPE_LABELS = { item: '物品', club: '社团', activity: '活动' }
const REASON_LABELS = { fraud: '疑似诈骗', prohibited: '违禁物品', false_info: '虚假信息', spam: '广告刷屏', abuse: '辱骂骚扰', other: '其他' }
const CONTENT_STATUS = { online: '展示中', offline: '已下架', pending: '待审核', rejected: '已驳回', deleted: '已删除' }
const QUICK = {
  resolve: ['经核实内容违规，已下架处理', '经核实存在虚假描述，已下架处理', '已联系发布者整改'],
  dismiss: ['经核实未发现违规', '属于正常交易范围，不予处理', '信息不足，暂无法认定违规'],
}

const query = reactive({ status: 'pending', target_type: '', page: 1, page_size: 10 })
const rows = ref([])
const total = ref(0)
const loading = ref(false)
const dialog = reactive({ visible: false, row: null, action: 'resolve', note: '', takedown: true, submitting: false })

const canTakedown = computed(() => dialog.row?.target.status === 'online')

async function load() {
  loading.value = true
  try {
    const params = { ...query, target_type: query.target_type || undefined }
    const data = await adminApi.reports(params)
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

function openHandle(row, action) {
  Object.assign(dialog, { visible: true, row, action, note: '', takedown: row.target.status === 'online', submitting: false })
}

async function submit() {
  const note = dialog.note.trim()
  if (!note) {
    ElMessage.warning('请填写处理说明，它会通知给举报人')
    return
  }
  dialog.submitting = true
  try {
    await adminApi.handleReport(dialog.row.id, {
      action: dialog.action,
      note,
      takedown: dialog.action === 'resolve' && dialog.takedown && canTakedown.value,
    })
    ElMessage.success(dialog.action === 'dismiss' ? '已驳回举报' : '已处理')
    dialog.visible = false
    load()
  } finally {
    dialog.submitting = false
  }
}

onMounted(load)
</script>

<template>
  <el-card shadow="never" class="panel">
    <div class="toolbar">
      <el-tabs v-model="query.status" class="tabs" @tab-change="reset">
        <el-tab-pane v-for="t in TABS" :key="t.name" :name="t.name" :label="t.label" />
      </el-tabs>
      <el-select v-model="query.target_type" placeholder="全部类型" clearable style="width: 140px" @change="reset">
        <el-option v-for="(label, key) in TYPE_LABELS" :key="key" :value="key" :label="label" />
      </el-select>
    </div>

    <el-table v-loading="loading" :data="rows" row-key="id" empty-text="暂无举报">
      <el-table-column label="被举报内容" min-width="220">
        <template #default="{ row }">
          <el-tag size="small" effect="plain">{{ TYPE_LABELS[row.target.type] }}</el-tag>
          <a :href="row.target.link" target="_blank" rel="noopener" class="title">{{ row.target.title }}</a>
          <div class="muted">
            发布者 {{ row.owner.nickname }} · {{ CONTENT_STATUS[row.target.status] || row.target.status }}
            <el-tag v-if="row.status === 'pending' && row.same_target_pending > 1" size="small" type="danger" class="ml">
              被 {{ row.same_target_pending }} 人举报
            </el-tag>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="举报原因" min-width="220">
        <template #default="{ row }">
          <el-tag size="small" type="warning">{{ REASON_LABELS[row.reason] }}</el-tag>
          <div class="desc">{{ row.description || '（未填写说明）' }}</div>
        </template>
      </el-table-column>
      <el-table-column label="举报人" width="140">
        <template #default="{ row }">
          <div>{{ row.reporter.nickname }}</div>
          <div class="muted">{{ row.reporter.student_no }}</div>
        </template>
      </el-table-column>
      <el-table-column label="举报时间" width="160">
        <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column :label="query.status === 'pending' ? '操作' : '处理结果'" width="200" fixed="right">
        <template #default="{ row }">
          <template v-if="row.status === 'pending'">
            <el-button type="danger" size="small" @click="openHandle(row, 'resolve')">属实</el-button>
            <el-button size="small" @click="openHandle(row, 'dismiss')">驳回</el-button>
          </template>
          <template v-else>
            <div class="note">{{ row.handle_note }}</div>
            <div class="muted">处理人 {{ row.handler?.nickname || '—' }}</div>
          </template>
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
        @size-change="reset"
      />
    </div>
  </el-card>

  <el-dialog v-model="dialog.visible" :title="dialog.action === 'resolve' ? '举报属实' : '驳回举报'" width="500px">
    <p class="dialog-item">
      {{ TYPE_LABELS[dialog.row?.target.type] }}「{{ dialog.row?.target.title }}」· {{ REASON_LABELS[dialog.row?.reason] }}
    </p>
    <el-checkbox v-if="dialog.action === 'resolve'" v-model="dialog.takedown" :disabled="!canTakedown" class="takedown">
      同时下架该{{ TYPE_LABELS[dialog.row?.target.type] }}，并通知发布者
      <span v-if="!canTakedown" class="muted">（内容已不在展示中）</span>
    </el-checkbox>
    <div class="quick">
      <el-tag v-for="q in QUICK[dialog.action]" :key="q" class="quick-tag" effect="plain" @click="dialog.note = q">{{ q }}</el-tag>
    </div>
    <el-input v-model="dialog.note" type="textarea" :rows="3" maxlength="300" show-word-limit placeholder="处理说明会通过站内通知发给举报人" />
    <p v-if="dialog.action === 'resolve' && dialog.takedown && canTakedown && dialog.row?.same_target_pending > 1" class="muted hint">
      同一内容的其余 {{ dialog.row.same_target_pending - 1 }} 条待处理举报会一并标为属实。
    </p>
    <template #footer>
      <el-button @click="dialog.visible = false">取消</el-button>
      <el-button :type="dialog.action === 'resolve' ? 'danger' : 'primary'" :loading="dialog.submitting" @click="submit">确认</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.panel {
  border-radius: var(--r);
}
.toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
}
.tabs {
  flex: 1;
}
.title {
  margin-left: 6px;
  font-weight: 500;
  color: var(--text-1);
}
.title:hover {
  color: var(--brand);
  text-decoration: underline;
}
.desc {
  margin-top: 4px;
  color: var(--text-2);
  font-size: 12px;
  line-height: 1.5;
}
.muted {
  margin-top: 2px;
  color: var(--text-3);
  font-size: 12px;
}
.note {
  font-size: 12px;
  color: var(--text-1);
}
.ml {
  margin-left: 4px;
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
.takedown {
  margin-bottom: 10px;
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
.hint {
  margin-top: 8px;
}
</style>
