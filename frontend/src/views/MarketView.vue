<!-- 二手市场：分类、校区、成色、排序筛选 + 物品网格 + 分页 -->
<script setup>
import { Plus, X } from '@lucide/vue'
import { AnimatePresence, motion } from 'motion-v'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { itemApi } from '@/api'
import ItemCard from '@/components/ItemCard.vue'
import SectionBanner from '@/components/SectionBanner.vue'
import { Button } from '@/components/ui/button'
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
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const meta = useMetaStore()
const user = useUserStore()

// 筛选条件：对应后端 GET /api/items 的查询参数；keyword 来自顶部搜索框（网址 ?keyword=）
// Select 组件不接受空字符串，所以「全部」用 'all' 表示
const filters = reactive({ category_id: 0, campus_area: 'all', condition: 'all', sort: 'latest' })
const keyword = computed(() => route.query.keyword ?? '')
const page = ref(1)
const PAGE_SIZE = 20

const items = ref([])
const total = ref(0)
const loading = ref(true)

const conditions = computed(() => Object.entries(meta.enums?.item_condition ?? {}))
const SORTS = [
  ['latest', '最新发布'],
  ['price_asc', '价格从低到高'],
  ['price_desc', '价格从高到低'],
  ['popular', '最多浏览'],
]

async function load() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: PAGE_SIZE, sort: filters.sort }
    if (keyword.value) params.keyword = keyword.value
    if (filters.category_id) params.category_id = filters.category_id
    if (filters.campus_area !== 'all') params.campus_area = filters.campus_area
    if (filters.condition !== 'all') params.condition = filters.condition
    const data = await itemApi.list(params)
    items.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

// 任何筛选条件变了，都回到第一页重新查
function reload() {
  page.value = 1
  load()
}
watch(() => ({ ...filters }), reload)
watch(keyword, reload)

function onPage(p) {
  page.value = p
  load()
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function onPublish() {
  if (user.isLoggedIn) router.push({ name: 'publish' })
  else user.openLogin()
}

onMounted(() => {
  meta.load().catch(() => {})
  load()
})
</script>

<template>
  <div class="container">
    <SectionBanner eyebrow="二手航道" title="二手市场">
      <template #description>
        <template v-if="keyword">「{{ keyword }}」的搜索结果，</template>共 {{ total }} 件在售，支持黄埔与琶洲校区筛选
        <button v-if="keyword" type="button" class="ml-1.5 inline-flex items-center text-signal hover:underline" @click="router.replace({ name: 'market' })">
          <X class="size-3.5" />清除搜索
        </button>
      </template>
      <template #actions>
        <Button @click="onPublish"><Plus />发布闲置</Button>
      </template>
    </SectionBanner>

    <!-- 筛选工具栏：分类胶囊 + 校区 / 成色 / 排序 -->
    <div class="mt-5 flex flex-wrap items-center justify-between gap-3 rounded-2xl border bg-white p-3.5">
      <div class="flex flex-wrap gap-1.5" role="radiogroup" aria-label="分类">
        <button
          v-for="c in [{ id: 0, name: '全部' }, ...meta.itemCategories]"
          :key="c.id"
          type="button"
          role="radio"
          :aria-checked="filters.category_id === c.id"
          class="rounded-full px-3.5 py-1.5 text-sm transition-colors"
          :class="filters.category_id === c.id ? 'bg-ocean text-white' : 'text-muted-foreground hover:bg-secondary hover:text-ocean'"
          @click="filters.category_id = c.id"
        >
          {{ c.name }}
        </button>
      </div>
      <div class="flex gap-2">
        <Select v-model="filters.campus_area">
          <SelectTrigger class="w-32" aria-label="校区"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部校区</SelectItem>
            <SelectItem v-for="c in meta.enums?.campus_area ?? []" :key="c" :value="c">{{ c }}</SelectItem>
          </SelectContent>
        </Select>
        <Select v-model="filters.condition">
          <SelectTrigger class="w-32" aria-label="成色"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部成色</SelectItem>
            <SelectItem v-for="[v, t] in conditions" :key="v" :value="v">{{ t }}</SelectItem>
          </SelectContent>
        </Select>
        <Select v-model="filters.sort">
          <SelectTrigger class="w-36" aria-label="排序"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem v-for="[v, t] in SORTS" :key="v" :value="v">{{ t }}</SelectItem>
          </SelectContent>
        </Select>
      </div>
    </div>

    <div class="mt-6 min-h-80">
      <div v-if="loading && !items.length" class="grid grid-cols-2 gap-x-4 gap-y-6 sm:grid-cols-3 lg:grid-cols-5">
        <div v-for="i in 10" :key="i"><Skeleton class="aspect-square rounded-lg" /><Skeleton class="mt-2 h-4 w-3/4" /></div>
      </div>
      <!-- 筛选变化时：layout 让留下的卡片平滑移动到新位置，新卡片淡入、离开的淡出 -->
      <div
        v-else-if="items.length"
        class="grid grid-cols-2 gap-x-4 gap-y-6 transition-opacity sm:grid-cols-3 lg:grid-cols-5"
        :class="loading ? 'opacity-50' : ''"
      >
        <AnimatePresence :initial="false">
          <motion.div
            v-for="it in items"
            :key="it.id"
            layout
            :initial="{ opacity: 0, scale: 0.96 }"
            :animate="{ opacity: 1, scale: 1 }"
            :exit="{ opacity: 0, scale: 0.96 }"
            :transition="{ duration: 0.25 }"
          >
            <ItemCard :item="it" />
          </motion.div>
        </AnimatePresence>
      </div>
      <div v-else class="py-20 text-center">
        <p class="font-medium text-ocean">没有找到符合条件的物品</p>
        <p class="mt-1 text-sm text-muted-foreground">换个关键词或者放宽筛选条件试试</p>
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
