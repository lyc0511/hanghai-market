<!-- 物品详情：左侧大图 + 缩略图，右侧价格、信息、卖家和操作按钮；手机上上下排列 -->
<script setup>
import { Check, Eye, ImageOff, Loader2, MapPin, Pencil } from '@lucide/vue'
import { AnimatePresence, motion } from 'motion-v'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'

import { intentApi, itemApi } from '@/api'
import PageHeader from '@/components/PageHeader.vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Skeleton } from '@/components/ui/skeleton'
import { Textarea } from '@/components/ui/textarea'
import { confirm } from '@/composables/confirm'
import { formatDate } from '@/lib/time'
import { useMetaStore } from '@/stores/meta'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const user = useUserStore()
const meta = useMetaStore()

const item = ref(null)
const notFound = ref(false)
const current = ref(0) // 当前大图下标
const intentOpen = ref(false)
const message = ref('')
const sending = ref(false)
const sent = ref(false) // 本次已发起意向：按钮变成「已发起」

const discount = computed(() => {
  const it = item.value
  if (!it?.original_price || it.original_price <= it.price) return null
  return Math.round((it.price / it.original_price) * 100) / 10 // 例如 3.5 折
})

async function load() {
  try {
    item.value = await itemApi.detail(route.params.id)
    notFound.value = false
  } catch {
    notFound.value = true
  }
}

onMounted(() => {
  meta.load().catch(() => {})
  load()
})

// 在本页登录 / 退出后，「是不是我的物品」等信息会变，重新加载一次
watch(
  () => user.profile?.id ?? null,
  (now, before) => {
    if (now !== before) {
      sent.value = false
      load()
    }
  },
)

function onWant() {
  // 未登录：直接弹出右上角的登录窗口，登录后留在当前页面
  if (!user.isLoggedIn) {
    user.openLogin()
    return
  }
  intentOpen.value = true
}

async function sendIntent() {
  sending.value = true
  try {
    await intentApi.create(item.value.id, message.value.trim())
    intentOpen.value = false
    message.value = ''
    sent.value = true
    toast.success('已告诉卖家，等对方回复', { description: '可以在「我的意向」里查看进度' })
  } catch (e) {
    // 没填微信号时，引导去个人中心填写
    if (e.code === 42202) {
      intentOpen.value = false
      if (await confirm({ title: '还没有填写微信号', message: '卖家接受后需要互相添加微信，现在去填写吗？', confirmText: '去填写' })) {
        router.push({ name: 'me' })
      }
    }
  } finally {
    sending.value = false
  }
}

// 卖家本人：下架 / 重新上架
async function ownerAct(name) {
  const isOff = name === 'offline'
  const ok = await confirm(
    isOff
      ? { title: '下架物品', message: '下架后其他同学将看不到这件物品，进行中的交易意向会自动关闭。', confirmText: '下架' }
      : { title: '重新上架', message: '重新上架需要管理员再次审核。', confirmText: '提交审核' },
  )
  if (!ok) return
  try {
    item.value = await (isOff ? itemApi.offline : itemApi.relist)(item.value.id)
    toast.success(isOff ? '已下架' : '已提交审核')
  } catch {
    /* 提示已由 http.js 弹出 */
  }
}
</script>

