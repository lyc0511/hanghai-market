<script setup>
import { computed, onMounted, reactive, ref } from 'vue'

import { itemApi } from '@/api'
import ItemCard from '@/components/ItemCard.vue'
import { useMetaStore } from '@/stores/meta'

const meta = useMetaStore()
const PAGE_SIZE = 20

// 筛选条件：对应后端 GET /api/items 的查询参数
const filters = reactive({ keyword: '', category_id: 0, campus_area: '', sort: 'latest' })
const keywordInput = ref('')

const items = ref([])
const page = ref(0)
const total = ref(0)
const loading = ref(false)
const finished = ref(false)
const refreshing = ref(false)
const error = ref(false)

const campusOptions = computed(() => [
  { text: '全部校区', value: '' },
  ...(meta.enums?.campus_area ?? []).map((c) => ({ text: c, value: c })),
])
const sortOptions = [
  { text: '最新发布', value: 'latest' },
  { text: '价格从低到高', value: 'price_asc' },
  { text: '价格从高到低', value: 'price_desc' },
  { text: '最多浏览', value: 'popular' },
]

function buildParams() {
  const p = { page: page.value + 1, page_size: PAGE_SIZE, sort: filters.sort }
  if (filters.keyword) p.keyword = filters.keyword
  if (filters.category_id) p.category_id = filters.category_id
  if (filters.campus_area) p.campus_area = filters.campus_area
  return p
}

// van-list 滚动到底部时自动调用，加载下一页
async function loadMore() {
  try {
    const data = await itemApi.list(buildParams())
    if (refreshing.value) {
      items.value = []
      refreshing.value = false
    }
    items.value.push(...data.items)
    page.value = data.page
    total.value = data.total
    finished.value = items.value.length >= data.total
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}

// 条件变化时从第一页重新加载
function reload() {
  items.value = []
  page.value = 0
  finished.value = false
  error.value = false
  loading.value = true
  loadMore()
}

function onSearch() {
  filters.keyword = keywordInput.value.trim()
  reload()
}

function onRefresh() {
  page.value = 0
  finished.value = false
  loadMore()
}

onMounted(() => meta.load().catch(() => {}))
</script>

<template>
  <div class="home">
    <header class="top">
      <div class="brand">
        <span class="name">航海集市</span>
        <span class="sub">校内二手 · 闲置流转</span>
      </div>
      <van-search
        v-model="keywordInput"
        placeholder="搜索教材、数码、生活用品"
        shape="round"
        background="transparent"
        class="search"
        @search="onSearch"
        @clear="onSearch"
      />
    </header>

    <div class="sticky">
      <van-tabs
        v-model:active="filters.category_id"
        shrink
        line-width="18"
        :ellipsis="false"
        @change="reload"
      >
        <van-tab title="全部" :name="0" />
        <van-tab v-for="c in meta.itemCategories" :key="c.id" :title="c.name" :name="c.id" />
      </van-tabs>
      <van-dropdown-menu class="filters">
        <van-dropdown-item v-model="filters.campus_area" :options="campusOptions" @change="reload" />
        <van-dropdown-item v-model="filters.sort" :options="sortOptions" @change="reload" />
      </van-dropdown-menu>
    </div>

    <van-pull-refresh v-model="refreshing" @refresh="onRefresh">
      <van-list
        v-model:loading="loading"
        v-model:error="error"
        :finished="finished"
        :finished-text="items.length ? '没有更多了' : ''"
        error-text="加载失败，点击重试"
        :offset="200"
        @load="loadMore"
      >
        <p v-if="filters.keyword && !loading" class="result-hint">
          「{{ filters.keyword }}」共找到 {{ total }} 件
        </p>
        <div class="grid">
          <ItemCard v-for="it in items" :key="it.id" :item="it" />
        </div>
        <van-empty v-if="finished && !items.length" image="search" description="没有找到相关物品" />
      </van-list>
    </van-pull-refresh>
  </div>
</template>

<style scoped>
.top {
  background: var(--brand);
  color: #fff;
  padding: 18px var(--page-x) 6px;
}
.brand {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 0 4px;
}
.name {
  font-size: 20px;
  font-weight: 600;
  letter-spacing: 1px;
}
.sub {
  font-size: 12px;
  opacity: 0.8;
}
.search {
  padding: 10px 0 8px;
  --van-search-content-background: #fff;
}

.sticky {
  position: sticky;
  top: 0;
  z-index: 10;
  background: var(--bg-card);
  box-shadow: 0 1px 0 var(--border);
}
.filters {
  --van-dropdown-menu-height: 40px;
  --van-dropdown-menu-shadow: none;
  --van-dropdown-menu-title-font-size: 13px;
  border-top: 1px solid var(--border);
}

.result-hint {
  margin: 12px var(--page-x) 0;
  color: var(--text-2);
  font-size: 12px;
}
.grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--gap);
  padding: var(--gap) var(--page-x);
}
</style>
