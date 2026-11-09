<!--
  消息通知：全部 / 未读两个分页签，点一条 = 标为已读 + 跳到相关页面。
  右上角「全部已读」一键清空红点。
-->
<script setup>
import { Bell, CheckCheck } from '@lucide/vue'
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'

import { notificationApi } from '@/api'
import PageHeader from '@/components/PageHeader.vue'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { toneOf } from '@/lib/notification'
import { formatDateTime, timeAgo } from '@/lib/time'
import { useNotificationStore } from '@/stores/notifications'

const PAGE_SIZE = 20

const router = useRouter()
const notices = useNotificationStore()

const tab = ref('all')
const items = ref([])
const total = ref(0)
const page = ref(1)
const loading = ref(true)
const loadingMore = ref(false)

async function fetchPage(p) {
  return notificationApi.list({ unread_only: tab.value === 'unread', page: p, page_size: PAGE_SIZE })
}

async function load() {
  loading.value = true
  page.value = 1
  try {
    const res = await fetchPage(1)
    items.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

async function more() {
  loadingMore.value = true
  try {
    const res = await fetchPage(page.value + 1)
    page.value += 1
    items.value.push(...res.items)
    total.value = res.total
  } finally {
    loadingMore.value = false
  }
}

async function open(n) {
  if (!n.is_read) {
    try {
      notices.unread = (await notificationApi.read(n.id)).count
      n.is_read = true
    } catch {
      /* 标已读失败不影响跳转 */
    }
  }
  if (n.link) router.push(n.link)
}

async function readAll() {
  await notificationApi.readAll()
  notices.unread = 0
  items.value.forEach((n) => (n.is_read = true))
  if (tab.value === 'unread') {
    items.value = []
    total.value = 0
  }
  toast.success('已全部标为已读')
}

onMounted(load)
</script>

<template>
  <div class="container narrow">
    <PageHeader title="消息通知">
      <Button variant="outline" :disabled="!notices.unread" @click="readAll"><CheckCheck />全部已读</Button>
    </PageHeader>

    <div class="flex items-center justify-between gap-3">
      <Tabs v-model="tab" @update:model-value="load">
        <TabsList>
          <TabsTrigger value="all">全部</TabsTrigger>
          <TabsTrigger value="unread">未读</TabsTrigger>
        </TabsList>
      </Tabs>
      <span class="text-sm text-muted-foreground">{{ notices.unread ? `${notices.unread} 条未读` : '没有未读消息' }}</span>
    </div>

    <div class="mt-4">
      <div v-if="loading" class="space-y-3"><Skeleton v-for="i in 4" :key="i" class="h-20" /></div>

      <div v-else-if="!items.length" class="rounded-xl border border-dashed py-16 text-center text-muted-foreground">
        <Bell class="mx-auto mb-3 size-8 opacity-40" />
        {{ tab === 'unread' ? '没有未读消息，一切顺风' : '还没有收到任何通知' }}
      </div>

      <ul v-else class="divide-y overflow-hidden rounded-xl border bg-white">
        <li v-for="n in items" :key="n.id">
          <button
            type="button"
            class="flex w-full gap-3 px-4 py-4 text-left transition-colors hover:bg-sail"
            :class="n.is_read ? '' : 'bg-signal/[0.04]'"
            @click="open(n)"
          >
            <span class="mt-1.5 size-2.5 shrink-0 rounded-full" :class="n.is_read ? 'bg-fog' : toneOf(n.type)" />
            <span class="min-w-0 flex-1">
              <span class="flex items-baseline justify-between gap-3">
                <span class="truncate" :class="n.is_read ? 'text-foreground' : 'font-semibold text-ocean'">{{ n.title }}</span>
                <time class="shrink-0 text-xs text-muted-foreground" :title="formatDateTime(n.created_at)">{{ timeAgo(n.created_at) }}</time>
              </span>
              <span class="mt-1 line-clamp-2 block text-sm text-muted-foreground">{{ n.body }}</span>
            </span>
          </button>
        </li>
      </ul>

      <div v-if="!loading && items.length < total" class="mt-4 text-center">
        <Button variant="ghost" :disabled="loadingMore" @click="more">{{ loadingMore ? '加载中…' : '加载更多' }}</Button>
      </div>
    </div>
  </div>
</template>
