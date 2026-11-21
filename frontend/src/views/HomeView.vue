<script setup>
import { ArrowRight, Search } from '@lucide/vue'
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { activityApi, clubApi, itemApi, postApi } from '@/api'
import ItemCard from '@/components/ItemCard.vue'
import { monthDay, weekTime } from '@/lib/activity'
import { timeAgo } from '@/lib/time'
import { useMetaStore } from '@/stores/meta'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const meta = useMetaStore()
const user = useUserStore()
const keyword = ref('')
const campus = ref('all')
const items = ref([])
const clubs = ref([])
const activities = ref([])
const posts = ref([])
const wallSummary = ref(null)
const itemsLoading = ref(true)
const clubsLoading = ref(true)
const activitiesLoading = ref(true)
const postsLoading = ref(false)
let loadId = 0
let postLoadId = 0

const shortcuts = [
  { title: '二手闲置', detail: '淘点需要的，也出点用不上的', mobileDetail: '淘好物', to: { name: 'market' } },
  { title: '社团招新', detail: '找到一起做喜欢的事的人', mobileDetail: '找同好', to: { name: 'clubs' } },
  { title: '校园活动', detail: '讲座、球赛、周末出行', mobileDetail: '一起玩', to: { name: 'activities' } },
  { title: '校园墙', detail: '求助、寻物、找搭子', mobileDetail: '聊一聊', to: { name: 'wall' } },
]

const campusLabel = computed(() => campus.value === 'all' ? '全部校区' : campus.value)

function onSearch() {
  const value = keyword.value.trim()
  router.push({ name: 'market', query: value ? { keyword: value } : {} })
}

function loadSections() {
  const current = ++loadId
  const filter = campus.value === 'all' ? {} : { campus_area: campus.value }
  itemsLoading.value = true
  clubsLoading.value = true
  activitiesLoading.value = true

  itemApi.list({ page: 1, page_size: 4, sort: 'latest', ...filter })
    .then((data) => { if (current === loadId) items.value = data.items })
    .catch(() => { if (current === loadId) items.value = [] })
    .finally(() => { if (current === loadId) itemsLoading.value = false })

  clubApi.list({ recruiting: true, page: 1, page_size: 3, ...filter })
    .then((data) => { if (current === loadId) clubs.value = data.items })
    .catch(() => { if (current === loadId) clubs.value = [] })
    .finally(() => { if (current === loadId) clubsLoading.value = false })

  activityApi.list({ when: 'upcoming', page: 1, page_size: 3, ...filter })
    .then((data) => { if (current === loadId) activities.value = data.items })
    .catch(() => { if (current === loadId) activities.value = [] })
    .finally(() => { if (current === loadId) activitiesLoading.value = false })
}

function loadPosts(loggedIn) {
  const current = ++postLoadId
  posts.value = []
  if (!loggedIn) {
    postsLoading.value = false
    return
  }
  postsLoading.value = true
  postApi.list({ page: 1, page_size: 2 })
    .then((data) => { if (current === postLoadId) posts.value = data.items })
    .catch(() => { if (current === postLoadId) posts.value = [] })
    .finally(() => { if (current === postLoadId) postsLoading.value = false })
}

watch(campus, loadSections)
watch(() => user.isLoggedIn, loadPosts, { immediate: true })

onMounted(() => {
  meta.load().catch(() => {})
  postApi.summary()
    .then((data) => { wallSummary.value = data })
    .catch(() => {})
  loadSections()
})

function activityDate(value) {
  return monthDay(value).replace('/', '.')
}

function postPreview(body) {
  return body?.replace(/\s+/g, ' ').trim() || ''
}
</script>

