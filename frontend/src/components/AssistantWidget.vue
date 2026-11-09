<!--
  AI 助手「小航」：右下角悬浮按钮 + 聊天面板（手机上全屏）。
  - 对话历史只存在本标签页的 sessionStorage，每次提问把最近的历史一起发给后端（后端不保存上下文）。
  - 助手回复里的 [文字](/路径) 渲染成站内链接；只认以 / 开头的站内路径，其他一律当普通文字，不用 v-html，避免注入。
  - 搜到的物品 / 社团 / 活动以卡片显示在回复下方，点击跳转。
-->
<script setup>
import { ArrowUp, Loader2, RotateCcw, Sparkles, X } from '@lucide/vue'
import { nextTick, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import { assistantApi } from '@/api'

const STORE_KEY = 'hhjs-assistant'
const SUGGESTIONS = ['有没有 50 元以内的台灯', '最近有什么活动可以报名', '哪些社团在招新', '怎么发布闲置']
const TYPE_NAMES = { item: '闲置', club: '社团', activity: '活动' }
const LINK_RE = /\[([^\]\n]+)\]\((\/(?!\/)[^)\s]*)\)/g

const route = useRoute()

const open = ref(false)
const input = ref('')
const sending = ref(false)
const scroller = ref(null)
const inputEl = ref(null)

