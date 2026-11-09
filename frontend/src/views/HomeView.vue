<!--
  首页：标题 + 搜索（主角）、到港公告牌（全站唯一的入场动画）、闲置货架、社团、活动航班表。
  三个板块各用不同的形式，不做成三张一样的卡片。
-->
<script setup>
import { ArrowRight, Search } from '@lucide/vue'
import { motion } from 'motion-v'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { activityApi, clubApi, itemApi } from '@/api'
import ActivityTable from '@/components/ActivityTable.vue'
import ItemCard from '@/components/ItemCard.vue'
import SignalFlag from '@/components/SignalFlag.vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { monthDay, weekTime } from '@/lib/activity'
import { timeAgo } from '@/lib/time'
import { useMetaStore } from '@/stores/meta'

const router = useRouter()
const meta = useMetaStore()

const keyword = ref('')
const shelf = ref([]) // 闲置货架
const recruitingClubs = ref([])
const upcoming = ref([]) // 活动航班表：即将开始的活动
const clubsLoaded = ref(false)
const activitiesLoaded = ref(false)
const loading = ref(true)

/**
 * 到港公告：把三个板块的最新动态排成一块牌子——
 * 新上架的闲置（货）、正在招新的社团（招）、即将开始的活动（航）。
 * 固定节奏：货、航、货、招、货；某类没有数据时用闲置补位，最多 5 行。
 */
const board = computed(() => {
  const items = shelf.value.map((it) => ({
    key: `i${it.id}`,
    tag: '货',
    tagClass: 'bg-white/15 text-white',
    to: { name: 'item', params: { id: it.id } },
    left: timeAgo(it.created_at),
    title: it.title,
    right: it.price === 0 ? '免费送' : `¥${it.price}`,
    rightClass: it.price === 0 ? 'text-[#7FD1B0]' : 'text-buoy',
  }))
  const acts = upcoming.value.slice(0, 1).map((a) => ({
    key: `a${a.id}`,
    tag: '航',
    tagClass: 'bg-signal text-white',
    to: { name: 'activity', params: { id: a.id } },
    left: monthDay(a.start_time),
    title: a.title,
    right: weekTime(a.start_time),
    rightClass: 'text-white/70',
  }))
  const clubs = recruitingClubs.value.slice(0, 1).map((c) => ({
    key: `c${c.id}`,
    tag: '招',
    tagClass: 'bg-buoy text-white',
    to: { name: 'club', params: { id: c.id } },
    left: '招新中',
    title: c.title,
    right: `${c.member_count} 人`,
    rightClass: 'text-white/70',
  }))
  const order = [items, acts, items, clubs, items]
  const rows = []
  for (const src of order) {
    const next = src.shift() ?? items.shift()
    if (next) rows.push(next)
  }
  return rows
})
const boardReady = computed(() => !loading.value && clubsLoaded.value && activitiesLoaded.value)

onMounted(async () => {
  meta.load().catch(() => {})
  activityApi
    .list({ when: 'upcoming', page_size: 5 })
    .then((data) => (upcoming.value = data.items))
    .catch(() => {})
    .finally(() => (activitiesLoaded.value = true))
  const clubsTask = clubApi
    .list({ recruiting: true, page: 1, page_size: 20 })
    .then((data) => {
      recruitingClubs.value = data.items
    })
    .catch(() => {})
    .finally(() => {
      clubsLoaded.value = true
    })
  try {
    const data = await itemApi.list({ page: 1, page_size: 10, sort: 'latest' })
    shelf.value = data.items.slice(0, 5)
  } finally {
    loading.value = false
  }
  await clubsTask
})

function onSearch() {
  const k = keyword.value.trim()
  router.push({ name: 'market', query: k ? { keyword: k } : {} })
}

// 公告牌逐行翻下：每行晚 0.12 秒，绕 X 轴从 -90° 翻到 0°，像机场航班牌
function flip(i) {
  return {
    initial: { rotateX: -90, opacity: 0 },
    animate: { rotateX: 0, opacity: 1 },
    transition: { delay: 0.25 + i * 0.12, duration: 0.45, ease: [0.22, 1, 0.36, 1] },
  }
}
</script>