<template>
  <div class="figma-home">
    <div class="home-content">
      <div class="home-greeting">
        <div>
          <h1>今天，在校园里逛逛。</h1>
          <p>广州航海学院 · 闲置流转、社团相遇，还有身边的新鲜事</p>
        </div>
        <label class="home-campus">
          <span class="sr-only">筛选校区</span>
          <select v-model="campus" :aria-label="'当前校区：' + campusLabel">
            <option value="all">全部校区</option>
            <option value="黄埔校区">黄埔校区</option>
            <option value="琶洲校区">琶洲校区</option>
          </select>
        </label>
      </div>

      <form class="home-search" role="search" @submit.prevent="onSearch">
        <Search class="home-search-icon" aria-hidden="true" />
        <input v-model="keyword" type="search" placeholder="搜索闲置物品" aria-label="搜索闲置物品" />
        <button type="submit">搜索</button>
      </form>

      <nav class="home-shortcuts" aria-label="校园服务快捷入口">
        <router-link v-for="entry in shortcuts" :key="entry.title" :to="entry.to" class="home-shortcut">
          <strong>{{ entry.title }} <span class="shortcut-arrow">↗</span></strong>
          <span class="shortcut-desktop">{{ entry.detail }}</span>
          <span class="shortcut-mobile">{{ entry.mobileDetail }}</span>
        </router-link>
      </nav>

      <section class="home-section" aria-labelledby="latest-items">
        <div class="home-section-heading">
          <h2 id="latest-items">最新闲置</h2>
          <router-link :to="{ name: 'market' }">看看全部 <ArrowRight aria-hidden="true" /></router-link>
        </div>
        <div v-if="itemsLoading" class="home-items-grid" aria-label="正在加载闲置">
          <div v-for="index in 4" :key="index" class="home-item-skeleton">
            <span class="home-item-skeleton-image" />
            <span class="home-item-skeleton-line" />
          </div>
        </div>
        <div v-else-if="items.length" class="home-items-grid">
          <ItemCard v-for="item in items" :key="item.id" :item="item" variant="home" />
        </div>
        <div v-else class="home-empty">这个校区暂时没有新上架的闲置。<router-link :to="{ name: 'market' }">去二手市场看看 →</router-link></div>
      </section>

      <div class="home-columns">
        <section class="home-panel" aria-labelledby="recruiting-clubs">
          <div class="home-section-heading">
            <h2 id="recruiting-clubs">正在招新的社团</h2>
            <router-link :to="{ name: 'clubs' }">全部社团 <ArrowRight aria-hidden="true" /></router-link>
          </div>
          <div v-if="clubsLoading" class="home-panel-empty">正在加载社团…</div>
          <div v-else-if="clubs.length" class="home-panel-list">
            <router-link
              v-for="club in clubs"
              :key="club.id"
              :to="{ name: 'club', params: { id: club.id } }"
              class="home-club-row"
            >
              <span class="home-list-copy">
                <strong>{{ club.title }}</strong>
                <small>{{ club.summary || '来认识更多有共同兴趣的同学。' }}</small>
              </span>
              <span class="home-club-badge">招新中</span>
              <span class="home-club-mobile-action">加入 →</span>
            </router-link>
          </div>
          <div v-else class="home-panel-empty">这个校区暂时没有正在招新的社团。</div>
        </section>

        <section class="home-panel" aria-labelledby="upcoming-activities">
          <div class="home-section-heading">
            <h2 id="upcoming-activities">近期活动</h2>
            <router-link :to="{ name: 'activities' }">活动日历 <ArrowRight aria-hidden="true" /></router-link>
          </div>
          <div v-if="activitiesLoading" class="home-panel-empty">正在加载活动…</div>
          <div v-else-if="activities.length" class="home-panel-list">
            <router-link
              v-for="activity in activities"
              :key="activity.id"
              :to="{ name: 'activity', params: { id: activity.id } }"
              class="home-activity-row"
            >
              <span class="home-activity-date">{{ activityDate(activity.start_time) }}</span>
              <span class="home-list-copy">
                <strong>{{ activity.title }}</strong>
                <small>{{ weekTime(activity.start_time) }} · {{ activity.location }}</small>
              </span>
            </router-link>
          </div>
          <div v-else class="home-panel-empty">这个校区暂时没有即将开始的活动。</div>
        </section>
      </div>

      <section class="home-section home-wall" aria-labelledby="wall-preview">
        <div class="home-section-heading">
          <h2 id="wall-preview">校园墙 · 此刻校园</h2>
          <router-link :to="{ name: 'wall' }">去逛逛 <ArrowRight aria-hidden="true" /></router-link>
        </div>
        <div v-if="user.isLoggedIn && postsLoading" class="home-panel-empty">正在加载校园墙…</div>
        <div v-else-if="user.isLoggedIn && posts.length" class="home-posts">
          <router-link v-for="post in posts" :key="post.id" :to="{ name: 'wall-post', params: { id: post.id } }" class="home-post">
            <span class="home-post-tag">{{ post.tag?.name || '校园日常' }}</span>
            <strong>{{ postPreview(post.body) }}</strong>
            <small>{{ post.published_at ? timeAgo(post.published_at) : '' }}</small>
          </router-link>
        </div>
        <div v-else-if="user.isLoggedIn" class="home-panel-empty">校园墙暂时没有新帖子。</div>
        <button v-else type="button" class="home-wall-guest" @click="user.openLogin()">
          登录后查看同学们的校园动态
          <span v-if="wallSummary?.today"> · 今天新增 {{ wallSummary.today }} 条</span>
          <ArrowRight aria-hidden="true" />
        </button>
      </section>
    </div>
  </div>
