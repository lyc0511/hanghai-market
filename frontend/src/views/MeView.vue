<!-- 个人中心：基本信息、微信号设置、常用入口 -->
<script setup>
import { ChevronRight, Loader2, LogOut, Package, Settings, ShieldCheck, ShoppingBag, Store } from '@lucide/vue'
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'

import { authApi } from '@/api'
import PageHeader from '@/components/PageHeader.vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { confirm } from '@/composables/confirm'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const user = useUserStore()

const wechatOpen = ref(false)
const wechatInput = ref('')
const saving = ref(false)

const LINKS = [
  { to: { name: 'my-items' }, icon: Package, label: '我发布的' },
  { to: { name: 'my-intents', query: { role: 'buyer' } }, icon: ShoppingBag, label: '我想要的' },
  { to: { name: 'my-intents', query: { role: 'seller' } }, icon: Store, label: '找我买的' },
]

function openWechat() {
  wechatInput.value = user.profile?.wechat_id ?? ''
  wechatOpen.value = true
}

async function saveWechat() {
  saving.value = true
  try {
    user.profile = await authApi.updateMe({ wechat_id: wechatInput.value.trim() })
    wechatOpen.value = false
    toast.success('微信号已保存')
  } catch {
    /* 格式错误等提示已由 http.js 弹出 */
  } finally {
    saving.value = false
  }
}

async function onLogout() {
  if (!(await confirm({ title: '退出登录', message: '确定要退出当前账号吗？', confirmText: '退出' }))) return
  user.logout()
  router.replace('/')
}
</script>

<template>
  <div class="container narrow">
    <PageHeader title="个人中心" />

    <section class="flex items-center gap-4 rounded-xl bg-ocean p-6 text-white">
      <span class="grid size-16 shrink-0 place-items-center rounded-full bg-white/15 font-display text-3xl">
        {{ user.profile?.nickname?.slice(0, 1) ?? '我' }}
      </span>
      <div class="min-w-0">
        <div class="flex items-center gap-2 text-xl font-semibold">
          <span class="truncate">{{ user.profile?.nickname }}</span>
          <Badge v-if="user.isAdmin" class="bg-buoy text-white">管理员</Badge>
        </div>
        <div class="mt-1 text-sm text-white/70">学号 {{ user.profile?.student_no }}，{{ user.profile?.campus_area ?? '未设置校区' }}</div>
      </div>
    </section>

    <section class="mt-6 rounded-xl border bg-white">
      <button type="button" class="flex w-full items-center gap-3 px-4 py-4 text-left hover:bg-sail" @click="openWechat">
        <span class="flex-1">
          <span class="block font-medium text-ocean">微信号</span>
          <span class="mt-0.5 flex items-center gap-1 text-xs text-muted-foreground">
            <ShieldCheck class="size-3.5" />加密保存，卖家接受交易意向后才会展示给对方
          </span>
        </span>
        <span v-if="user.profile?.wechat_id" class="text-sm text-ocean">{{ user.profile.wechat_id }}</span>
        <span v-else class="text-sm font-medium text-buoy">未填写，交易时需要</span>
        <ChevronRight class="size-4 text-muted-foreground" />
      </button>
    </section>

    <nav class="mt-4 divide-y rounded-xl border bg-white" aria-label="我的">
      <router-link v-for="l in LINKS" :key="l.label" :to="l.to" class="flex items-center gap-3 px-4 py-3.5 hover:bg-sail">
        <component :is="l.icon" class="size-5 text-signal" />
        <span class="flex-1 text-ocean">{{ l.label }}</span>
        <ChevronRight class="size-4 text-muted-foreground" />
      </router-link>
      <router-link v-if="user.isAdmin" :to="{ name: 'admin-items' }" class="flex items-center gap-3 px-4 py-3.5 hover:bg-sail">
        <Settings class="size-5 text-signal" />
        <span class="flex-1 text-ocean">管理后台</span>
        <span class="text-xs text-muted-foreground">建议在电脑上打开</span>
        <ChevronRight class="size-4 text-muted-foreground" />
      </router-link>
    </nav>

    <Button variant="ghost" class="mt-6 text-muted-foreground" @click="onLogout"><LogOut />退出登录</Button>

    <Dialog v-model:open="wechatOpen">
      <DialogContent class="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>设置微信号</DialogTitle>
          <DialogDescription>字母开头的微信号，或者 11 位手机号</DialogDescription>
        </DialogHeader>
        <Input v-model="wechatInput" maxlength="20" placeholder="例如 wx_lixiaoming" class="h-10" @keyup.enter="saveWechat" />
        <DialogFooter>
          <Button variant="outline" @click="wechatOpen = false">取消</Button>
          <Button :disabled="saving" @click="saveWechat"><Loader2 v-if="saving" class="animate-spin" />保存</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>
