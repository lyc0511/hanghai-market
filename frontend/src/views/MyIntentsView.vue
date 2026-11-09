<!-- 我的意向：「我想要的」（我是买家）和「找我买的」（我是卖家），按角色和状态显示不同操作 -->
<script setup>
import { Copy, ImageOff, Loader2, MessageCircle } from '@lucide/vue'
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'

import { intentApi } from '@/api'
import PageHeader from '@/components/PageHeader.vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { confirm } from '@/composables/confirm'
import { timeAgo } from '@/lib/time'
import { useMetaStore } from '@/stores/meta'

const route = useRoute()
const router = useRouter()
const meta = useMetaStore()

const STATUS_CLASS = {
  pending: 'bg-buoy/10 text-[#B44A10]',
  accepted: 'bg-signal/10 text-signal',
  completed: 'bg-kelp/10 text-kelp',
  rejected: 'bg-secondary text-muted-foreground',
  cancelled: 'bg-secondary text-muted-foreground',
}

const role = ref(route.query.role === 'seller' ? 'seller' : 'buyer')
const list = ref([])
const page = ref(0)
const total = ref(0)
const loading = ref(false)
const busyId = ref(null)

async function loadMore() {
  loading.value = true
  try {
    const data = await intentApi.mine({ role: role.value, page: page.value + 1, page_size: 20 })
    list.value.push(...data.items)
    page.value = data.page
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function reload() {
  router.replace({ query: { role: role.value } })
  list.value = []
  page.value = 0
  loadMore()
}

// 每个操作：确认 → 调接口 → 用返回的最新数据替换列表里那一条
const ACTIONS = {
  accept: { api: intentApi.accept, title: '接受意向', message: '接受后，你们可以互相看到对方的微信号。', confirmText: '接受', done: '已接受，现在可以加对方微信了' },
  reject: { api: intentApi.reject, title: '拒绝意向', message: '确定不考虑这位同学的意向吗？', confirmText: '拒绝', danger: true, done: '已拒绝' },
  cancel: { api: intentApi.cancel, title: '取消意向', message: '确定取消这次意向吗？', confirmText: '取消意向', danger: true, done: '已取消' },
  complete: { api: intentApi.complete, title: '确认成交', message: '确认已经线下完成交易？物品会自动下架，其他同学的意向会自动关闭。', confirmText: '确认成交', done: '已成交' },
}

async function act(t, name) {
  const a = ACTIONS[name]
  if (!(await confirm(a))) return
  busyId.value = t.id
  try {
    const fresh = await a.api(t.id)
    const i = list.value.findIndex((x) => x.id === t.id)
    if (i >= 0) list.value[i] = fresh
    toast.success(a.done)
  } catch {
    /* 提示已由 http.js 弹出 */
  } finally {
    busyId.value = null
  }
}

async function copyWechat(text) {
  try {
    await navigator.clipboard.writeText(text)
    toast.success('微信号已复制')
  } catch {
    toast(`微信号：${text}`)
  }
}

onMounted(() => {
  meta.load().catch(() => {})
  loadMore()
})
</script>

<template>
  <div class="container narrow">
    <PageHeader title="我的意向" />

    <Tabs v-model="role" @update:model-value="reload">
      <TabsList>
        <TabsTrigger value="buyer">我想要的</TabsTrigger>
        <TabsTrigger value="seller">找我买的</TabsTrigger>
      </TabsList>
    </Tabs>

    <ul class="mt-4 space-y-3">
      <li v-for="t in list" :key="t.id" class="rounded-xl border bg-white p-4">
        <div class="flex items-center justify-between gap-2 text-sm">
          <span class="text-muted-foreground">
            {{ t.my_role === 'buyer' ? '卖家' : '买家' }}<span class="ml-1.5 font-medium text-ocean">{{ t.counterpart.nickname }}</span>
          </span>
          <Badge :class="STATUS_CLASS[t.status]">{{ meta.label('intent_status', t.status) }}</Badge>
        </div>

        <router-link :to="{ name: 'item', params: { id: t.item.id } }" class="mt-3 flex items-center gap-3 rounded-lg bg-sail p-2.5 hover:bg-secondary">
          <span class="relative size-12 shrink-0 overflow-hidden rounded-md bg-secondary">
            <img v-if="t.item.cover" :src="t.item.cover" alt="" class="relative z-10 size-full object-cover" @error="(e) => (e.target.style.display = 'none')" />
            <ImageOff class="absolute inset-0 m-auto size-4 text-ocean/25" aria-hidden="true" />
          </span>
          <span class="min-w-0 flex-1 truncate text-ocean">{{ t.item.title }}</span>
          <span class="font-semibold tabular-nums text-buoy">¥{{ t.item.price }}</span>
        </router-link>

        <p v-if="t.message" class="mt-3 flex gap-1.5 text-sm text-muted-foreground"><MessageCircle class="mt-0.5 size-4 shrink-0" />{{ t.message }}</p>

        <!-- 卖家接受后：显示对方微信号 -->
        <div v-if="t.counterpart_wechat" class="mt-3 flex items-center gap-2 rounded-lg border border-signal/30 bg-signal/5 px-3 py-2 text-sm">
          <span class="text-muted-foreground">对方微信号</span>
          <span class="font-semibold text-ocean">{{ t.counterpart_wechat }}</span>
          <Button size="xs" variant="outline" class="ml-auto" @click="copyWechat(t.counterpart_wechat)"><Copy />复制</Button>
        </div>

        <div class="mt-4 flex items-center gap-2">
          <span class="flex-1 text-xs text-muted-foreground">{{ timeAgo(t.updated_at) }}</span>
          <template v-if="t.my_role === 'seller' && t.status === 'pending'">
            <Button size="sm" variant="outline" :disabled="busyId === t.id" @click="act(t, 'reject')">拒绝</Button>
            <Button size="sm" :disabled="busyId === t.id" @click="act(t, 'accept')">接受</Button>
          </template>
          <Button v-else-if="t.my_role === 'seller' && t.status === 'accepted'" size="sm" :disabled="busyId === t.id" @click="act(t, 'complete')">
            已线下成交
          </Button>
          <Button
            v-if="t.my_role === 'buyer' && (t.status === 'pending' || t.status === 'accepted')"
            size="sm"
            variant="outline"
            :disabled="busyId === t.id"
            @click="act(t, 'cancel')"
          >
            取消意向
          </Button>
        </div>
      </li>
    </ul>

    <div v-if="loading && !list.length" class="space-y-3"><Skeleton v-for="i in 3" :key="i" class="h-36 rounded-xl" /></div>
    <div v-else-if="!list.length" class="py-16 text-center">
      <p class="font-medium text-ocean">{{ role === 'buyer' ? '还没有想要的物品' : '还没有人对你的物品发起意向' }}</p>
      <Button v-if="role === 'buyer'" class="mt-4" @click="router.push({ name: 'market' })">去二手市场看看</Button>
    </div>
    <div v-else-if="list.length < total" class="mt-6 text-center">
      <Button variant="outline" :disabled="loading" @click="loadMore"><Loader2 v-if="loading" class="animate-spin" />加载更多</Button>
    </div>
  </div>
</template>