</template>

<style scoped>
.figma-home {
  --home-blue: #176B98;
  --home-dark: #0E2A47;
  --home-muted: #607487;
  --home-soft: #E7F2F7;
  min-height: 100%;
  background: linear-gradient(180deg, #F0F8FB 0, #F7FAFC 320px);
  color: var(--home-dark);
  font-family: "Noto Sans SC", "Microsoft YaHei", sans-serif;
}
.home-content { width: min(100% - 40px, 1152px); margin: 0 auto; padding: 36px 0 40px; }
.home-greeting { display: flex; align-items: flex-start; justify-content: space-between; gap: 24px; }
.home-greeting h1 { margin: 0; font-size: 30px; line-height: 1.5; font-weight: 700; }
.home-greeting p { margin-top: 7px; color: var(--home-muted); font-size: 14px; }
.home-campus select { appearance: none; border: 0; border-radius: 6px; padding: 9px 28px 9px 14px; background: #fff; color: var(--home-dark); cursor: pointer; font-size: 13px; }
.home-campus::after { content: "⌄"; position: relative; right: 18px; pointer-events: none; color: var(--home-blue); }
.home-search { display: flex; align-items: center; gap: 16px; height: 54px; margin-top: 32px; padding: 8px 8px 8px 20px; border: 1px solid #B8D0DE; border-radius: 10px; background: #fff; }
.home-search-icon { width: 18px; height: 18px; color: var(--home-muted); }
.home-search input { min-width: 0; flex: 1; border: 0; outline: 0; background: transparent; color: var(--home-dark); font-size: 15px; }
.home-search input::placeholder { color: var(--home-muted); }
.home-search button { align-self: stretch; padding: 0 16px; border-radius: 6px; background: var(--home-blue); color: #fff; font-size: 13px; font-weight: 500; }
.home-search button:hover { background: #105779; }
.home-shortcuts { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-top: 32px; }
.home-shortcut { min-width: 0; min-height: 87px; display: flex; flex-direction: column; gap: 7px; padding: 18px; border-radius: 8px; background: #fff; transition: box-shadow .2s, transform .2s; }
.home-shortcut:hover { box-shadow: 0 4px 14px #0E2A4714; transform: translateY(-2px); }
.home-shortcut strong { font-size: 17px; font-weight: 500; line-height: 1.5; }
.home-shortcut > span { color: var(--home-muted); font-size: 12px; }
.shortcut-arrow { color: var(--home-blue); }
.shortcut-mobile { display: none; }
.home-section { margin-top: 32px; }
.home-section-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 18px; }
.home-section-heading h2 { margin: 0; font-size: 23px; line-height: 1.5; font-weight: 700; }
.home-section-heading a { display: inline-flex; align-items: center; gap: 4px; flex-shrink: 0; color: var(--home-blue); font-size: 13px; font-weight: 500; }
.home-section-heading a:hover { text-decoration: underline; }
.home-section-heading svg { width: 14px; height: 14px; }
.home-items-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 20px; }
.home-item-skeleton-image { display: block; height: 188px; border-radius: 8px; background: #E7F2F7; }
.home-item-skeleton-line { display: block; width: 80%; height: 16px; margin-top: 12px; border-radius: 4px; background: #DFEAF0; }
.home-empty, .home-panel-empty { color: var(--home-muted); font-size: 13px; }
.home-empty { padding: 36px 18px; border-radius: 8px; background: #fff; }
.home-empty a { display: inline-block; margin-left: 8px; color: var(--home-blue); }
.home-columns { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 32px; margin-top: 32px; }
.home-panel { min-width: 0; border-radius: 10px; padding: 24px; background: #fff; }
.home-panel .home-section-heading { margin-bottom: 18px; }
.home-panel-list { display: flex; flex-direction: column; gap: 18px; }
.home-panel-empty { padding: 20px 0; }
.home-club-row, .home-activity-row { min-width: 0; display: flex; align-items: flex-start; gap: 12px; }
.home-club-row:hover strong, .home-activity-row:hover strong { color: var(--home-blue); }
.home-list-copy { display: flex; min-width: 0; flex: 1; flex-direction: column; gap: 5px; }
.home-list-copy strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 15px; font-weight: 500; }
.home-list-copy small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--home-muted); font-size: 12px; }
.home-club-badge { flex: none; border-radius: 6px; padding: 8px 14px; background: var(--home-soft); color: var(--home-blue); font-size: 13px; }
.home-club-mobile-action { display: none; }
.home-activity-date { flex: none; border-radius: 5px; padding: 10px; background: var(--home-soft); color: var(--home-blue); font-size: 16px; font-weight: 700; line-height: 24px; }
.home-wall { margin-top: 32px; }
.home-posts { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 24px; }
.home-post { display: flex; min-width: 0; flex-direction: column; gap: 7px; padding: 18px; border-radius: 8px; background: #fff; }
.home-post:hover strong { color: var(--home-blue); }
.home-post-tag { color: var(--home-blue); font-size: 12px; font-weight: 500; }
.home-post strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 14px; font-weight: 400; }
.home-post small { color: var(--home-muted); font-size: 11px; }
.home-wall-guest { display: flex; align-items: center; gap: 8px; width: 100%; padding: 24px; border-radius: 8px; background: #fff; color: var(--home-blue); text-align: left; font-size: 14px; }
.home-wall-guest svg { width: 16px; height: 16px; }

@media (max-width: 767px) {
  .home-content { padding-top: 24px; padding-bottom: 28px; }
  .home-greeting { align-items: center; gap: 8px; }
  .home-greeting h1 { font-size: 21px; white-space: nowrap; }
  .home-greeting p { display: none; }
  .home-campus { flex: none; }
  .home-campus select { max-width: 60px; padding: 6px 14px 6px 4px; background: transparent; color: var(--home-blue); font-size: 12px; }
  .home-campus::after { right: 13px; }
  .home-search { height: 45px; gap: 8px; margin-top: 17px; padding: 8px 12px; border: 0; border-radius: 8px; }
  .home-search-icon { display: none; }
  .home-search input { font-size: 14px; }
  .home-search button { padding: 0; background: transparent; color: var(--home-blue); font-size: 14px; }
  .home-search button:hover { background: transparent; }
  .home-shortcuts { gap: 8px; margin-top: 17px; }
  .home-shortcut { align-items: center; gap: 5px; min-height: 58px; padding: 8px 3px; border-radius: 6px; text-align: center; }
  .home-shortcut strong { color: var(--home-blue); font-size: 13px; white-space: nowrap; }
  .shortcut-arrow, .shortcut-desktop { display: none; }
  .home-shortcut .shortcut-mobile { display: block; font-size: 11px; }
  .home-section { margin-top: 18px; }
  .home-section-heading { margin-bottom: 16px; }
  .home-section-heading h2 { font-size: 20px; }
  .home-section-heading a { font-size: 12px; }
  .home-items-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
  .home-item-skeleton-image { height: 145px; }
  .home-columns { display: flex; flex-direction: column; gap: 22px; margin-top: 24px; }
  .home-panel { padding: 0; background: transparent; }
  .home-panel .home-section-heading { margin-bottom: 14px; }
  .home-panel-list { gap: 10px; }
  .home-club-row, .home-activity-row { padding: 14px; border-radius: 8px; background: #fff; }
  .home-club-row:nth-child(n+3), .home-activity-row:nth-child(n+2) { display: none; }
  .home-club-badge { display: none; }
  .home-club-mobile-action { display: block; flex: none; color: var(--home-blue); font-size: 12px; }
  .home-activity-date { padding: 8px; }
  .home-wall { margin-top: 24px; }
  .home-posts { grid-template-columns: 1fr; gap: 10px; }
  .home-post:nth-child(n+2) { display: none; }
  .home-post { padding: 0; background: transparent; }
  .home-post strong { white-space: normal; }
  .home-post small { display: none; }
}
</style>
