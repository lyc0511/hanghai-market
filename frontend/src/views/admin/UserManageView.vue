<!--
  用户管理：按学号 / 昵称搜索，封禁（可同时下架在售物品）/ 解封。
  管理员账号和自己不能封禁，后端也会拦。
-->
<script setup>
import { ElMessage, ElMessageBox } from 'element-plus'
import 'element-plus/es/components/message/style/css'
import 'element-plus/es/components/message-box/style/css'
import { onMounted, reactive, ref } from 'vue'

import { adminApi } from '@/api'
import { formatDate } from '@/lib/time'
import { useUserStore } from '@/stores/user'

const me = useUserStore()
const QUICK = ['多次发布虚假信息', '交易中存在欺诈行为', '发布违禁物品', '辱骂骚扰其他同学']

const query = reactive({ keyword: '', status: '', page: 1, page_size: 20 })
const rows = ref([])
const total = ref(0)
const loading = ref(false)
const busyId = ref(null)
const resetResult = reactive({ visible: false, studentNo: '', password: '' })

async function resetPassword(row) {
  if (busyId.value !== null) return
  try {
    await ElMessageBox.confirm(
      `请先当面或通过可信渠道核实「${row.nickname}（${row.student_no}）」的学生身份。重置会使所有旧登录失效。确认已核实本人身份？`,
      '重置密码', { confirmButtonText: '已核实身份，重置', cancelButtonText: '取消', type: 'warning' },
    )
  } catch {
    return
  }
  busyId.value = row.id
  try {
    const result = await adminApi.resetPassword(row.id)
    Object.assign(resetResult, { visible: true, studentNo: row.student_no, password: result.temporary_password })
  } catch {
    /* 请求失败由统一拦截器提示，可重新操作 */
  } finally {
    busyId.value = null
  }
}
const dialog = reactive({ visible: false, row: null, reason: '', offline_items: true, submitting: false })

async function load() {
  loading.value = true
  try {
    const params = { ...query, keyword: query.keyword.trim() || undefined, status: query.status || undefined }
    const data = await adminApi.users(params)
    rows.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function search() {
  query.page = 1
  load()
}

function canBan(row) {
  return row.role !== 'admin' && row.id !== me.profile?.id
}

function openBan(row) {
  Object.assign(dialog, { visible: true, row, reason: '', offline_items: true, submitting: false })
}

async function submitBan() {
  const reason = dialog.reason.trim()
  if (reason.length < 2) {
    ElMessage.warning('请填写封禁原因（至少 2 个字）')
    return
  }
  dialog.submitting = true
  try {
    await adminApi.banUser(dialog.row.id, { reason, offline_items: dialog.offline_items })
    ElMessage.success('已封禁')
    dialog.visible = false
    load()
  } finally {
    dialog.submitting = false
  }
}

async function unban(row) {
  try {
    await ElMessageBox.confirm(`解封后「${row.nickname}」可以正常登录。之前被下架的物品不会自动上架。`, '解除封禁', {
      confirmButtonText: '解封',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  busyId.value = row.id
  try {
    await adminApi.unbanUser(row.id)
    ElMessage.success('已解除封禁')
    load()
  } finally {
    busyId.value = null
  }
}

onMounted(load)
</script>

<template>
  <el-card shadow="never" class="panel">
    <form class="toolbar" @submit.prevent="search">
      <el-input v-model="query.keyword" placeholder="学号或昵称" clearable style="width: 240px" @clear="search" />
      <el-select v-model="query.status" placeholder="全部状态" clearable style="width: 130px" @change="search">
        <el-option value="active" label="正常" />
        <el-option value="banned" label="已封禁" />
      </el-select>
      <el-button type="primary" native-type="submit">搜索</el-button>
    </form>

    <el-table v-loading="loading" :data="rows" row-key="id" empty-text="没有找到用户">
      <el-table-column label="用户" min-width="180">
        <template #default="{ row }">
          <div class="name">
            {{ row.nickname }}
            <el-tag v-if="row.role === 'admin'" size="small" effect="dark">管理员</el-tag>
          </div>
          <div class="muted">{{ row.student_no }}</div>
        </template>
      </el-table-column>
      <el-table-column label="校区" width="110">
        <template #default="{ row }">{{ row.campus_area || '—' }}</template>
      </el-table-column>
      <el-table-column label="发布物品" width="90" align="right" prop="items_count" />
      <el-table-column label="交易意向" width="90" align="right" prop="intents_count" />
      <el-table-column label="被举报" width="80" align="right">
        <template #default="{ row }">
          <span :class="{ warn: row.reported_count > 0 }">{{ row.reported_count }}</span>
        </template>
      </el-table-column>
      <el-table-column label="注册时间" width="120">
        <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag v-if="row.status === 'banned'" type="danger" size="small">已封禁</el-tag>
          <el-tag v-else type="success" size="small" effect="plain">正常</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="210" fixed="right">
        <template #default="{ row }">
          <template v-if="canBan(row)">
            <el-button v-if="row.status === 'active'" size="small" :disabled="busyId !== null" @click="resetPassword(row)">重置密码</el-button>
            <el-button v-if="row.status === 'active'" type="danger" size="small" plain @click="openBan(row)">封禁</el-button>
            <el-button v-else size="small" :loading="busyId === row.id" @click="unban(row)">解封</el-button>
          </template>
          <span v-else class="muted">—</span>
        </template>
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
        @size-change="search"
      />
    </div>
  </el-card>

  <el-dialog v-model="resetResult.visible" title="临时密码" width="480px" @closed="resetResult.password = ''">
    <p>学号 {{ resetResult.studentNo }}</p>
    <p>请复制并通过私下渠道交给已核实身份的本人。关闭后无法再次查看，可重新生成。</p>
    <el-input :model-value="resetResult.password" readonly aria-label="临时密码" />
    <p>学生用它登录后必须设置新密码。</p>
    <template #footer><el-button @click="resetResult.visible = false">已记录，关闭</el-button></template>
  </el-dialog>

  <el-dialog v-model="dialog.visible" title="封禁用户" width="480px">
    <p class="dialog-item">{{ dialog.row?.nickname }}（{{ dialog.row?.student_no }}）</p>
    <p class="muted">封禁后对方立即无法登录和操作，已登录的设备也会失效。</p>
    <div class="quick">
      <el-tag v-for="q in QUICK" :key="q" class="quick-tag" effect="plain" @click="dialog.reason = q">{{ q }}</el-tag>
    </div>
    <el-input v-model="dialog.reason" type="textarea" :rows="3" maxlength="200" show-word-limit placeholder="封禁原因，2–200 字" />
    <el-checkbox v-model="dialog.offline_items" class="offline">
      同时下架其在售物品（{{ dialog.row?.items_count }} 件发布记录中正在展示的）
    </el-checkbox>
    <template #footer>
      <el-button @click="dialog.visible = false">取消</el-button>
      <el-button type="danger" :loading="dialog.submitting" @click="submitBan">确认封禁</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.panel {
  border-radius: var(--r);
}
.toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}
.name {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 500;
  color: var(--text-1);
}
.muted {
  margin: 2px 0 0;
  color: var(--text-3);
  font-size: 12px;
}
.warn {
  color: var(--hot);
  font-weight: 600;
}
.pager {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
.dialog-item {
  margin: 0;
  font-weight: 500;
}
.quick {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 12px 0 10px;
}
.quick-tag {
  cursor: pointer;
}
.offline {
  margin-top: 10px;
}
</style>