<template>
  <div class="container">
    <!-- 第一屏：标题 + 搜索 / 到港公告牌 -->
    <section class="grid items-center gap-8 lg:grid-cols-[1.2fr_1fr] lg:gap-12">
      <div>
        <h1 class="font-display text-5xl leading-[1.1] text-ocean sm:text-6xl">
          今天港口<br />到了什么货？
        </h1>
        <p class="mt-4 max-w-md text-base leading-relaxed text-muted-foreground">
          二手闲置、社团招新、校园活动，在广航同学之间流转。看中了就发起意向，卖家同意后加微信面交。
        </p>
        <form class="mt-7 flex max-w-lg items-center gap-2 rounded-full border-2 border-ocean bg-white p-1.5 pl-5" role="search" @submit.prevent="onSearch">
          <Search class="size-5 shrink-0 text-muted-foreground" aria-hidden="true" />
          <Input
            v-model="keyword"
            placeholder="搜教材、自行车、耳机……"
            class="h-10 border-0 bg-transparent px-1 text-base shadow-none focus-visible:ring-0"
            aria-label="搜索闲置物品"
          />
          <Button type="submit" class="h-10 rounded-full px-6 text-base">搜索</Button>
        </form>
      </div>

      <!-- 到港公告牌 -->
      <aside class="rounded-xl bg-ocean p-5 text-white shadow-[0_20px_40px_-20px_rgba(14,42,71,0.6)]" aria-label="到港公告：最新闲置、招新和活动">
        <div class="mb-3 flex items-center justify-between text-sm text-white/60">
          <span class="font-display text-lg text-white">到港公告</span>
          <span class="flex items-center gap-1.5"><span class="size-1.5 animate-pulse rounded-full bg-buoy" />实时</span>
        </div>
        <ol class="divide-y divide-white/10" style="perspective: 600px">
          <template v-if="!boardReady">
            <li v-for="i in 5" :key="i" class="py-3"><div class="h-5 rounded bg-white/10" /></li>
          </template>
          <motion.li
            v-for="(row, i) in board"
            v-else
            :key="row.key"
            v-bind="flip(i)"
            class="origin-top"
          >
            <router-link :to="row.to" class="grid grid-cols-[1.5rem_4.5rem_1fr_auto] items-center gap-3 py-3 hover:text-buoy">
              <span class="grid size-6 place-items-center rounded text-xs font-semibold" :class="row.tagClass" aria-hidden="true">{{ row.tag }}</span>
              <span class="text-sm tabular-nums text-white/55">{{ row.left }}</span>
              <span class="truncate">{{ row.title }}</span>
              <span class="text-sm tabular-nums" :class="row.rightClass">{{ row.right }}</span>
            </router-link>
          </motion.li>
        </ol>
        <p class="mt-3 flex gap-4 border-t border-white/10 pt-3 text-xs text-white/50">
          <span>货 · 新到闲置</span><span>招 · 社团招新</span><span>航 · 近期活动</span>
        </p>
      </aside>
    </section>

    <!-- 闲置货架 -->
    <section class="mt-16">
      <div class="mb-5 flex items-end justify-between">
        <h2 class="font-display text-3xl text-ocean">闲置货架</h2>
        <router-link :to="{ name: 'market' }" class="flex items-center gap-1 text-sm text-signal hover:underline">
          去二手市场<ArrowRight class="size-4" />
        </router-link>
      </div>
      <div class="grid grid-cols-2 gap-x-4 gap-y-6 sm:grid-cols-3 lg:grid-cols-5">
        <template v-if="loading">
          <div v-for="i in 5" :key="i"><Skeleton class="aspect-square rounded-lg" /><Skeleton class="mt-2 h-4 w-3/4" /></div>
        </template>
        <ItemCard v-for="it in shelf" v-else :key="it.id" :item="it" />
      </div>
    </section>

    <!-- 社团 + 活动航班表 -->
    <section class="mt-16 grid gap-10 lg:grid-cols-[1fr_1.2fr]">
      <div>
        <div class="mb-5 flex items-end justify-between">
          <h2 class="font-display text-3xl text-ocean">社团</h2>
          <router-link :to="{ name: 'clubs' }" class="flex items-center gap-1 text-sm text-signal hover:underline">全部社团<ArrowRight class="size-4" /></router-link>
        </div>
        <div v-if="!clubsLoaded" class="flex flex-wrap gap-2">
          <Skeleton v-for="i in 6" :key="i" class="h-9 w-24 rounded-full" />
        </div>
        <div v-else-if="recruitingClubs.length" class="flex flex-wrap gap-2">
          <router-link
            v-for="c in recruitingClubs"
            :key="c.id"
            :to="{ name: 'club', params: { id: c.id } }"
            class="inline-flex items-center gap-2 rounded-full border bg-white px-3 py-1.5 text-sm text-ocean hover:border-buoy"
          >
            <SignalFlag />
            <span class="sr-only">正在招新</span>
            {{ c.title }}
          </router-link>
        </div>
        <p v-else class="rounded-xl border border-dashed bg-white/60 px-4 py-6 text-sm text-muted-foreground">现在没有社团在招新</p>
      </div>

      <div>
        <div class="mb-5 flex items-end justify-between">
          <h2 class="font-display text-3xl text-ocean">活动航班表</h2>
          <router-link :to="{ name: 'activities' }" class="flex items-center gap-1 text-sm text-signal hover:underline">全部活动<ArrowRight class="size-4" /></router-link>
        </div>
        <ActivityTable :items="upcoming" compact empty-text="最近没有即将开始的活动" />
      </div>
    </section>
  </div>
</template>
