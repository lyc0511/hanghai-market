<!--
  帖子的评论区：列表 + 输入框 + 回复 + 删除 + 举报。
  评论显示昵称；帖子的投稿人在这里显示为「楼主」（后端不返回楼主的昵称）。
  评论数变化时通过 @count 告诉父组件，让帖子卡片上的数字同步。
-->
<script setup>
import { Loader2, Send, X } from '@lucide/vue'
import { computed, onMounted, ref, watch } from 'vue'
import { toast } from 'vue-sonner'

import { postApi } from '@/api'
import ReportButton from '@/components/ReportButton.vue'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Textarea } from '@/components/ui/textarea'
import { confirm } from '@/composables/confirm'
import { timeAgo } from '@/lib/time'
import { useUserStore } from '@/stores/user'

const props = defineProps({
  postId: { type: Number, required: true },
  isMine: { type: Boolean, default: false }, // 当前用户是不是楼主
  canComment: { type: Boolean, default: true }, // 只有已上墙的帖子能评论
})
const emit = defineEmits(['count'])

const COMMENT_MAX = 300
const PAGE_SIZE = 30

const user = useUserStore()
const items = ref([])
const page = ref(0)
const total = ref(0)
const loading = ref(false)

const draft = ref('')
const replyTo = ref(null) // { id, name }
const sending = ref(false)
const busyId = ref(null)
const input = ref()

const draftLength = computed(() => draft.value.trim().length)

function nameOf(c) {
  return c.is_op ? '楼主' : c.nickname
}

async function loadMore() {
  loading.value = true
  try {
    const data = await postApi.comments(props.postId, { page: page.value + 1, page_size: PAGE_SIZE })
    items.value.push(...data.items)
    page.value = data.page
    total.value = data.total
  } catch {
    /* 提示已由 http.js 弹出 */
  } finally {
    loading.value = false
  }
}

function reload() {
  items.value = []
  page.value = 0
  total.value = 0
  loadMore()
}

function startReply(c) {
  replyTo.value = { id: c.id, name: nameOf(c) }
  input.value?.$el?.focus?.()
}

async function send() {
  if (!draftLength.value || sending.value) return
  sending.value = true
  try {
    const c = await postApi.addComment(props.postId, draft.value.trim(), replyTo.value?.id)
    // 已经加载到最后一页时直接追加；否则只更新总数，等用户点「加载更多」
    if (items.value.length >= total.value) items.value.push(c)
    total.value += 1
    emit('count', total.value)
    draft.value = ''
    replyTo.value = null
  } catch {
    /* 提示已由 http.js 弹出 */
  } finally {
    sending.value = false
  }
}

async function remove(c) {
  const byAdmin = !c.is_mine
  const ok = await confirm({
    title: byAdmin ? '下架这条评论' : '删除这条评论',
    message: byAdmin ? '下架后大家都看不到它，评论人会收到通知。' : '删除后不能恢复。',
    confirmText: byAdmin ? '下架' : '删除',
    danger: true,
  })
  if (!ok) return
  busyId.value = c.id
  try {
    await postApi.removeComment(props.postId, c.id)
    items.value = items.value.filter((x) => x.id !== c.id)
    total.value = Math.max(0, total.value - 1)
    emit('count', total.value)
    toast.success(byAdmin ? '已下架' : '已删除')
  } catch {
    /* 提示已由 http.js 弹出 */
  } finally {
    busyId.value = null
  }
}

onMounted(loadMore)
watch(() => props.postId, reload)
</script>

