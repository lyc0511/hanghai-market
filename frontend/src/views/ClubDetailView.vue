<!-- 社团详情：简介、招新信息、成员，以及申请 / 退出 / 会长编辑 -->
<script setup>
import { Loader2 } from '@lucide/vue'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'

import { clubApi } from '@/api'
import ClubActivities from '@/components/ClubActivities.vue'
import PageHeader from '@/components/PageHeader.vue'
import SignalFlag from '@/components/SignalFlag.vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { Textarea } from '@/components/ui/textarea'
import { confirm } from '@/composables/confirm'
import { useMetaStore } from '@/stores/meta'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const meta = useMetaStore()
const user = useUserStore()

const club = ref(null)
const members = ref([])
const memberTotal = ref(0)
const memberPage = ref(1)
const notFound = ref(false)
const MEMBER_SIZE = 20

const applyOpen = ref(false)
const reason = ref('')
const sending = ref(false)
const editOpen = ref(false)
const saving = ref(false)
const editForm = reactive({
  summary: '',
  recruit_status: 'closed',
  recruit_start: '',
  recruit_end: '',
  recruit_note: '',
})

const action = computed(() => {
  const c = club.value
  if (!c) return ''
  if (c.my_status === 'president') return 'president'
  if (c.my_status === 'member') return 'member'
  if (c.my_status === 'pending') return 'pending'
  if (c.recruiting_now) return 'apply'
  return 'closed'
})

function typeName(code) {
  return meta.enums?.club_type?.[code] ?? ''
}

function roleName(role) {
  return role === 'president' ? '会长' : '成员'
}

function dateText(start, end) {
  const a = (start || '').slice(0, 10)
  const b = (end || '').slice(0, 10)
  if (a && b) return `${a} 至 ${b}`
  return a || b
}

async function load() {
  const id = route.params.id
  memberPage.value = 1
  try {
    const data = await clubApi.detail(id)
    if (route.params.id !== id) return
    club.value = data
    notFound.value = false
    document.title = `${data.title} · 航海集市`
  } catch {
    if (route.params.id !== id) return
    notFound.value = true
    club.value = null
    return
  }
  try {
    const data = await clubApi.members(id, { page: 1, page_size: MEMBER_SIZE })
    if (route.params.id !== id) return
    members.value = data.items
    memberTotal.value = data.total
  } catch {
    members.value = []
  }
}

async function loadMembers(p) {
  memberPage.value = p
  const data = await clubApi.members(route.params.id, { page: p, page_size: MEMBER_SIZE })
  members.value = data.items
  memberTotal.value = data.total
}

function onApply() {
  if (!user.isLoggedIn) {
    user.openLogin()
    return
  }
  reason.value = ''
  applyOpen.value = true
}

async function sendApply() {
  sending.value = true
  try {
    await clubApi.apply(club.value.id, reason.value.trim())
    applyOpen.value = false
    toast.success('申请已提交', { description: '可以在「我的社团」里查看进度' })
    await load()
  } catch {
    /* 未在招新、重复申请等提示已由 http.js 弹出 */
  } finally {
    sending.value = false
  }
}

async function onLeave() {
  const ok = await confirm({
    title: '退出社团',
    message: `确定退出「${club.value.title}」吗？退出后需要重新申请才能再加入。`,
    confirmText: '退出',
    danger: true,
  })
  if (!ok) return
  try {
    await clubApi.leave(club.value.id)
    toast.success('已退出社团')
    await load()
  } catch {
    /* 已不是成员等提示已由 http.js 弹出 */
  }
}

function openEdit() {
  const c = club.value
  editForm.summary = c.summary ?? ''
  editForm.recruit_status = c.recruit_status === 'recruiting' ? 'recruiting' : 'closed'
  editForm.recruit_start = (c.recruit_start || '').slice(0, 10)
  editForm.recruit_end = (c.recruit_end || '').slice(0, 10)
  editForm.recruit_note = c.recruit_note ?? ''
  editOpen.value = true
}

