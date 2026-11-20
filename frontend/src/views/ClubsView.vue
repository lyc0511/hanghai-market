<!-- 社团目录：按类型、校区、是否招新、关键词筛选。正在招新的名字前挂橙色信号旗 -->
<script setup>
import { Search } from '@lucide/vue'
import { AnimatePresence, motion } from 'motion-v'
import { computed, onMounted, reactive, ref, watch } from 'vue'

import { clubApi } from '@/api'
import SectionBanner from '@/components/SectionBanner.vue'
import SignalFlag from '@/components/SignalFlag.vue'
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
import { useMetaStore } from '@/stores/meta'

const meta = useMetaStore()

const filters = reactive({ club_type: 'all', campus_area: 'all', recruiting: 'all' })
const keyword = ref('')
const page = ref(1)
const PAGE_SIZE = 12

const clubs = ref([])
const total = ref(0)
const loading = ref(true)
let seq = 0
let keywordTimer = 0

const typeOptions = computed(() => Object.entries(meta.enums?.club_type ?? {}))

function typeName(code) {
  return meta.enums?.club_type?.[code] ?? ''
}

async function load() {
  const n = ++seq
  loading.value = true
  try {
    const params = { page: page.value, page_size: PAGE_SIZE }
    const q = keyword.value.trim()
    if (q) params.keyword = q
    if (filters.club_type !== 'all') params.club_type = filters.club_type
    if (filters.campus_area !== 'all') params.campus_area = filters.campus_area
    if (filters.recruiting === 'yes') params.recruiting = true
    if (filters.recruiting === 'no') params.recruiting = false
    const data = await clubApi.list(params)
    if (n !== seq) return
    clubs.value = data.items
    total.value = data.total
  } finally {
    if (n === seq) loading.value = false
  }
}

function reload() {
  page.value = 1
  load()
}

watch(() => ({ ...filters }), reload)
watch(keyword, () => {
  clearTimeout(keywordTimer)
  keywordTimer = setTimeout(reload, 300)
})

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
    <SectionBanner
      eyebrow="社团码头"
      title="社团目录"
      :description="`共 ${total} 个社团，名字前挂有橙色信号旗的正在招新`"
    />

    <div class="mt-5 flex flex-wrap items-center justify-between gap-3 rounded-2xl border bg-white p-3.5">
      <div class="flex flex-wrap gap-1.5" role="radiogroup" aria-label="社团类型">
        <button
          v-for="c in [{ code: 'all', name: '全部' }, ...typeOptions.map(([code, name]) => ({ code, name }))]"
          :key="c.code"
          type="button"
          role="radio"
          :aria-checked="filters.club_type === c.code"
          class="rounded-full px-3.5 py-1.5 text-sm transition-colors"
          :class="filters.club_type === c.code ? 'bg-ocean text-white' : 'text-muted-foreground hover:bg-secondary hover:text-ocean'"
          @click="filters.club_type = c.code"
        >
          {{ c.name }}
        </button>
      </div>
      <div class="flex flex-wrap gap-2">
        <div class="relative">
          <Search class="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input v-model="keyword" placeholder="搜索社团" class="h-9 w-40 pl-9" aria-label="搜索社团" />
        </div>
        <Select v-model="filters.campus_area">
          <SelectTrigger class="w-32" aria-label="校区"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部校区</SelectItem>
            <SelectItem v-for="c in meta.enums?.campus_area ?? []" :key="c" :value="c">{{ c }}</SelectItem>
          </SelectContent>
        </Select>
        <Select v-model="filters.recruiting">
          <SelectTrigger class="w-32" aria-label="招新状态"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部状态</SelectItem>
            <SelectItem value="yes">正在招新</SelectItem>
            <SelectItem value="no">暂未招新</SelectItem>
          </SelectContent>
        </Select>
      </div>
    </div>

    <div class="mt-6 min-h-80">
      <div v-if="loading && !clubs.length" class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <Skeleton v-for="i in 6" :key="i" class="h-28 rounded-xl" />
      </div>
      <div v-else-if="clubs.length" class="grid gap-4 transition-opacity sm:grid-cols-2 xl:grid-cols-3" :class="loading ? 'opacity-50' : ''">
        <AnimatePresence :initial="false">
          <motion.div
            v-for="c in clubs"
            :key="c.id"
            layout
            :initial="{ opacity: 0, scale: 0.96 }"
            :animate="{ opacity: 1, scale: 1 }"
            :exit="{ opacity: 0, scale: 0.96 }"
            :transition="{ duration: 0.25 }"
          >
            <router-link :to="{ name: 'club', params: { id: c.id } }" class="flex h-full gap-4 rounded-xl border bg-white p-4 text-left transition-colors hover:border-signal">
              <span class="grid size-12 shrink-0 place-items-center rounded-lg bg-ocean font-display text-2xl text-white">{{ c.title.slice(0, 1) }}</span>
              <span class="min-w-0 flex-1">
                <span class="flex items-center gap-2 font-medium text-ocean">
                  <SignalFlag v-if="c.recruiting_now" />
                  <span v-if="c.recruiting_now" class="sr-only">正在招新</span>
                  <span class="truncate">{{ c.title }}</span>
                </span>
                <span class="mt-1 line-clamp-2 block text-sm leading-relaxed text-muted-foreground">{{ c.summary }}</span>
                <span class="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted-foreground">
                  <span>{{ typeName(c.club_type) }}</span>
                  <span v-if="c.campus_area">{{ c.campus_area }}</span>
                  <span>{{ c.member_count }} 名成员</span>
                </span>
              </span>
            </router-link>
          </motion.div>
        </AnimatePresence>
      </div>
      <div v-else class="py-20 text-center">
        <p class="font-medium text-ocean">没有找到符合条件的社团</p>
        <p class="mt-1 text-sm text-muted-foreground">换个关键词，或者把筛选放宽一些</p>
      </div>
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
