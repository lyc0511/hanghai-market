<!-- 活动航班表：即将开始 / 已结束，按校区和关键词筛选 -->
<script setup>
import { Search } from '@lucide/vue'
import { onMounted, reactive, ref, watch } from 'vue'

import { activityApi } from '@/api'
import ActivityTable from '@/components/ActivityTable.vue'
import { Input } from '@/components/ui/input'
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationNext,
  PaginationPrevious,
} from '@/components/ui/pagination'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useMetaStore } from '@/stores/meta'

const meta = useMetaStore()
const PAGE_SIZE = 20

// Select 组件不接受空字符串，「全部校区」用 'all' 表示
const filters = reactive({ when: 'upcoming', campus_area: 'all', keyword: '' })
const keywordInput = ref('')
const page = ref(1)
const items = ref([])
const total = ref(0)
const loading = ref(true)

async function load() {
  loading.value = true
  try {
    const params = { when: filters.when, page: page.value, page_size: PAGE_SIZE }
    if (filters.campus_area !== 'all') params.campus_area = filters.campus_area
    if (filters.keyword) params.keyword = filters.keyword
    const data = await activityApi.list(params)
    items.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function reload() {
  page.value = 1
  load()
}
watch(() => ({ ...filters }), reload)

function onPage(p) {
  page.value = p
  load()
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

onMounted(() => {
  meta.load().catch(() => {})
  load()
})
</script>

<template>
  <div class="container">
    <h1 class="font-display text-4xl text-ocean">活动航班表</h1>
    <p class="mt-1 text-sm text-muted-foreground">全校同学都可以报名社团活动，名额先到先得。</p>

    <div class="mt-6 flex flex-wrap items-center justify-between gap-3 border-y py-3">
      <Tabs v-model="filters.when">
        <TabsList>
          <TabsTrigger value="upcoming">即将开始</TabsTrigger>
          <TabsTrigger value="ended">已结束</TabsTrigger>
        </TabsList>
      </Tabs>
      <div class="flex gap-2">
        <form class="relative" role="search" @submit.prevent="filters.keyword = keywordInput.trim()">
          <Search class="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input v-model="keywordInput" placeholder="搜活动名、地点、社团" class="w-52 pl-9" aria-label="搜索活动" />
        </form>
        <Select v-model="filters.campus_area">
          <SelectTrigger class="w-32" aria-label="校区"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部校区</SelectItem>
            <SelectItem v-for="c in meta.enums?.campus_area ?? []" :key="c" :value="c">{{ c }}</SelectItem>
          </SelectContent>
        </Select>
      </div>
    </div>

    <div class="mt-4 min-h-80">
      <div v-if="loading && !items.length" class="space-y-3 pt-2"><Skeleton v-for="i in 5" :key="i" class="h-14" /></div>
      <ActivityTable
        v-else
        :items="items"
        :class="loading ? 'opacity-50 transition-opacity' : ''"
        :empty-text="filters.when === 'upcoming' ? '最近没有即将开始的活动' : '还没有已结束的活动'"
      />
    </div>

    <Pagination
      v-if="total > PAGE_SIZE"
      v-slot="{ page: current }"
      :page="page"
      :total="total"
      :items-per-page="PAGE_SIZE"
      :sibling-count="1"
      show-edges
      class="mt-10"
      @update:page="onPage"
    >
      <PaginationContent v-slot="{ items: pages }">
        <PaginationPrevious />
        <template v-for="(p, i) in pages" :key="i">
          <PaginationItem v-if="p.type === 'page'" :value="p.value" :is-active="p.value === current">{{ p.value }}</PaginationItem>
          <PaginationEllipsis v-else :index="i" />
        </template>
        <PaginationNext />
      </PaginationContent>
    </Pagination>
  </div>
</template>