<template>
  <div class="container">
    <PageHeader title="物品详情" />

    <div v-if="notFound" class="py-24 text-center">
      <p class="font-display text-2xl text-ocean">这件物品不存在或已下架</p>
      <Button class="mt-6" @click="router.push({ name: 'market' })">去二手市场看看</Button>
    </div>

    <div v-else-if="!item" class="grid gap-10 md:grid-cols-2">
      <Skeleton class="aspect-square rounded-xl" />
      <div class="space-y-4"><Skeleton class="h-8 w-3/4" /><Skeleton class="h-16" /><Skeleton class="h-32" /></div>
    </div>

    <template v-else>
      <section class="grid gap-8 md:grid-cols-2 lg:gap-12">
        <!-- 左：图片 -->
        <div>
          <div class="relative aspect-square overflow-hidden rounded-xl border bg-secondary">
            <img
              v-if="item.images[current]"
              :key="current"
              :src="item.images[current]"
              :alt="item.title"
              class="relative z-10 size-full object-contain"
              @error="(e) => (e.target.style.display = 'none')"
            />
            <ImageOff class="absolute inset-0 m-auto size-12 text-ocean/20" aria-hidden="true" />
          </div>
          <div v-if="item.images.length > 1" class="mt-3 flex flex-wrap gap-2">
            <button
              v-for="(src, i) in item.images"
              :key="i"
              type="button"
              class="size-16 overflow-hidden rounded-md border-2 bg-secondary transition-colors"
              :class="i === current ? 'border-signal' : 'border-transparent hover:border-fog'"
              :aria-label="`第 ${i + 1} 张图`"
              @click="current = i"
            >
              <img :src="src" alt="" class="size-full object-cover" />
            </button>
          </div>
        </div>

        <!-- 右：信息与操作 -->
        <div class="flex flex-col">
          <div
            v-if="item.status !== 'online'"
            class="mb-4 rounded-lg px-4 py-3 text-sm"
            :class="item.status === 'rejected' ? 'bg-destructive/10 text-destructive' : 'bg-buoy/10 text-[#B44A10]'"
          >
            <template v-if="item.status === 'rejected'">未通过审核：{{ item.reject_reason }}</template>
            <template v-else>当前状态：{{ item.sold_at ? '已售出' : meta.label('content_status', item.status) }}，只有你自己能看到</template>
          </div>

          <h1 class="text-2xl font-semibold leading-snug text-ocean">{{ item.title }}</h1>

          <div class="mt-4 flex items-baseline gap-3">
            <span v-if="item.price === 0" class="font-display text-4xl text-kelp">免费送</span>
            <span v-else class="font-display text-5xl tabular-nums text-buoy">¥{{ item.price }}</span>
            <span v-if="item.original_price" class="text-muted-foreground line-through">原价 ¥{{ item.original_price }}</span>
            <Badge v-if="discount" class="bg-buoy text-white">{{ discount }} 折</Badge>
          </div>

          <dl class="mt-6 grid grid-cols-2 gap-x-6 gap-y-4 border-y py-5 text-sm">
            <div><dt class="text-muted-foreground">成色</dt><dd class="mt-0.5 font-medium">{{ meta.label('item_condition', item.condition) }}</dd></div>
            <div><dt class="text-muted-foreground">分类</dt><dd class="mt-0.5 font-medium">{{ item.category?.name ?? '未分类' }}</dd></div>
            <div><dt class="flex items-center gap-1 text-muted-foreground"><MapPin class="size-3.5" />交易校区</dt><dd class="mt-0.5 font-medium">{{ item.campus_area ?? '未填写' }}</dd></div>
            <div><dt class="flex items-center gap-1 text-muted-foreground"><Eye class="size-3.5" />浏览</dt><dd class="mt-0.5 font-medium tabular-nums">{{ item.view_count }}</dd></div>
          </dl>

          <div v-if="item.tags.length" class="mt-4 flex flex-wrap gap-1.5">
            <Badge v-for="t in item.tags" :key="t" variant="secondary">{{ t }}</Badge>
          </div>

          <div class="mt-6 flex items-center gap-3">
            <span class="grid size-11 place-items-center rounded-full bg-ocean text-lg font-semibold text-white">{{ item.seller.nickname.slice(0, 1) }}</span>
            <div>
              <div class="font-medium">{{ item.seller.nickname }}</div>
              <div class="text-sm text-muted-foreground">{{ item.seller.campus_area ?? '校内同学' }}，{{ formatDate(item.created_at) }} 发布</div>
            </div>
          </div>

          <div class="mt-auto flex gap-3 pt-8">
            <template v-if="item.is_mine">
              <Button v-if="item.sold_at" size="lg" disabled>已售出</Button>
              <template v-else>
                <Button size="lg" variant="outline" @click="router.push({ name: 'item-edit', params: { id: item.id } })"><Pencil />编辑</Button>
                <Button v-if="item.status !== 'offline'" size="lg" variant="outline" @click="ownerAct('offline')">下架</Button>
                <Button v-else size="lg" @click="ownerAct('relist')">重新上架</Button>
              </template>
            </template>
            <Button v-else-if="item.status !== 'online'" size="lg" disabled>暂不可交易</Button>
            <!-- 「我想要」→「已发起」：图标和文字切换，给用户明确的反馈 -->
            <Button v-else size="lg" class="h-11 min-w-44 text-base" :variant="sent ? 'secondary' : 'default'" :disabled="sent" @click="onWant">
              <AnimatePresence mode="wait" :initial="false">
                <motion.span v-if="sent" key="sent" class="flex items-center gap-1.5" :initial="{ y: 8, opacity: 0 }" :animate="{ y: 0, opacity: 1 }">
                  <Check class="size-4" />已发起意向
                </motion.span>
                <motion.span v-else key="want" :exit="{ y: -8, opacity: 0 }">我想要</motion.span>
              </AnimatePresence>
            </Button>
          </div>
          <p v-if="!item.is_mine && item.status === 'online'" class="mt-3 text-xs text-muted-foreground">
            卖家同意后，你们能看到对方的微信号并约定面交。
          </p>
        </div>
      </section>

      <section v-if="item.summary" class="mt-12 max-w-3xl">
        <h2 class="font-display text-2xl text-ocean">物品描述</h2>
        <p class="mt-3 whitespace-pre-wrap leading-loose text-muted-foreground">{{ item.summary }}</p>
      </section>
    </template>

    <Dialog v-model:open="intentOpen">
      <DialogContent class="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>给卖家留句话</DialogTitle>
          <DialogDescription>卖家会收到通知，同意后你们可以互相看到微信号。</DialogDescription>
        </DialogHeader>
        <Textarea v-model="message" rows="3" maxlength="200" placeholder="例如：还在吗？今晚可以在图书馆门口面交" />
        <DialogFooter>
          <Button variant="outline" @click="intentOpen = false">取消</Button>
          <Button :disabled="sending" @click="sendIntent"><Loader2 v-if="sending" class="animate-spin" />发起意向</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>
