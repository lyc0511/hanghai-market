<!-- 我的社团：我管理的、我加入的，以及还在审核或被拒绝的申请 -->
<script setup>
import { ChevronRight } from '@lucide/vue'
import { computed, onMounted, ref } from 'vue'

import { clubApi } from '@/api'
import PageHeader from '@/components/PageHeader.vue'
import SignalFlag from '@/components/SignalFlag.vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { timeAgo } from '@/lib/time'

const clubs = ref([])
const applications = ref([])
const loading = ref(true)

const managing = computed(() => clubs.value.filter((c) => c.my_role === 'president'))
const joined = computed(() => clubs.value.filter((c) => c.my_role !== 'president'))

// 同一个社团只保留最新一条，已通过的已经出现在成员列表里，这里不再重复
const latestApps = computed(() => {
  const seen = new Set()
  const out = []
  for (const app of applications.value) {
    if (seen.has(app.club_id)) continue
    seen.add(app.club_id)
    if (app.status === 'pending' || app.status === 'rejected') out.push(app)
  }
  return out
})

async function load() {
  loading.value = true
  try {
    const [mine, apps] = await Promise.all([
      clubApi.mine({ page: 1, page_size: 50 }),
      clubApi.myApplications({ page: 1, page_size: 50 }),
    ])
    clubs.value = mine.items
    applications.value = apps.items
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="container narrow">
    <PageHeader title="我的社团" />

    <div v-if="loading" class="space-y-3">
      <Skeleton v-for="i in 3" :key="i" class="h-16 rounded-xl" />
    </div>

    <template v-else>
      <section v-if="latestApps.length">
        <h2 class="mb-2 text-sm text-muted-foreground">我的申请</h2>
        <ul class="divide-y rounded-xl border bg-white">
          <li v-for="app in latestApps" :key="app.id">
            <router-link :to="{ name: 'club', params: { id: app.club_id } }" class="flex items-center gap-3 px-4 py-3.5 hover:bg-sail">
              <span class="min-w-0 flex-1">
                <span class="block truncate font-medium text-ocean">{{ app.club_title }}</span>
                <span class="mt-0.5 block truncate text-xs text-muted-foreground">{{ app.reason }}</span>
              </span>
              <Badge v-if="app.status === 'pending'" variant="secondary">审核中</Badge>
              <Badge v-else variant="outline">未通过，可再申请</Badge>
              <span class="hidden text-xs text-muted-foreground sm:inline">{{ timeAgo(app.created_at) }}</span>
              <ChevronRight class="size-4 text-muted-foreground" />
            </router-link>
          </li>
        </ul>
      </section>

      <section class="mt-6">
        <h2 class="mb-2 text-sm text-muted-foreground">我管理的</h2>
        <ul v-if="managing.length" class="divide-y rounded-xl border bg-white">
          <li v-for="c in managing" :key="c.id" class="flex items-center gap-2 px-2 py-2">
            <router-link :to="{ name: 'club', params: { id: c.id } }" class="flex min-w-0 flex-1 items-center gap-3 rounded-lg px-2 py-1.5 hover:bg-sail">
              <SignalFlag v-if="c.recruiting_now" />
              <span class="min-w-0 flex-1 truncate font-medium text-ocean">{{ c.title }}</span>
              <span class="text-xs text-muted-foreground">{{ c.member_count }} 人</span>
            </router-link>
            <Button size="sm" variant="outline" as-child>
              <router-link :to="{ name: 'club-applications', params: { id: c.id } }">
                审批<span v-if="c.pending_count"> {{ c.pending_count }}</span>
              </router-link>
            </Button>
          </li>
        </ul>
        <p v-else class="rounded-xl border border-dashed px-4 py-6 text-sm text-muted-foreground">你还没有担任会长的社团</p>
      </section>

      <section class="mt-6">
        <h2 class="mb-2 text-sm text-muted-foreground">我加入的</h2>
        <ul v-if="joined.length" class="divide-y rounded-xl border bg-white">
          <li v-for="c in joined" :key="c.id">
            <router-link :to="{ name: 'club', params: { id: c.id } }" class="flex items-center gap-3 px-4 py-3.5 hover:bg-sail">
              <SignalFlag v-if="c.recruiting_now" />
              <span class="min-w-0 flex-1 truncate font-medium text-ocean">{{ c.title }}</span>
              <span class="text-xs text-muted-foreground">{{ c.member_count }} 人</span>
              <ChevronRight class="size-4 text-muted-foreground" />
            </router-link>
          </li>
        </ul>
        <div v-else class="rounded-xl border border-dashed px-4 py-6 text-sm text-muted-foreground">
          还没有加入社团。
          <router-link :to="{ name: 'clubs' }" class="text-signal hover:underline">去社团目录看看</router-link>
        </div>
      </section>
    </template>
  </div>
</template>
