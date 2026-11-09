<!-- 我发布的：按状态筛选，每行带编辑 / 下架 / 重新上架 / 删除 -->
<script setup>
import { ImageOff, Loader2, Plus } from '@lucide/vue'
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'

import { itemApi } from '@/api'
import PageHeader from '@/components/PageHeader.vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { confirm } from '@/composables/confirm'
import { useMetaStore } from '@/stores/meta'

const router = useRouter()
const meta = useMetaStore()

const TABS = [
  ['all', '全部'],
  ['pending', '审核中'],
  ['online', '在售'],
  ['rejected', '未通过'],
  ['offline', '已下架'],
]
// 状态标签的颜色
const STATUS_CLASS = {
  pending: 'bg-buoy/10 text-[#B44A10]',
  online: 'bg-kelp/10 text-kelp',
  rejected: 'bg-destructive/10 text-destructive',
  offline: 'bg-secondary text-muted-foreground',
}

const status = ref('all')
const items = ref([])
const page = ref(0)
const total = ref(0)
const loading = ref(false)
const busyId = ref(null)

function statusText(it) {
  return it.sold ? '已售出' : meta.label('content_status', it.status)
}

async function loadMore() {
  loading.value = true
  try {
    const params = { page: page.value + 1, page_size: 20 }
    if (status.value !== 'all') params.status = status.value
    const data = await itemApi.mine(params)
    items.value.push(...data.items)
    page.value = data.page
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function reload() {
  items.value = []
  page.value = 0
  loadMore()
}

// 下架 / 重新上架 / 删除：确认 → 调接口 → 刷新列表
const ACTIONS = {
  offline: { api: itemApi.offline, title: '下架物品', message: '下架后其他同学将看不到这件物品，进行中的交易意向会自动关闭。', confirmText: '下架', done: '已下架' },
  relist: { api: itemApi.relist, title: '重新上架', message: '重新上架需要管理员再次审核。', confirmText: '提交审核', done: '已提交审核' },
  remove: { api: itemApi.remove, title: '删除物品', message: '删除后这件物品将不再显示，确定删除吗？', confirmText: '删除', danger: true, done: '已删除' },
}

async function act(it, name) {
  const a = ACTIONS[name]
  if (!(await confirm(a))) return
  busyId.value = it.id
  try {
    await a.api(it.id)
    toast.success(a.done)
    reload()
  } catch {
    /* 提示已由 http.js 弹出 */
  } finally {
    busyId.value = null
  }
}

onMounted(() => {
  meta.load().catch(() => {})
  loadMore()
})
</script>

<template>
  <div class="container narrow">
    <PageHeader title="我发布的">
      <Button @click="router.push({ name: 'publish' })"><Plus />发布闲置</Button>
    </PageHeader>

    <Tabs v-model="status" @update:model-value="reload">
      <TabsList>
        <TabsTrigger v-for="[v, t] in TABS" :key="v" :value="v">{{ t }}</TabsTrigger>
      </TabsList>
    </Tabs>

    <ul class="mt-4 divide-y border-y">
      <li v-for="it in items" :key="it.id" class="flex gap-4 py-4">
        <router-link :to="{ name: 'item', params: { id: it.id } }" class="relative size-20 shrink-0 overflow-hidden rounded-lg border bg-secondary">
          <img v-if="it.cover" :src="it.cover" alt="" class="relative z-10 size-full object-cover" @error="(e) => (e.target.style.display = 'none')" />
          <ImageOff class="absolute inset-0 m-auto size-5 text-ocean/25" aria-hidden="true" />
        </router-link>
        <div class="min-w-0 flex-1">
          <div class="flex items-start gap-2">
            <router-link :to="{ name: 'item', params: { id: it.id } }" class="min-w-0 flex-1 truncate font-medium text-ocean hover:text-signal">
              {{ it.title }}
            </router-link>
            <Badge class="shrink-0" :class="it.sold ? 'bg-kelp/10 text-kelp' : STATUS_CLASS[it.status]">{{ statusText(it) }}</Badge>
          </div>
          <div class="mt-1 flex items-baseline gap-3 text-sm">
            <span v-if="it.price === 0" class="font-semibold text-kelp">免费送</span>
            <span v-else class="font-semibold tabular-nums text-buoy">¥{{ it.price }}</span>
            <span class="text-muted-foreground">{{ it.view_count }} 次浏览</span>
          </div>
          <p v-if="it.status === 'rejected' && it.reject_reason" class="mt-2 rounded-md bg-destructive/10 px-2.5 py-1.5 text-sm text-destructive">
            未通过原因：{{ it.reject_reason }}
          </p>
          <div class="mt-3 flex justify-end gap-2">
            <template v-if="!it.sold">
              <Button size="sm" variant="outline" @click="router.push({ name: 'item-edit', params: { id: it.id } })">编辑</Button>
              <Button v-if="it.status !== 'offline'" size="sm" variant="outline" :disabled="busyId === it.id" @click="act(it, 'offline')">下架</Button>
              <Button v-else size="sm" :disabled="busyId === it.id" @click="act(it, 'relist')">重新上架</Button>
            </template>
            <Button v-else size="sm" variant="destructive" :disabled="busyId === it.id" @click="act(it, 'remove')">删除</Button>
          </div>
        </div>
      </li>
    </ul>

    <div v-if="loading && !items.length" class="space-y-4 py-4">
      <div v-for="i in 3" :key="i" class="flex gap-4"><Skeleton class="size-20 rounded-lg" /><div class="flex-1 space-y-2"><Skeleton class="h-5 w-2/3" /><Skeleton class="h-4 w-1/3" /></div></div>
    </div>
    <div v-else-if="!items.length" class="py-16 text-center">
      <p class="font-medium text-ocean">这里还没有物品</p>
      <Button class="mt-4" @click="router.push({ name: 'publish' })">发布第一件闲置</Button>
    </div>
    <div v-else-if="items.length < total" class="mt-6 text-center">
      <Button variant="outline" :disabled="loading" @click="loadMore"><Loader2 v-if="loading" class="animate-spin" />加载更多</Button>
    </div>
  </div>
</template>
