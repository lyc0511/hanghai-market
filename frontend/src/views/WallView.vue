<!--
  墙：一条信息流 + 标签筛选 + 搜索。只有登录的同学能看到内容；
  游客看到的是登录提示和几个数字（今天新增多少、各标签有多少），证明里面是活的，但不透露任何内容。
  排序由后端决定：置顶在最前，其余按上墙时间从新到旧。
-->
<script setup>
import { Loader2, Lock, PenLine, Search, X } from '@lucide/vue'
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { postApi } from '@/api'
import PostCard from '@/components/PostCard.vue'
import SectionBanner from '@/components/SectionBanner.vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { useMetaStore } from '@/stores/meta'
import { tagClass } from '@/lib/wall'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const meta = useMetaStore()
const user = useUserStore()

const PAGE_SIZE = 20

const tagId = ref(0) // 0 = 全部
const keywordInput = ref('')
const keyword = ref('')
const posts = ref([])
const page = ref(0)
const total = ref(0)
const loading = ref(false)
const summary = ref(null) // 游客看的统计数字
// 每次重新加载加 1：筛选切换得很快时，丢弃旧请求晚到的结果
let loadSeq = 0

async function loadMore() {
  const seq = loadSeq
  loading.value = true
  try {
    const params = { page: page.value + 1, page_size: PAGE_SIZE }
    if (tagId.value) params.tag_id = tagId.value
    if (keyword.value) params.keyword = keyword.value
    const data = await postApi.list(params)
    if (seq !== loadSeq) return
    posts.value.push(...data.items)
    page.value = data.page
    total.value = data.total
  } catch {
    /* 提示已由 http.js 弹出 */
  } finally {
    if (seq === loadSeq) loading.value = false
  }
}

function reload() {
  loadSeq += 1
  posts.value = []
  page.value = 0
  total.value = 0
  loadMore()
}

async function loadSummary() {
  try {
    summary.value = await postApi.summary()
  } catch {
    summary.value = null // 拿不到数字不影响登录提示
  }
}

function onSearch() {
  keyword.value = keywordInput.value.trim()
}

function clearSearch() {
  keywordInput.value = ''
  keyword.value = ''
}

watch([tagId, keyword], reload)
// 在这个页面上登录 / 退出时，立刻切换显示
watch(
  () => user.isLoggedIn,
  (v) => {
    if (v) reload()
    else {
      posts.value = []
      loadSummary()
    }
  },
)

onMounted(() => {
  meta.load().catch(() => {})
  if (user.isLoggedIn) loadMore()
  else loadSummary()
})
</script>

<template>
  <div class="container narrow">
    <SectionBanner
      eyebrow="匿名广场"
      title="校园墙"
      description="匿名投稿，审核后上墙。失物招领、求助、找搭子、想说的话，都可以发。"
    >
      <template v-if="user.isLoggedIn" #actions>
        <Button class="shrink-0" @click="router.push({ name: 'wall-new' })"><PenLine />匿名投稿</Button>
      </template>
    </SectionBanner>

    <!-- 游客：看不到内容 -->
    <div v-if="!user.isLoggedIn" class="mt-8 rounded-2xl border bg-white px-6 py-14 text-center">
      <span class="mx-auto grid size-14 place-items-center rounded-full bg-secondary text-ocean/60"><Lock class="size-6" /></span>
      <p class="mt-4 text-lg font-medium text-ocean">墙上的内容只对登录的同学开放</p>
      <p class="mt-1 text-sm text-muted-foreground">登录后可以看墙、匿名投稿和评论</p>

      <template v-if="summary && summary.total > 0">
        <p class="mt-6 text-sm text-ocean">
          <template v-if="summary.today > 0">今天新上墙 <strong class="text-xl tabular-nums text-buoy">{{ summary.today }}</strong> 条，</template>
          墙上共 <strong class="text-xl tabular-nums">{{ summary.total }}</strong> 条
        </p>
        <div class="mt-3 flex flex-wrap justify-center gap-1.5">
          <span
            v-for="t in summary.tags.filter((x) => x.count > 0)"
            :key="t.slug"
            class="rounded-full px-2.5 py-1 text-xs font-medium"
            :class="tagClass(t.slug)"
          >
            {{ t.name }} {{ t.count }}
          </span>
        </div>
      </template>
      <div class="mt-6 flex justify-center gap-3">
        <Button @click="user.openLogin('login')">登录</Button>
        <Button variant="outline" @click="user.openLogin('register')">注册</Button>
      </div>
    </div>

    <template v-else>
      <div class="mt-5 space-y-3 rounded-2xl border bg-white p-3.5">
        <!-- 标签：横向一排，手机上可以左右滑动 -->
        <div
          class="-mx-1 flex gap-1.5 overflow-x-auto px-1 pb-0.5 [scrollbar-width:none] sm:mx-0 sm:flex-wrap sm:px-0 [&::-webkit-scrollbar]:hidden"
          role="radiogroup"
          aria-label="标签"
        >
          <button
            v-for="t in [{ id: 0, name: '全部' }, ...meta.postTags]"
            :key="t.id"
            type="button"
            role="radio"
            :aria-checked="tagId === t.id"
            class="shrink-0 rounded-full px-3.5 py-1.5 text-sm transition-colors"
            :class="tagId === t.id ? 'bg-ocean text-white' : 'bg-sail text-muted-foreground hover:bg-secondary hover:text-ocean'"
            @click="tagId = t.id"
          >
            {{ t.name }}
          </button>
        </div>

        <form class="relative" role="search" @submit.prevent="onSearch">
          <Search class="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input v-model="keywordInput" placeholder="搜一搜，比如：校园卡、羽毛球" class="h-10 rounded-full bg-sail pl-10 pr-10" aria-label="搜索帖子" />
          <button
            v-if="keywordInput"
            type="button"
            class="absolute right-2 top-1/2 grid size-7 -translate-y-1/2 place-items-center rounded-full text-muted-foreground hover:bg-secondary"
            aria-label="清除搜索"
            @click="clearSearch"
          >
            <X class="size-4" />
          </button>
        </form>
      </div>

      <div class="mt-5 min-h-80 space-y-3">
        <template v-if="loading && !posts.length">
          <div v-for="i in 3" :key="i" class="rounded-2xl border bg-white p-5">
            <div class="flex items-center gap-3"><Skeleton class="size-10 rounded-full" /><Skeleton class="h-4 w-24" /></div>
            <Skeleton class="mt-4 h-4 w-full" /><Skeleton class="mt-2 h-4 w-2/3" />
          </div>
        </template>

        <template v-else-if="posts.length">
          <PostCard v-for="p in posts" :key="p.id" :post="p" clamp />
          <div v-if="posts.length < total" class="pt-3 text-center">
            <Button variant="outline" :disabled="loading" @click="loadMore"><Loader2 v-if="loading" class="animate-spin" />加载更多</Button>
          </div>
          <p v-else class="pt-3 text-center text-xs text-muted-foreground">已经到底了</p>
        </template>

        <div v-else class="rounded-2xl border bg-white px-6 py-16 text-center">
          <p class="font-medium text-ocean">{{ keyword || tagId ? '没有找到相关的帖子' : '墙上还是空的' }}</p>
          <p class="mt-1 text-sm text-muted-foreground">{{ keyword || tagId ? '换个关键词或标签试试' : '来发第一条吧' }}</p>
          <Button class="mt-5" @click="router.push({ name: 'wall-new' })"><PenLine />投稿</Button>
        </div>
      </div>
    </template>
  </div>
</template>
