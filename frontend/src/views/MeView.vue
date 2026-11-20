<!-- 个人中心：基本信息、昵称和校区、微信号设置、常用入口 -->
<script setup>
import { Bell, CalendarDays, ChevronRight, Flag, Loader2, LogOut, Package, PenLine, Settings, ShieldCheck, ShoppingBag, Store, Users } from '@lucide/vue'
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'

import { authApi } from '@/api'
import PageHeader from '@/components/PageHeader.vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { confirm } from '@/composables/confirm'
import { useMetaStore } from '@/stores/meta'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const user = useUserStore()
const meta = useMetaStore()
onMounted(() => meta.load().catch(() => {}))

// 修改昵称和校区
const profileOpen = ref(false)
const profileForm = reactive({ nickname: '', campus: '' })
const profileSaving = ref(false)

function openProfile() {
  profileForm.nickname = user.profile?.nickname ?? ''
  profileForm.campus = user.profile?.campus_area ?? ''
  profileOpen.value = true
}

async function saveProfile() {
  const nickname = profileForm.nickname.trim()
  if (!nickname) return toast.error('昵称不能为空')
  profileSaving.value = true
  try {
    const body = { nickname }
    if (profileForm.campus) body.campus_area = profileForm.campus
    user.profile = await authApi.updateMe(body)
    profileOpen.value = false
    toast.success('资料已保存')
  } catch {
    /* 错误提示已由 http.js 弹出 */
  } finally {
    profileSaving.value = false
  }
}

const wechatOpen = ref(false)
const wechatInput = ref('')
const saving = ref(false)

const LINKS = [
  { to: { name: 'my-clubs' }, icon: Users, label: '我的社团' },
  { to: { name: 'my-activities' }, icon: CalendarDays, label: '我报名的活动' },
  { to: { name: 'my-items' }, icon: Package, label: '我发布的' },
  { to: { name: 'my-posts' }, icon: PenLine, label: '我的投稿' },
  { to: { name: 'my-intents', query: { role: 'buyer' } }, icon: ShoppingBag, label: '我想要的' },
  { to: { name: 'my-intents', query: { role: 'seller' } }, icon: Store, label: '找我买的' },
  { to: { name: 'notifications' }, icon: Bell, label: '消息通知' },
  { to: { name: 'my-reports' }, icon: Flag, label: '我的举报' },
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

const passwordOpen = ref(false)
const passwordSaving = ref(false)

async function savePassword(event) {
  if (passwordSaving.value) return
  const form = event.currentTarget
  const fields = new FormData(form)
  if (fields.get('new_password') !== fields.get('confirm_password')) return toast.error('两次输入的新密码不一致')
  passwordSaving.value = true
  try {
    await authApi.changePassword({ old_password: fields.get('old_password'), new_password: fields.get('new_password') })
    form.reset()
    passwordOpen.value = false
    user.logout()
    toast.success('密码已修改，请用新密码重新登录')
    await router.replace({ name: 'login' })
  } catch {
    /* 请求失败由统一拦截器提示 */
  } finally {
    passwordSaving.value = false
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

    <section class="mt-6 divide-y rounded-xl border bg-white">
      <button type="button" class="flex w-full items-center gap-3 px-4 py-4 text-left hover:bg-sail" @click="openProfile">
        <span class="flex-1">
          <span class="block font-medium text-ocean">昵称和校区</span>
          <span class="mt-0.5 block text-xs text-muted-foreground">学号不能改，昵称和校区随时可以改</span>
        </span>
        <span class="truncate text-sm text-ocean">{{ user.profile?.nickname }}，{{ user.profile?.campus_area ?? '未设置校区' }}</span>
        <ChevronRight class="size-4 shrink-0 text-muted-foreground" />
      </button>
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
      <router-link v-if="user.isAdmin" :to="{ name: 'admin-dashboard' }" class="flex items-center gap-3 px-4 py-3.5 hover:bg-sail">
        <Settings class="size-5 text-signal" />
        <span class="flex-1 text-ocean">管理后台</span>
        <span class="text-xs text-muted-foreground">建议在电脑上打开</span>
        <ChevronRight class="size-4 text-muted-foreground" />
      </router-link>
    </nav>

    <Button variant="outline" class="mt-6" @click="passwordOpen = true">修改密码</Button>
    <Button variant="ghost" class="mt-6 text-muted-foreground" @click="onLogout"><LogOut />退出登录</Button>

    <Dialog v-model:open="passwordOpen">
      <DialogContent class="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>修改密码</DialogTitle>
          <DialogDescription>保存后，所有设备都需要重新登录。</DialogDescription>
        </DialogHeader>
        <form class="space-y-3" @submit.prevent="savePassword">
          <Label for="old-password">当前密码</Label>
          <Input id="old-password" name="old_password" type="password" autocomplete="current-password" required />
          <Label for="new-password">新密码（8–32 位，含字母和数字）</Label>
          <Input id="new-password" name="new_password" type="password" autocomplete="new-password" minlength="8" maxlength="32" required />
          <Label for="confirm-password">确认新密码</Label>
          <Input id="confirm-password" name="confirm_password" type="password" autocomplete="new-password" maxlength="32" required />
          <DialogFooter><Button type="submit" :disabled="passwordSaving">保存新密码</Button></DialogFooter>
        </form>
      </DialogContent>
    </Dialog>

    <Dialog v-model:open="profileOpen">
      <DialogContent class="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>修改昵称和校区</DialogTitle>
          <DialogDescription>昵称会显示在你发布的物品、评论和社团成员列表里</DialogDescription>
        </DialogHeader>
        <div class="space-y-4">
          <div class="space-y-1.5">
            <Label for="me-nickname">昵称</Label>
            <Input id="me-nickname" v-model="profileForm.nickname" maxlength="30" class="h-10" @keyup.enter="saveProfile" />
          </div>
          <div class="space-y-1.5">
            <Label>校区</Label>
            <Select v-model="profileForm.campus">
              <SelectTrigger class="h-10 w-full"><SelectValue placeholder="选择校区" /></SelectTrigger>
              <SelectContent>
                <SelectItem v-for="c in meta.enums?.campus_area ?? []" :key="c" :value="c">{{ c }}</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" @click="profileOpen = false">取消</Button>
          <Button :disabled="profileSaving" @click="saveProfile"><Loader2 v-if="profileSaving" class="animate-spin" />保存</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

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
