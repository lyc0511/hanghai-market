<!-- 我的举报：看处理进度和管理员的处理说明 -->
<script setup>
import { Flag } from '@lucide/vue'
import { onMounted, ref } from 'vue'

import { reportApi } from '@/api'
import PageHeader from '@/components/PageHeader.vue'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { formatDateTime } from '@/lib/time'

const TYPE_LABELS = { item: '物品', club: '社团', activity: '活动', post: '帖子', comment: '评论' }
const REASON_LABELS = { fraud: '疑似诈骗', prohibited: '违禁物品', false_info: '虚假信息', spam: '广告刷屏', abuse: '辱骂骚扰', privacy: '泄露隐私', other: '其他' }
const STATUS = {
  pending: { label: '处理中', cls: 'bg-buoy/10 text-buoy' },
  resolved: { label: '举报属实', cls: 'bg-kelp/10 text-kelp' },
  dismissed: { label: '未成立', cls: 'bg-muted text-muted-foreground' },
}

const items = ref([])
const loading = ref(true)

onMounted(async () => {
  try {
    items.value = (await reportApi.mine({ page_size: 50 })).items
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="container narrow">
    <PageHeader title="我的举报" />
    <p class="-mt-2 mb-5 text-sm text-muted-foreground">举报人信息不会透露给被举报的同学。处理结果也会通过消息通知告诉你。</p>

    <div v-if="loading" class="space-y-3"><Skeleton v-for="i in 3" :key="i" class="h-24" /></div>

    <div v-else-if="!items.length" class="rounded-xl border border-dashed py-16 text-center text-muted-foreground">
      <Flag class="mx-auto mb-3 size-8 opacity-40" />
      还没有举报记录。看到违规内容时，可以在详情页右上角点「举报」。
    </div>

    <ul v-else class="space-y-3">
      <li v-for="r in items" :key="r.id" class="rounded-xl border bg-white p-4">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <div class="flex items-center gap-2 text-xs text-muted-foreground">
              <Badge variant="outline">{{ TYPE_LABELS[r.target.type] }}</Badge>
              {{ formatDateTime(r.created_at) }}
            </div>
            <router-link
              v-if="r.target.status === 'online'"
              :to="r.target.link"
              class="mt-1.5 block truncate font-medium text-ocean hover:underline"
            >{{ r.target.title }}</router-link>
            <div v-else class="mt-1.5 truncate font-medium text-muted-foreground">{{ r.target.title }}（已下架）</div>
          </div>
          <span class="shrink-0 rounded-full px-2.5 py-1 text-xs font-medium" :class="STATUS[r.status].cls">{{ STATUS[r.status].label }}</span>
        </div>
        <p class="mt-2 text-sm text-muted-foreground">
          <span class="text-foreground">{{ REASON_LABELS[r.reason] }}</span>
          <template v-if="r.description">：{{ r.description }}</template>
        </p>
        <p v-if="r.handle_note" class="mt-3 rounded-lg bg-sail px-3 py-2 text-sm">
          <span class="font-medium text-ocean">管理员回复：</span>{{ r.handle_note }}
        </p>
      </li>
    </ul>
  </div>
</template>