function newSessionId() {
  return globalThis.crypto?.randomUUID?.() ?? `s-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

function restore() {
  try {
    const saved = JSON.parse(sessionStorage.getItem(STORE_KEY) || 'null')
    if (saved && Array.isArray(saved.messages) && typeof saved.sessionId === 'string') return saved
  } catch {
    /* 隐私模式等情况下读不到存储，忽略 */
  }
  return { sessionId: newSessionId(), messages: [] }
}

const saved = restore()
const sessionId = ref(saved.sessionId)
// 每条：{ role: 'user' | 'assistant', content, cards?, fallback?, error? }
const messages = ref(saved.messages)

watch(
  messages,
  (v) => {
    try {
      sessionStorage.setItem(STORE_KEY, JSON.stringify({ sessionId: sessionId.value, messages: v.slice(-40) }))
    } catch {
      /* 存不进去不影响使用 */
    }
  },
  { deep: true },
)

// 换页面时（点了助手里的链接），手机上自动收起面板
watch(
  () => route.fullPath,
  () => {
    if (window.matchMedia('(max-width: 639px)').matches) open.value = false
  },
)

async function scrollToBottom() {
  await nextTick()
  if (scroller.value) scroller.value.scrollTop = scroller.value.scrollHeight
}

async function toggle() {
  open.value = !open.value
  if (open.value) {
    await scrollToBottom()
    inputEl.value?.focus()
  }
}

/** 把回复拆成 [{text}|{text, to}]，只有站内路径会变成链接 */
function segments(text) {
  const out = []
  let last = 0
  for (const m of text.matchAll(LINK_RE)) {
    if (m.index > last) out.push({ text: text.slice(last, m.index) })
    out.push({ text: m[1], to: m[2] })
    last = m.index + m[0].length
  }
  if (last < text.length) out.push({ text: text.slice(last) })
  // 模型偶尔还是会输出 **加粗**，去掉星号
  return out.map((s) => ({ ...s, text: s.text.replace(/\*\*/g, '') }))
}

async function send(text = input.value) {
  const q = text.trim()
  if (!q || sending.value) return
  if (q.length > 300) return
  input.value = ''
  messages.value.push({ role: 'user', content: q })
  sending.value = true
  await scrollToBottom()

  // 出错的提示不发给后端；只带最近 12 条
  const history = messages.value
    .filter((m) => !m.error)
    .slice(-12)
    .map((m) => ({ role: m.role, content: m.content.slice(0, 2000) }))
  // 后端要求第一条之后可以任意，但最后一条必须是用户提问（上面刚 push 的就是）
  try {
    const res = await assistantApi.chat(sessionId.value, history)
    messages.value.push({ role: 'assistant', content: res.reply, cards: res.cards, fallback: res.fallback })
  } catch (e) {
    messages.value.push({
      role: 'assistant',
      content: e.code === 42981 ? '提问太频繁了，休息一下再来吧。' : '网络开小差了，请稍后再试。',
      error: true,
    })
  } finally {
    sending.value = false
    await scrollToBottom()
    inputEl.value?.focus()
  }
}

function onKeydown(e) {
  // 回车发送；Shift+回车换行；中文输入法选词时的回车不算
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
    e.preventDefault()
    send()
  }
}

function reset() {
  messages.value = []
  sessionId.value = newSessionId()
}
</script>

<template>
  <!-- 悬浮按钮 -->
  <button
    type="button"
    class="fixed bottom-5 right-5 z-40 flex h-12 items-center gap-2 rounded-full bg-signal pl-4 pr-5 text-sm font-medium text-white shadow-lg shadow-signal/25 transition hover:brightness-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal focus-visible:ring-offset-2"
    :class="open ? 'max-sm:hidden' : ''"
    :aria-expanded="open"
    aria-controls="assistant-panel"
    @click="toggle"
  >
    <X v-if="open" class="size-5" />
    <Sparkles v-else class="size-5" />
    {{ open ? '收起' : '问小航' }}
  </button>

  <!-- 聊天面板 -->
  <Transition
    enter-from-class="opacity-0 translate-y-3"
    enter-active-class="transition duration-200 ease-out"
    leave-to-class="opacity-0 translate-y-3"
    leave-active-class="transition duration-150 ease-in"
  >
    <section
      v-if="open"
      id="assistant-panel"
      role="dialog"
      aria-label="AI 助手小航"
      class="fixed inset-0 z-50 flex flex-col bg-sail sm:inset-auto sm:bottom-20 sm:right-5 sm:h-[min(600px,calc(100vh-7rem))] sm:w-[380px] sm:overflow-hidden sm:rounded-2xl sm:border sm:shadow-2xl"
    >
      <!-- 标题栏 -->
      <header class="flex items-center gap-3 bg-ocean px-4 py-3 text-white">
        <span class="flex size-9 shrink-0 items-center justify-center rounded-full bg-white/15"><Sparkles class="size-5" /></span>
        <div class="min-w-0 flex-1">
          <p class="font-display text-lg leading-tight tracking-wide">小航 · 网站助手</p>
          <p class="truncate text-xs text-white/70">帮你找闲置、社团、活动和功能入口</p>
        </div>
        <button
          v-if="messages.length"
          type="button"
          class="rounded-md p-1.5 text-white/80 hover:bg-white/10 hover:text-white"
          title="清空对话"
          aria-label="清空对话"
          @click="reset"
        >
          <RotateCcw class="size-4" />
        </button>
        <button type="button" class="rounded-md p-1.5 text-white/80 hover:bg-white/10 hover:text-white" aria-label="关闭" @click="open = false">
          <X class="size-5" />
        </button>
      </header>

      <!-- 消息区 -->
      <div ref="scroller" class="flex-1 space-y-4 overflow-y-auto px-4 py-4" aria-live="polite">
        <!-- 欢迎语 + 示例问题 -->
        <div class="rounded-2xl rounded-tl-sm border bg-white px-3.5 py-3 text-sm leading-relaxed text-ocean">
          你好，我是小航。可以直接问我「有没有便宜的自行车」「最近有什么讲座」，或者「怎么加入社团」。
          <div class="mt-3 flex flex-wrap gap-2">
            <button
              v-for="s in SUGGESTIONS"
              :key="s"
              type="button"
              class="rounded-full border border-signal/30 bg-signal/5 px-3 py-1 text-xs text-signal hover:bg-signal/10 disabled:opacity-50"
              :disabled="sending"
              @click="send(s)"
            >
              {{ s }}
            </button>
          </div>
        </div>

        <template v-for="(m, i) in messages" :key="i">
          <div v-if="m.role === 'user'" class="flex justify-end">
            <p class="max-w-[85%] whitespace-pre-line break-words rounded-2xl rounded-tr-sm bg-signal px-3.5 py-2.5 text-sm text-white">{{ m.content }}</p>
          </div>

          <div v-else class="max-w-[92%] space-y-2">
            <p
              class="whitespace-pre-line break-words rounded-2xl rounded-tl-sm border bg-white px-3.5 py-2.5 text-sm leading-relaxed"
              :class="m.error ? 'border-destructive/30 text-destructive' : 'text-ocean'"
            ><template v-for="(s, j) in segments(m.content)" :key="j"><router-link v-if="s.to" :to="s.to" class="font-medium text-signal underline-offset-2 hover:underline">{{ s.text }}</router-link><template v-else>{{ s.text }}</template></template></p>
            <p v-if="m.fallback && m.cards?.length" class="px-1 text-xs text-muted-foreground">AI 暂时不可用，以上是关键词搜索的结果</p>

            <!-- 结果卡片 -->
            <ul v-if="m.cards?.length" class="space-y-1.5">
              <li v-for="c in m.cards" :key="`${c.type}-${c.id}`">
                <router-link :to="c.link" class="flex items-center gap-3 rounded-xl border bg-white p-2 transition hover:border-signal/40 hover:shadow-sm">
                  <!-- 文字垫底，图片盖在上面；图片加载失败就隐藏，露出文字（与 ItemCard 的做法一致） -->
                  <span class="relative flex size-12 shrink-0 items-center justify-center overflow-hidden rounded-lg bg-sail text-xs text-muted-foreground">
                    {{ TYPE_NAMES[c.type] }}
                    <img
                      v-if="c.cover"
                      :src="c.cover"
                      alt=""
                      class="absolute inset-0 size-full object-cover"
                      loading="lazy"
                      @error="(e) => (e.target.style.display = 'none')"
                    />
                  </span>
                  <span class="min-w-0 flex-1">
                    <span class="block truncate text-sm font-medium text-ocean">{{ c.title }}</span>
                    <span class="block truncate text-xs text-muted-foreground">{{ c.subtitle }}</span>
                  </span>
                  <span class="shrink-0 rounded bg-sail px-1.5 py-0.5 text-[11px] text-muted-foreground">{{ TYPE_NAMES[c.type] }}</span>
                </router-link>
              </li>
            </ul>
          </div>
        </template>

        <div v-if="sending" class="flex w-fit items-center gap-2 rounded-2xl rounded-tl-sm border bg-white px-3.5 py-2.5 text-sm text-muted-foreground">
          <Loader2 class="size-4 animate-spin" />小航正在查找…
        </div>
      </div>

      <!-- 输入框 -->
      <form class="flex items-end gap-2 border-t bg-white p-3" @submit.prevent="send()">
        <textarea
          ref="inputEl"
          v-model="input"
          rows="1"
          maxlength="300"
          placeholder="想找什么？例如：二手自行车"
          aria-label="输入问题"
          class="max-h-28 min-h-10 flex-1 resize-none rounded-xl border bg-sail px-3 py-2 text-sm text-ocean outline-none placeholder:text-muted-foreground focus:border-signal focus:ring-2 focus:ring-signal/20"
          @keydown="onKeydown"
        />
        <button
          type="submit"
          class="flex size-10 shrink-0 items-center justify-center rounded-xl bg-signal text-white transition hover:brightness-110 disabled:opacity-40"
          :disabled="sending || !input.trim()"
          aria-label="发送"
        >
          <ArrowUp class="size-5" />
        </button>
      </form>
      <p class="bg-white pb-2 text-center text-[11px] text-muted-foreground">AI 回答仅供参考，以页面实际信息为准</p>
    </section>
  </Transition>
</template>
