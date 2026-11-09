<!-- 活动详情：时间地点、主办社团、名额进度、报名 / 取消；主办会长能看到报名名单 -->
<script setup>
import { Check, Clock, Loader2, MapPin, Users } from '@lucide/vue'
import { AnimatePresence, motion } from 'motion-v'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'

import { activityApi } from '@/api'
import PageHeader from '@/components/PageHeader.vue'
import ReportButton from '@/components/ReportButton.vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { confirm } from '@/composables/confirm'
import { monthDay, signupState, timeRange, TONE_CLASS } from '@/lib/activity'
import { bj, formatDateTime } from '@/lib/time'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const user = useUserStore()

const act = ref(null)
const notFound = ref(false)
const busy = ref(false)
const signups = ref([])
const signupTotal = ref(0)

const state = computed(() => (act.value ? signupState(act.value) : null))
const percent = computed(() => (act.value ? Math.min(100, Math.round((act.value.enrolled_count / act.value.capacity) * 100)) : 0))

async function load() {
  try {
    act.value = await activityApi.detail(route.params.id)
    notFound.value = false
    if (act.value.is_organizer) loadSignups()
  } catch {
    notFound.value = true
  }
}

async function loadSignups() {
  try {
    const data = await activityApi.signups(route.params.id, { page_size: 100 })
    signups.value = data.items
    signupTotal.value = data.total
  } catch {
    signups.value = []
  }
}

onMounted(load)
// 在本页登录 / 退出后，「我是否已报名、是不是主办方」会变，重新加载
watch(() => user.profile?.id ?? null, (now, before) => now !== before && load())

async function onSignup() {
  if (!user.isLoggedIn) {
    user.openLogin()
    return
  }
  busy.value = true
  try {
    act.value = await activityApi.signup(act.value.id)
    toast.success('报名成功', { description: '可以在「我报名的活动」里查看' })
    if (act.value.is_organizer) loadSignups()
  } catch {
    // 名额刚好被抢完等情况：刷新一下让页面显示最新名额
    load()
  } finally {
    busy.value = false
  }
}