async function saveEdit() {
  saving.value = true
  try {
    club.value = await clubApi.update(club.value.id, {
      summary: editForm.summary.trim(),
      recruit_status: editForm.recruit_status,
      recruit_start: editForm.recruit_start || null,
      recruit_end: editForm.recruit_end || null,
      recruit_note: editForm.recruit_note.trim(),
    })
    editOpen.value = false
    toast.success('招新信息已保存')
  } catch {
    /* 校验提示已弹出 */
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  meta.load().catch(() => {})
  load()
})
watch(() => route.params.id, (now, before) => {
  if (now !== before) load()
})
watch(
  () => user.profile?.id ?? null,
  (now, before) => {
    if (now !== before) load()
  },
)
</script>

<template>
  <div class="container">
    <PageHeader :title="club?.title || '社团详情'">
      <span v-if="club?.recruiting_now" class="inline-flex items-center gap-2">
        <SignalFlag />
        <Badge class="bg-buoy text-white">招新中</Badge>
      </span>
    </PageHeader>

    <div v-if="notFound" class="py-24 text-center">
      <p class="font-display text-2xl text-ocean">这个社团不存在</p>
      <Button class="mt-6" @click="router.push({ name: 'clubs' })">返回社团目录</Button>
    </div>

    <div v-else-if="!club" class="grid gap-8 lg:grid-cols-[1fr_280px]">
      <div class="space-y-4">
        <Skeleton class="h-8 w-2/3" />
        <Skeleton class="h-24" />
        <Skeleton class="h-40" />
      </div>
      <Skeleton class="h-48 rounded-xl" />
    </div>

    <div v-else class="grid items-start gap-8 lg:grid-cols-[1fr_280px]">
      <div>
        <p class="text-lg leading-relaxed text-ocean">{{ club.summary }}</p>
        <dl class="mt-6 grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
          <div>
            <dt class="text-muted-foreground">类型</dt>
            <dd class="mt-1 text-ocean">{{ typeName(club.club_type) }}</dd>
          </div>
          <div>
            <dt class="text-muted-foreground">校区</dt>
            <dd class="mt-1 text-ocean">{{ club.campus_area || '未填写' }}</dd>
          </div>
          <div>
            <dt class="text-muted-foreground">成立</dt>
            <dd class="mt-1 text-ocean">{{ club.founded_year ? `${club.founded_year} 年` : '未填写' }}</dd>
          </div>
          <div>
            <dt class="text-muted-foreground">会长</dt>
            <dd class="mt-1 text-ocean">{{ club.president?.nickname || '暂无' }}</dd>
          </div>
        </dl>

        <section class="mt-8 rounded-xl border bg-white p-5">
          <h2 class="font-display text-2xl text-ocean">招新</h2>
          <p v-if="club.recruiting_now" class="mt-2 text-sm text-kelp">正在招新<template v-if="dateText(club.recruit_start, club.recruit_end)">，{{ dateText(club.recruit_start, club.recruit_end) }}</template></p>
          <p v-else class="mt-2 text-sm text-muted-foreground">当前没有开放招新</p>
          <p v-if="club.recruit_note" class="mt-3 leading-relaxed text-ocean">{{ club.recruit_note }}</p>
        </section>

        <ClubActivities :club-id="club.id" :is-president="club.my_status === 'president'" />

        <section class="mt-8">
          <div class="mb-3 flex items-baseline justify-between">
            <h2 class="font-display text-2xl text-ocean">成员</h2>
            <span class="text-sm text-muted-foreground">{{ memberTotal }} 人</span>
          </div>
          <ul class="divide-y rounded-xl border bg-white">
            <li v-for="m in members" :key="m.user_id" class="flex items-center gap-3 px-4 py-3">
              <span class="grid size-9 shrink-0 place-items-center rounded-full bg-secondary font-medium text-ocean">{{ m.nickname.slice(0, 1) }}</span>
              <span class="min-w-0 flex-1 truncate text-ocean">{{ m.nickname }}</span>
              <Badge v-if="m.role === 'president'" class="bg-ocean text-white">{{ roleName(m.role) }}</Badge>
              <span v-else class="text-xs text-muted-foreground">{{ roleName(m.role) }}</span>
            </li>
            <li v-if="!members.length" class="px-4 py-8 text-center text-sm text-muted-foreground">还没有成员</li>
          </ul>
          <div v-if="memberTotal > MEMBER_SIZE" class="mt-3 flex justify-end gap-2">
            <Button variant="outline" size="sm" :disabled="memberPage <= 1" @click="loadMembers(memberPage - 1)">上一页</Button>
            <Button variant="outline" size="sm" :disabled="memberPage * MEMBER_SIZE >= memberTotal" @click="loadMembers(memberPage + 1)">下一页</Button>
          </div>
        </section>
      </div>

      <aside class="order-first rounded-xl border bg-white p-5 lg:sticky lg:top-24 lg:order-last">
        <p class="text-sm text-muted-foreground">成员人数</p>
        <p class="mt-1 text-3xl font-semibold text-ocean">{{ club.member_count }}</p>
        <Button v-if="action === 'apply'" class="mt-5 w-full" @click="onApply">申请入社</Button>
        <Button v-else-if="action === 'pending'" class="mt-5 w-full" disabled>申请审核中</Button>
        <Button v-else-if="action === 'member'" variant="outline" class="mt-5 w-full" @click="onLeave">退出社团</Button>
        <template v-else-if="action === 'president'">
          <Button variant="outline" class="mt-5 w-full" @click="openEdit">编辑招新信息</Button>
          <Button class="mt-2 w-full" @click="router.push({ name: 'club-applications', params: { id: club.id } })">
            审批申请<span v-if="club.pending_count">（{{ club.pending_count }}）</span>
          </Button>
        </template>
        <p v-else class="mt-5 text-sm leading-relaxed text-muted-foreground">会长还没有开放招新。开放后就可以在这里提交申请。</p>
        <p v-if="action === 'pending'" class="mt-3 text-xs leading-relaxed text-muted-foreground">会长处理之前不能重复提交。结果会显示在「我的社团」。</p>
      </aside>
    </div>

    <Dialog v-model:open="applyOpen">
      <DialogContent class="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>申请加入{{ club?.title }}</DialogTitle>
          <DialogDescription>用几句话说明你为什么想加入，会长会看到这段理由。</DialogDescription>
        </DialogHeader>
        <Textarea v-model="reason" maxlength="300" placeholder="例如：想跟着学拍照，周末可以参加外拍" class="min-h-28" />
        <DialogFooter>
          <Button variant="outline" @click="applyOpen = false">取消</Button>
          <Button :disabled="sending || !reason.trim()" @click="sendApply">
            <Loader2 v-if="sending" class="animate-spin" />提交申请
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <Dialog v-model:open="editOpen">
      <DialogContent class="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>编辑招新信息</DialogTitle>
          <DialogDescription>可以改简介、招新开关和说明。社团名称和会长不会在这里改变。</DialogDescription>
        </DialogHeader>
        <div class="grid gap-3">
          <div class="grid gap-1.5">
            <Label for="club-summary">简介</Label>
            <Textarea id="club-summary" v-model="editForm.summary" maxlength="300" class="min-h-24" />
          </div>
          <div class="grid gap-1.5">
            <Label>招新状态</Label>
            <Select v-model="editForm.recruit_status">
              <SelectTrigger class="w-full" aria-label="招新状态"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="recruiting">正在招新</SelectItem>
                <SelectItem value="closed">暂停招新</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div class="grid gap-1.5">
              <Label for="recruit-start">开始日期</Label>
              <Input id="recruit-start" v-model="editForm.recruit_start" type="date" class="h-10" />
            </div>
            <div class="grid gap-1.5">
              <Label for="recruit-end">结束日期</Label>
              <Input id="recruit-end" v-model="editForm.recruit_end" type="date" class="h-10" />
            </div>
          </div>
          <div class="grid gap-1.5">
            <Label for="recruit-note">招新说明</Label>
            <Textarea id="recruit-note" v-model="editForm.recruit_note" maxlength="300" placeholder="对应届同学说的话，可不填" />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" @click="editOpen = false">取消</Button>
          <Button :disabled="saving" @click="saveEdit"><Loader2 v-if="saving" class="animate-spin" />保存</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>
