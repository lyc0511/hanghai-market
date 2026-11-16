<!-- 我的投稿：按状态筛选，能看到审核结果和未通过原因，可以修改（未上墙时）或撤回 -->
<script setup>
import { Images, Loader2, PenLine } from '@lucide/vue'
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'

import { postApi } from '@/api'
import PageHeader from '@/components/PageHeader.vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { confirm } from '@/composables/confirm'
import { formatDateTime } from '@/lib/time'
import { POST_STATUS, tagClass } from '@/lib/wall'

const router = useRouter()

const TABS = [
  ['all', '全部'],
  ['pending', '审核中'],
  ['online', '已上墙'],
  ['rejected', '未通过'],
]

const status = ref('all')
const posts = ref([])
const page = ref(0)
const total = ref(0)
const loading = ref(false)
const busyId = ref(null)

async function loadMore() {
  loading.value = true
  try {
    const params = { page: page.value + 1, page_size: 20 }
    if (status.value !== 'all') params.status = status.value
    const data = await postApi.mine(params)
    posts.value.push(...data.items)
    page.value = data.page
    total.value = data.total
  } catch {
    /* 提示已由 http.js 弹出 */
  } finally {
    loading.value = false
  }
}

function reload() {
  posts.value = []
  page.value = 0
  loadMore()
}

async function withdraw(p) {
  const ok = await confirm({
    title: '撤回这条投稿',
    message: p.status === 'online' ? '撤回后大家都看不到它了，也不能恢复。' : '撤回后不会再进入审核，也不能恢复。',
    confirmText: '撤回',
    danger: true,
  })
  if (!ok) return
  busyId.value = p.id
  try {
    await postApi.withdraw(p.id)
    toast.success('已撤回')
    reload()
  } catch {
    /* 提示已由 http.js 弹出 */
  } finally {
    busyId.value = null
  }
}

onMounted(loadMore)
</script>

<template>
  <div class="container narrow">
    <PageHeader title="我的投稿">
      <Button @click="router.push({ name: 'wall-new' })"><PenLine />投稿</Button>
    </PageHeader>

    <Tabs v-model="status" @update:model-value="reload">
      <TabsList>
        <TabsTrigger v-for="[v, t] in TABS" :key="v" :value="v">{{ t }}</TabsTrigger>
      </TabsList>
    </Tabs>

    <ul class="mt-4 space-y-3">
      <li v-for="p in posts" :key="p.id" class="rounded-xl border bg-white p-4">
        <div class="flex items-center gap-2 text-xs">
          <span v-if="p.tag" class="rounded-full px-2 py-0.5 font-medium" :class="tagClass(p.tag.slug)">{{ p.tag.name }}</span>
          <span class="text-muted-foreground">{{ formatDateTime(p.created_at) }} 投稿</span>
          <Badge class="ml-auto shrink-0" :class="POST_STATUS[p.status]?.[1]">{{ POST_STATUS[p.status]?.[0] ?? p.status }}</Badge>
        </div>
        <router-link :to="{ name: 'wall-post', params: { id: p.id } }" class="mt-2 block">
          <p class="line-clamp-3 whitespace-pre-line break-words text-[15px] leading-relaxed text-foreground">{{ p.body }}</p>
        </router-link>
        <p v-if="p.images.length" class="mt-1.5 inline-flex items-center gap-1 text-xs text-muted-foreground">
          <Images class="size-3.5" />{{ p.images.length }} 张图片
        </p>
        <p v-if="p.status === 'rejected' && p.reject_reason" class="mt-2 rounded-md bg-destructive/10 px-2.5 py-1.5 text-sm text-destructive">
          未通过原因：{{ p.reject_reason }}
        </p>
        <div class="mt-3 flex justify-end gap-2">
          <Button
            v-if="['pending', 'rejected'].includes(p.status)"
            size="sm"
            :variant="p.status === 'rejected' ? 'default' : 'outline'"
            @click="router.push({ name: 'wall-edit', params: { id: p.id } })"
          >
            {{ p.status === 'rejected' ? '修改后重投' : '修改' }}
          </Button>
          <Button size="sm" variant="outline" :disabled="busyId === p.id" @click="withdraw(p)">撤回</Button>
        </div>
      </li>
    </ul>

    <div v-if="loading && !posts.length" class="space-y-3">
      <div v-for="i in 3" :key="i" class="rounded-xl border bg-white p-4"><Skeleton class="h-4 w-1/3" /><Skeleton class="mt-3 h-4 w-full" /></div>
    </div>
    <div v-else-if="!posts.length" class="py-16 text-center">
      <p class="font-medium text-ocean">这里还没有投稿</p>
      <Button class="mt-4" @click="router.push({ name: 'wall-new' })">去投一条</Button>
    </div>
    <div v-else-if="posts.length < total" class="mt-6 text-center">
      <Button variant="outline" :disabled="loading" @click="loadMore"><Loader2 v-if="loading" class="animate-spin" />加载更多</Button>
    </div>
  </div>
</template>
