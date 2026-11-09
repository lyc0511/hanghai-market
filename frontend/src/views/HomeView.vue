<!--
  首页：标题 + 搜索（主角）、到港公告牌（全站唯一的入场动画）、闲置货架、社团、活动航班表。
  三个板块各用不同的形式，不做成三张一样的卡片。
-->
<script setup>
import { ArrowRight, Search } from '@lucide/vue'
import { motion } from 'motion-v'
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { clubApi, itemApi } from '@/api'
import ItemCard from '@/components/ItemCard.vue'
import SignalFlag from '@/components/SignalFlag.vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { timeAgo } from '@/lib/time'
import { useMetaStore } from '@/stores/meta'

const router = useRouter()
const meta = useMetaStore()

const keyword = ref('')
const arrivals = ref([]) // 到港公告：最新上架的物品
const shelf = ref([]) // 闲置货架
const recruitingClubs = ref([])
const clubsLoaded = ref(false)
const loading = ref(true)

onMounted(async () => {
  meta.load().catch(() => {})
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
    arrivals.value = data.items.slice(0, 5)
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
      <aside class="rounded-xl bg-ocean p-5 text-white shadow-[0_20px_40px_-20px_rgba(14,42,71,0.6)]" aria-label="最新到港">
        <div class="mb-3 flex items-center justify-between text-sm text-white/60">
          <span class="font-display text-lg text-white">到港公告</span>
          <span class="flex items-center gap-1.5"><span class="size-1.5 animate-pulse rounded-full bg-buoy" />实时</span>
        </div>
        <ol class="divide-y divide-white/10" style="perspective: 600px">
          <template v-if="loading">
            <li v-for="i in 5" :key="i" class="py-3"><div class="h-5 rounded bg-white/10" /></li>
          </template>
          <motion.li
            v-for="(it, i) in arrivals"
            v-else
            :key="it.id"
            v-bind="flip(i)"
            class="origin-top"
          >
            <router-link :to="{ name: 'item', params: { id: it.id } }" class="grid grid-cols-[5.5rem_1fr_auto] items-center gap-3 py-3 hover:text-buoy">
              <span class="text-sm tabular-nums text-white/55">{{ timeAgo(it.created_at) }}</span>
              <span class="truncate">{{ it.title }}</span>
              <span v-if="it.price === 0" class="text-sm text-[#7FD1B0]">免费送</span>
              <span v-else class="tabular-nums text-buoy">¥{{ it.price }}</span>
            </router-link>
          </motion.li>
        </ol>
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
        <table class="w-full text-left text-sm">
          <thead class="border-y text-muted-foreground">
            <tr><th class="w-20 py-2 font-normal">日期</th><th class="py-2 font-normal">活动</th><th class="w-20 py-2 text-right font-normal">名额</th></tr>
          </thead>
          <tbody>
            <tr class="border-b">
              <td colspan="3" class="py-8 text-center text-muted-foreground">首批社团活动即将发布，报名后会显示在这里</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>
