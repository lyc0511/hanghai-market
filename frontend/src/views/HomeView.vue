<!--
  首页：港口主题首屏（标题 + 搜索 + 到港公告牌）→ 四大航道快速导览 → 闲置货架 → 社团招新与活动航班表 → 校园墙入口。
  清晰展示全站四大板块，每个板块形态各异、克制不复杂。
-->
<script setup>
import { ArrowRight, Calendar, Compass, MessageSquare, PenLine, Search, ShoppingBag, Users } from '@lucide/vue'
import { motion } from 'motion-v'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { activityApi, clubApi, itemApi, postApi } from '@/api'
import ActivityTable from '@/components/ActivityTable.vue'
import ItemCard from '@/components/ItemCard.vue'
import SignalFlag from '@/components/SignalFlag.vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { monthDay, weekTime } from '@/lib/activity'
import { timeAgo } from '@/lib/time'
import { tagClass } from '@/lib/wall'
import { useMetaStore } from '@/stores/meta'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const meta = useMetaStore()
const user = useUserStore()

const keyword = ref('')
const shelf = ref([])
const itemTotal = ref(0)
const recruitingClubs = ref([])
const clubTotal = ref(0)
const upcoming = ref([])
const activityTotal = ref(0)
const wallSummary = ref(null)

const clubsLoaded = ref(false)
const activitiesLoaded = ref(false)
const loading = ref(true)

const QUICK_WORDS = ['教材', '自行车', '耳机', '台灯']

/**
 * 四大航道快速导览：3 秒看清平台全部核心功能，一键直达。
 */
const channels = computed(() => [
  {
    to: { name: 'market' },
    title: '二手市场',
    desc: '教材、数码、生活闲置，谈妥加微信面交',
    stat: loading.value ? '加载中' : `${itemTotal.value} 件在售`,
    icon: ShoppingBag,
    badgeClass: 'bg-signal/10 text-signal',
  },
  {
    to: { name: 'clubs' },
    title: '社团目录',
    desc: '浏览全校社团，橙旗社团可直接申请入社',
    stat: clubsLoaded.value ? `${clubTotal.value} 个招新中` : '加载中',
    icon: Users,
    badgeClass: 'bg-buoy/12 text-buoy',
  },
  {
    to: { name: 'activities' },
    title: '社团活动',
    desc: '全校公开活动航班表，在线占位先到先得',
    stat: activitiesLoaded.value ? `${activityTotal.value} 场即将开始` : '加载中',
    icon: Calendar,
    badgeClass: 'bg-kelp/12 text-kelp',
  },
  {
    to: { name: 'wall' },
    title: '匿名校园墙',
    desc: '失物招领、求助、找搭子，先审后发护隐私',
    stat: wallSummary.value
      ? wallSummary.value.today > 0
        ? `今日新上墙 ${wallSummary.value.today} 条`
        : `共 ${wallSummary.value.total} 条帖子`
      : '校内同学专属',
    icon: MessageSquare,
    badgeClass: 'bg-ocean/10 text-ocean',
  },
])