<template>
  <section id="comments" class="mt-3 scroll-mt-20 rounded-2xl border bg-white p-4 sm:p-5">
    <h2 class="text-[15px] font-medium text-ocean">评论 <span class="text-muted-foreground">{{ total || '' }}</span></h2>

    <!-- 输入框 -->
    <div v-if="canComment" class="mt-3">
      <div v-if="replyTo" class="mb-2 inline-flex items-center gap-1 rounded-full bg-secondary py-1 pl-3 pr-1.5 text-xs text-ocean">
        回复 {{ replyTo.name }}
        <button type="button" class="grid size-5 place-items-center rounded-full hover:bg-white" aria-label="取消回复" @click="replyTo = null">
          <X class="size-3" />
        </button>
      </div>
      <Textarea
        ref="input"
        v-model="draft"
        rows="2"
        :maxlength="COMMENT_MAX"
        :placeholder="replyTo ? `回复 ${replyTo.name}…` : '说点什么…'"
        class="text-[15px]"
        aria-label="评论内容"
        @keydown.ctrl.enter.prevent="send"
      />
      <div class="mt-2 flex items-center gap-3">
        <p class="min-w-0 flex-1 text-xs text-muted-foreground">
          {{ isMine ? '你是楼主，评论会显示为「楼主」，不显示昵称。' : `评论会显示你的昵称「${user.profile?.nickname ?? ''}」。` }}
        </p>
        <span class="text-xs tabular-nums text-muted-foreground">{{ draftLength }}/{{ COMMENT_MAX }}</span>
        <Button size="sm" :disabled="!draftLength || sending" @click="send">
          <Loader2 v-if="sending" class="animate-spin" /><Send v-else />发表
        </Button>
      </div>
    </div>
    <p v-else class="mt-3 text-sm text-muted-foreground">帖子上墙后才能评论。</p>

    <!-- 列表 -->
    <ul v-if="items.length" class="mt-4 divide-y">
      <li v-for="c in items" :key="c.id" class="flex gap-3 py-3.5">
        <span
          class="grid size-8 shrink-0 place-items-center rounded-full text-sm font-medium"
          :class="c.is_op ? 'bg-ocean text-white' : 'bg-secondary text-ocean'"
          aria-hidden="true"
        >
          {{ c.is_op ? '主' : c.nickname?.slice(0, 1) }}
        </span>
        <div class="min-w-0 flex-1">
          <div class="flex flex-wrap items-center gap-x-2 text-sm">
            <span class="font-medium text-ocean">{{ nameOf(c) }}</span>
            <span v-if="c.is_mine" class="rounded bg-ocean/10 px-1.5 py-px text-[11px] text-ocean">我</span>
            <span class="text-xs text-muted-foreground">{{ timeAgo(c.created_at) }}</span>
          </div>
          <p class="mt-1 whitespace-pre-line break-words text-[15px] leading-relaxed">
            <span v-if="c.reply_to" class="text-muted-foreground">回复 {{ c.reply_to.name }}：</span>{{ c.body }}
          </p>
          <div class="mt-1.5 flex items-center gap-4 text-xs text-muted-foreground">
            <button v-if="canComment" type="button" class="hover:text-ocean" @click="startReply(c)">回复</button>
            <button
              v-if="c.is_mine || user.isAdmin"
              type="button"
              class="hover:text-destructive disabled:opacity-60"
              :disabled="busyId === c.id"
              @click="remove(c)"
            >
              {{ c.is_mine ? '删除' : '下架' }}
            </button>
            <ReportButton v-if="!c.is_mine" compact target-type="comment" :target-id="c.id" />
          </div>
        </div>
      </li>
    </ul>

    <div v-if="loading && !items.length" class="mt-4 space-y-3">
      <div v-for="i in 2" :key="i" class="flex gap-3"><Skeleton class="size-8 rounded-full" /><div class="flex-1 space-y-2"><Skeleton class="h-4 w-24" /><Skeleton class="h-4 w-2/3" /></div></div>
    </div>
    <p v-else-if="!items.length" class="mt-4 py-6 text-center text-sm text-muted-foreground">还没有评论{{ canComment ? '，来说第一句吧' : '' }}</p>
    <div v-else-if="items.length < total" class="mt-2 text-center">
      <Button variant="ghost" size="sm" :disabled="loading" @click="loadMore"><Loader2 v-if="loading" class="animate-spin" />查看更多评论</Button>
    </div>
  </section>
</template>