async function onCancel() {
  const ok = await confirm({ title: '取消报名', message: '取消后名额会让给其他同学，确定取消吗？', confirmText: '取消报名', danger: true })
  if (!ok) return
  busy.value = true
  try {
    act.value = await activityApi.cancel(act.value.id)
    toast.success('已取消报名')
    if (act.value.is_organizer) loadSignups()
  } catch {
    load()
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="container">
    <PageHeader title="活动详情">
      <ReportButton v-if="act && !act.is_organizer && act.status === 'online'" target-type="activity" :target-id="act.id" />
    </PageHeader>

    <div v-if="notFound" class="py-24 text-center">
      <p class="font-display text-2xl text-ocean">这个活动不存在或还没通过审核</p>
      <Button class="mt-6" @click="router.push({ name: 'activities' })">看看其他活动</Button>
    </div>

    <div v-else-if="!act" class="grid gap-8 lg:grid-cols-[1fr_320px]">
      <div class="space-y-4"><Skeleton class="h-10 w-2/3" /><Skeleton class="h-32" /></div>
      <Skeleton class="h-48 rounded-xl" />
    </div>

    <section v-else class="grid gap-8 lg:grid-cols-[1fr_320px]">
      <div>
        <div v-if="act.status === 'rejected'" class="mb-4 rounded-lg bg-destructive/10 px-4 py-3 text-sm text-destructive">
          未通过审核：{{ act.reject_reason }}
        </div>
        <div v-else-if="act.status === 'pending'" class="mb-4 rounded-lg bg-signal/10 px-4 py-3 text-sm text-signal">
          正在等待管理员审核，通过后同学们才能看到和报名
        </div>

        <div class="flex items-start gap-5">
          <!-- 日期牌：像航班表上的日期 -->
          <div class="shrink-0 rounded-xl bg-ocean px-4 py-3 text-center text-white">
            <div class="font-display text-3xl leading-none tabular-nums">{{ monthDay(act.start_time) }}</div>
            <div class="mt-1 text-xs text-white/70">{{ bj(act.start_time).y }}</div>
          </div>
          <div class="min-w-0">
            <h1 class="text-2xl font-semibold leading-snug text-ocean">{{ act.title }}</h1>
            <router-link :to="{ name: 'club', params: { id: act.club.id } }" class="mt-1 inline-block text-sm text-signal hover:underline">
              {{ act.club.title }} 主办
            </router-link>
          </div>
        </div>

        <dl class="mt-6 space-y-3 border-y py-5 text-sm">
          <div class="flex gap-3"><dt class="flex w-20 shrink-0 items-center gap-1.5 text-muted-foreground"><Clock class="size-4" />时间</dt><dd>{{ timeRange(act.start_time, act.end_time) }}</dd></div>
          <div class="flex gap-3"><dt class="flex w-20 shrink-0 items-center gap-1.5 text-muted-foreground"><MapPin class="size-4" />地点</dt><dd>{{ act.location }}<template v-if="act.campus_area">（{{ act.campus_area }}）</template></dd></div>
          <div v-if="act.signup_deadline" class="flex gap-3"><dt class="w-20 shrink-0 pl-5.5 text-muted-foreground">报名截止</dt><dd>{{ formatDateTime(act.signup_deadline) }}</dd></div>
        </dl>

        <div v-if="act.tags.length" class="mt-4 flex flex-wrap gap-1.5">
          <Badge v-for="t in act.tags" :key="t" variant="secondary">{{ t }}</Badge>
        </div>

        <section v-if="act.summary" class="mt-8">
          <h2 class="font-display text-2xl text-ocean">活动介绍</h2>
          <p class="mt-3 max-w-2xl whitespace-pre-wrap leading-loose text-muted-foreground">{{ act.summary }}</p>
        </section>

        <!-- 主办会长：报名名单 -->
        <section v-if="act.is_organizer" class="mt-10">
          <h2 class="font-display text-2xl text-ocean">报名名单<span class="ml-2 font-sans text-base text-muted-foreground">{{ signupTotal }} 人</span></h2>
          <ul class="mt-3 divide-y rounded-xl border bg-white">
            <li v-for="s in signups" :key="s.user_id" class="flex items-center gap-3 px-4 py-2.5 text-sm">
              <span class="grid size-8 place-items-center rounded-full bg-secondary font-medium text-ocean">{{ s.nickname.slice(0, 1) }}</span>
              <span class="flex-1 text-ocean">{{ s.nickname }}</span>
              <span class="text-xs text-muted-foreground">{{ formatDateTime(s.signed_at) }} 报名</span>
            </li>
            <li v-if="!signups.length" class="px-4 py-8 text-center text-sm text-muted-foreground">还没有人报名</li>
          </ul>
        </section>
      </div>

      <!-- 右侧：名额与报名 -->
      <aside class="h-fit rounded-xl border bg-white p-5 lg:sticky lg:top-24">
        <div class="flex items-baseline justify-between">
          <span class="flex items-center gap-1.5 text-sm text-muted-foreground"><Users class="size-4" />名额</span>
          <span class="rounded px-1.5 py-0.5 text-xs" :class="TONE_CLASS[state.tone]">{{ state.text }}</span>
        </div>
        <div class="mt-2 font-display text-4xl tabular-nums text-ocean">
          {{ act.enrolled_count }}<span class="text-xl text-muted-foreground">/{{ act.capacity }}</span>
        </div>
        <!-- 名额进度条：宽度变化带过渡，报名 / 取消后能看到它在动 -->
        <div class="mt-3 h-2 overflow-hidden rounded-full bg-secondary" role="progressbar" :aria-valuenow="act.enrolled_count" :aria-valuemax="act.capacity">
          <div class="h-full rounded-full transition-[width] duration-500" :class="percent >= 100 ? 'bg-buoy' : 'bg-kelp'" :style="{ width: percent + '%' }" />
        </div>

        <div class="mt-6">
          <template v-if="act.signed_up">
            <AnimatePresence mode="wait">
              <motion.div key="signed" :initial="{ opacity: 0, y: 6 }" :animate="{ opacity: 1, y: 0 }" class="flex items-center gap-2 rounded-lg bg-kelp/10 px-3 py-2.5 text-sm text-kelp">
                <Check class="size-4" />你已报名，记得准时参加
              </motion.div>
            </AnimatePresence>
            <Button v-if="act.phase === 'upcoming'" variant="ghost" class="mt-2 w-full text-muted-foreground" :disabled="busy" @click="onCancel">
              <Loader2 v-if="busy" class="animate-spin" />取消报名
            </Button>
          </template>
          <Button v-else-if="act.signup_open" size="lg" class="h-11 w-full text-base" :disabled="busy" @click="onSignup">
            <Loader2 v-if="busy" class="animate-spin" />报名参加
          </Button>
          <Button v-else size="lg" class="h-11 w-full" disabled>{{ state.text }}</Button>
        </div>
        <p v-if="act.signup_open && !act.signed_up" class="mt-3 text-xs text-muted-foreground">活动开始前都可以取消报名，名额会让给其他同学。</p>
      </aside>
    </section>
  </div>
</template>