/**
 * 到港公告：把最新上架闲置（货）、正在招新的社团（招）、即将开始的活动（航）混排成一块航班牌。
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
  postApi
    .summary()
    .then((data) => (wallSummary.value = data))
    .catch(() => {})
  activityApi
    .list({ when: 'upcoming', page_size: 5 })
    .then((data) => {
      upcoming.value = data.items
      activityTotal.value = data.total
    })
    .catch(() => {})
    .finally(() => (activitiesLoaded.value = true))
  const clubsTask = clubApi
    .list({ recruiting: true, page: 1, page_size: 20 })
    .then((data) => {
      recruitingClubs.value = data.items
      clubTotal.value = data.total
    })
    .catch(() => {})
    .finally(() => {
      clubsLoaded.value = true
    })
  try {
    const data = await itemApi.list({ page: 1, page_size: 10, sort: 'latest' })
    shelf.value = data.items.slice(0, 5)
    itemTotal.value = data.total
  } finally {
    loading.value = false
  }
  await clubsTask
})

function onSearch(word) {
  const k = (typeof word === 'string' ? word : keyword.value).trim()
  router.push({ name: 'market', query: k ? { keyword: k } : {} })
}

function goWallSubmit() {
  if (user.isLoggedIn) router.push({ name: 'wall-new' })
  else user.openLogin()
}

// 公告牌逐行翻下：绕 X 轴从 -90° 翻到 0°，呼应港口航班翻牌机
function flip(i) {
  return {
    initial: { rotateX: -90, opacity: 0 },
    animate: { rotateX: 0, opacity: 1 },
    transition: { delay: 0.2 + i * 0.1, duration: 0.42, ease: [0.22, 1, 0.36, 1] },
  }
}
</script>

<template>
  <div class="container">
    <!-- 首屏：简洁港口宣言 + 搜索 / 到港公告牌 -->
    <section class="harbor-grid relative overflow-hidden rounded-3xl border bg-white/85 p-6 sm:p-8 lg:p-10">
      <div class="grid items-center gap-8 lg:grid-cols-[1.15fr_1fr] lg:gap-10">
        <div>
          <div class="inline-flex items-center gap-2 rounded-full border bg-sail px-3 py-1 text-xs font-medium text-ocean">
            <Compass class="size-3.5 text-buoy" />
            <span>广州航海学院校内服务港湾</span>
          </div>
          <h1 class="mt-4 font-display text-4xl leading-[1.12] text-ocean sm:text-5xl lg:text-6xl">
            今天港口<br />到了什么货？
          </h1>
          <p class="mt-4 max-w-md text-sm leading-relaxed text-muted-foreground sm:text-base">
            二手闲置、社团招新、校园活动与匿名校园墙，在广航同学之间直接流转，清晰好找、面交安心。
          </p>

          <form
            class="mt-6 flex max-w-lg items-center gap-2 rounded-full border-2 border-ocean bg-white p-1.5 pl-4 shadow-xs"
            role="search"
            @submit.prevent="onSearch()"
          >
            <Search class="size-5 shrink-0 text-muted-foreground" aria-hidden="true" />
            <Input
              v-model="keyword"
              placeholder="搜教材、自行车、耳机……"
              class="h-10 border-0 bg-transparent px-1 text-base shadow-none focus-visible:ring-0"
              aria-label="搜索闲置物品"
            />
            <Button type="submit" class="h-10 rounded-full px-6 text-sm sm:text-base">搜索</Button>
          </form>

          <div class="mt-3 flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
            <span>大家常搜：</span>
            <button
              v-for="w in QUICK_WORDS"
              :key="w"
              type="button"
              class="rounded-full border bg-white px-2.5 py-1 text-ocean transition-colors hover:border-signal hover:text-signal"
              @click="onSearch(w)"
            >
              {{ w }}
            </button>
          </div>
        </div>

        <!-- 到港公告牌 -->
        <aside class="rounded-2xl bg-ocean p-5 text-white shadow-[0_20px_40px_-20px_rgba(14,42,71,0.55)]" aria-label="到港公告：最新闲置、招新和活动">
          <div class="mb-3 flex items-center justify-between text-sm text-white/60">
            <span class="font-display text-lg text-white">到港公告</span>
            <span class="flex items-center gap-1.5 text-xs"><span class="size-1.5 animate-pulse rounded-full bg-buoy" />实时动态</span>
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
              <router-link :to="row.to" class="grid grid-cols-[1.5rem_4.2rem_1fr_auto] items-center gap-2.5 py-3 text-sm hover:text-buoy">
                <span class="grid size-6 place-items-center rounded text-xs font-semibold" :class="row.tagClass" aria-hidden="true">{{ row.tag }}</span>
                <span class="text-xs tabular-nums text-white/55">{{ row.left }}</span>
                <span class="truncate">{{ row.title }}</span>
                <span class="text-xs tabular-nums sm:text-sm" :class="row.rightClass">{{ row.right }}</span>
              </router-link>
            </motion.li>
          </ol>
          <div class="mt-3 flex flex-wrap gap-4 border-t border-white/10 pt-3 text-xs text-white/55">
            <span>货 新到闲置</span>
            <span>招 社团招新</span>
            <span>航 近期活动</span>
          </div>
        </aside>
      </div>
    </section>

    <!-- 四大航道快速导览 -->
    <section class="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4" aria-label="四大核心板块导航">
      <router-link
        v-for="ch in channels"
        :key="ch.title"
        :to="ch.to"
        class="group flex flex-col justify-between rounded-2xl border bg-white p-4 transition-all hover:-translate-y-0.5 hover:border-ocean/35 hover:shadow-sm"
      >
        <div>
          <div class="flex items-center justify-between gap-2">
            <span class="grid size-9 place-items-center rounded-xl" :class="ch.badgeClass">
              <component :is="ch.icon" class="size-4.5" />
            </span>
            <ArrowRight class="size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-ocean" />
          </div>
          <h2 class="mt-3 font-semibold text-ocean">{{ ch.title }}</h2>
          <p class="mt-1 text-xs leading-relaxed text-muted-foreground">{{ ch.desc }}</p>
        </div>
        <div class="mt-3 pt-2.5 text-xs font-medium text-signal border-t border-border/60">
          {{ ch.stat }}
        </div>
      </router-link>
    </section>

    <!-- 闲置货架 -->
    <section class="mt-12">
      <div class="mb-5 flex items-end justify-between">
        <div>
          <h2 class="font-display text-3xl text-ocean">闲置货架</h2>
          <p class="mt-0.5 text-xs text-muted-foreground">刚上架的校内闲置，支持黄埔与琶洲双校区筛选</p>
        </div>
        <router-link :to="{ name: 'market' }" class="flex items-center gap-1 text-sm font-medium text-signal hover:underline">
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

    <!-- 社团招新 + 活动航班表 -->
    <section class="mt-14 grid gap-8 lg:grid-cols-[1fr_1.25fr]">
      <div class="rounded-2xl border bg-white p-5 sm:p-6">
        <div class="mb-4 flex items-end justify-between">
          <div>
            <h2 class="font-display text-2xl text-ocean sm:text-3xl">社团招新</h2>
            <p class="mt-0.5 text-xs text-muted-foreground">挂出橙色信号旗的社团正在招新</p>
          </div>
          <router-link :to="{ name: 'clubs' }" class="flex items-center gap-1 text-sm font-medium text-signal hover:underline">
            全部社团<ArrowRight class="size-4" />
          </router-link>
        </div>
        <div v-if="!clubsLoaded" class="flex flex-wrap gap-2">
          <Skeleton v-for="i in 6" :key="i" class="h-9 w-24 rounded-full" />
        </div>
        <div v-else-if="recruitingClubs.length" class="flex flex-wrap gap-2">
          <router-link
            v-for="c in recruitingClubs"
            :key="c.id"
            :to="{ name: 'club', params: { id: c.id } }"
            class="inline-flex items-center gap-2 rounded-full border bg-sail/60 px-3.5 py-1.5 text-sm text-ocean transition-colors hover:border-buoy hover:bg-white"
          >
            <SignalFlag />
            <span class="sr-only">正在招新</span>
            {{ c.title }}
          </router-link>
        </div>
        <p v-else class="rounded-xl border border-dashed bg-sail/40 px-4 py-6 text-sm text-muted-foreground">现在没有社团在招新</p>
      </div>

      <div class="rounded-2xl border bg-white p-5 sm:p-6">
        <div class="mb-4 flex items-end justify-between">
          <div>
            <h2 class="font-display text-2xl text-ocean sm:text-3xl">活动航班表</h2>
            <p class="mt-0.5 text-xs text-muted-foreground">即将开始的社团活动，全校同学均可报名</p>
          </div>
          <router-link :to="{ name: 'activities' }" class="flex items-center gap-1 text-sm font-medium text-signal hover:underline">
            全部活动<ArrowRight class="size-4" />
          </router-link>
        </div>
        <ActivityTable :items="upcoming" compact empty-text="最近没有即将开始的活动" />
      </div>
    </section>

    <!-- 校园墙轻量入口卡：补齐首页第四板块，同时严格遵守游客不看正文原则 -->
    <section class="mt-10 rounded-2xl border bg-white p-5 sm:p-6">
      <div class="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
        <div class="min-w-0">
          <div class="flex items-center gap-2">
            <h2 class="font-display text-2xl text-ocean sm:text-3xl">匿名校园墙</h2>
            <span
              v-if="wallSummary && wallSummary.today > 0"
              class="rounded-full bg-buoy/12 px-2.5 py-0.5 text-xs font-medium text-buoy"
            >
              今日新增 {{ wallSummary.today }} 条
            </span>
          </div>
          <p class="mt-1 text-sm text-muted-foreground">
            失物招领、课程求助、找运动搭子、匿名吐槽，先审后发且自动保护隐私。
          </p>
          <div v-if="wallSummary?.tags?.length" class="mt-3 flex flex-wrap gap-1.5">
            <span
              v-for="t in wallSummary.tags.filter((x) => x.count > 0).slice(0, 6)"
              :key="t.slug"
              class="rounded-full px-2.5 py-0.5 text-xs font-medium"
              :class="tagClass(t.slug)"
            >
              {{ t.name }} {{ t.count }}
            </span>
          </div>
        </div>
        <div class="flex shrink-0 flex-wrap gap-2">
          <Button variant="outline" @click="router.push({ name: 'wall' })">
            逛逛校园墙<ArrowRight class="size-4" />
          </Button>
          <Button @click="goWallSubmit">
            <PenLine class="size-4" />匿名投稿
          </Button>
        </div>
      </div>
    </section>
  </div>
</template>
