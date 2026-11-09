<!-- 会长审批入社申请。只有 clubs.president_id 等于当前用户时，后端才返回名单 -->
<script setup>
import { Loader2 } from '@lucide/vue'
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'

import { clubApi } from '@/api'
import PageHeader from '@/components/PageHeader.vue'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Textarea } from '@/components/ui/textarea'
import { confirm } from '@/composables/confirm'
import { timeAgo } from '@/lib/time'

const route = useRoute()
const router = useRouter()

const club = ref(null)
const apps = ref([])
const total = ref(0)
const loading = ref(true)
const notFound = ref(false)
const status = ref('pending')
const acting = ref(0)
const rejectOpen = ref(false)
const rejectNote = ref('')
const rejectTarget = ref(null)

const FILTERS = [
  ['pending', '待审核'],
  ['approved', '已通过'],
  ['rejected', '未通过'],
]

async function load() {
  const id = route.params.id
  loading.value = true
  try {
    const detail = await clubApi.detail(id)
    if (route.params.id !== id) return
    club.value = detail
    if (detail.my_status !== 'president') {
      toast.error('只有会长可以查看入社申请')
      router.replace({ name: 'club', params: { id } })
      return
    }
    const data = await clubApi.applications(id, { status: status.value, page: 1, page_size: 50 })
    apps.value = data.items
    total.value = data.total
    notFound.value = false
  } catch {
    notFound.value = true
  } finally {
    loading.value = false
  }
}

async function approve(app) {
  const ok = await confirm({
    title: '通过申请',
    message: `通过后，${app.nickname} 会成为「${club.value.title}」的成员，成员人数加 1。`,
    confirmText: '通过',
  })
  if (!ok) return
  acting.value = app.id
  try {
    await clubApi.approve(app.id)
    toast.success(`已通过 ${app.nickname} 的申请`)
    await load()
  } catch {
    /* 已经处理过等提示由 http.js 弹出 */
  } finally {
    acting.value = 0
  }
}

function openReject(app) {
  rejectTarget.value = app
  rejectNote.value = ''
  rejectOpen.value = true
}

async function sendReject() {
  const app = rejectTarget.value
  if (!app) return
  acting.value = app.id
  try {
    await clubApi.reject(app.id, rejectNote.value.trim())
    rejectOpen.value = false
    toast.success(`已拒绝 ${app.nickname} 的申请`)
    await load()
  } catch {
    /* 提示已弹出 */
  } finally {
    acting.value = 0
  }
}

onMounted(load)
watch(() => route.params.id, (now, before) => {
  if (now !== before) load()
})
watch(status, () => load())
</script>

<template>
  <div class="container narrow">
    <PageHeader :title="club ? `${club.title}的入社申请` : '入社申请'" />

    <div v-if="notFound" class="py-24 text-center">
      <p class="font-display text-2xl text-ocean">这个社团不存在</p>
    </div>

    <template v-else>
      <div class="flex gap-1.5" role="radiogroup" aria-label="申请状态">
        <button
          v-for="[value, label] in FILTERS"
          :key="value"
          type="button"
          class="rounded-full px-3.5 py-1.5 text-sm transition-colors"
          :class="status === value ? 'bg-ocean text-white' : 'text-muted-foreground hover:bg-secondary hover:text-ocean'"
          @click="status = value"
        >
          {{ label }}
        </button>
      </div>

      <p class="mt-4 text-sm text-muted-foreground">{{ loading ? '加载中' : `共 ${total} 条` }}</p>

      <ul v-if="apps.length" class="mt-3 divide-y rounded-xl border bg-white">
        <li v-for="app in apps" :key="app.id" class="px-4 py-4">
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <p class="font-medium text-ocean">{{ app.nickname }}</p>
              <p class="mt-1 text-sm leading-relaxed text-ocean">{{ app.reason }}</p>
              <p class="mt-1 text-xs text-muted-foreground">{{ timeAgo(app.created_at) }}</p>
            </div>
          </div>
          <div v-if="status === 'pending'" class="mt-3 flex gap-2">
            <Button size="sm" :disabled="acting === app.id" @click="approve(app)">
              <Loader2 v-if="acting === app.id" class="animate-spin" />通过
            </Button>
            <Button size="sm" variant="outline" :disabled="acting === app.id" @click="openReject(app)">拒绝</Button>
          </div>
        </li>
      </ul>
      <p v-else-if="!loading" class="mt-10 text-center text-sm text-muted-foreground">
        {{ status === 'pending' ? '没有待审核的申请' : '这一栏是空的' }}
      </p>
    </template>

    <Dialog v-model:open="rejectOpen">
      <DialogContent class="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>拒绝{{ rejectTarget?.nickname }}的申请</DialogTitle>
          <DialogDescription>可以写一句原因，对方会在通知里看到。不写也会告诉对方可以再次申请。</DialogDescription>
        </DialogHeader>
        <Textarea v-model="rejectNote" maxlength="200" placeholder="例如：这学期名额已满，欢迎下学期再来" class="min-h-24" />
        <DialogFooter>
          <Button variant="outline" @click="rejectOpen = false">取消</Button>
          <Button variant="destructive" :disabled="acting === rejectTarget?.id" @click="sendReject">拒绝申请</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>
