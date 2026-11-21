<!--
  全站顶部导航：左侧港口标识 + 带图标的主导航，内页提供快捷搜索，右上角统一发布入口、通知与用户菜单。
  手机端主导航由 SiteLayout 底部栏承载，顶部保持轻盈不拥挤。
-->
<script setup>
import {
  Bell,
  Calendar,
  CalendarCheck,
  ChevronDown,
  Compass,
  Flag,
  Home,
  LogOut,
  MessageSquare,
  Package,
  PenLine,
  Plus,
  Search,
  Settings,
  ShoppingBag,
  User,
  Users,
} from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import LoginForm from '@/components/LoginForm.vue'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogTitle } from '@/components/ui/dialog'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Input } from '@/components/ui/input'
import { useNotificationStore } from '@/stores/notifications'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const user = useUserStore()
const notices = useNotificationStore()

// 登录后开始轮询未读数，退出后停止；换页时顺手刷新一次
watch(
  () => user.isLoggedIn,
  (v) => (v ? notices.start() : notices.stop()),
  { immediate: true },
)
watch(
  () => route.fullPath,
  () => user.isLoggedIn && notices.refresh(),
)

const NAV = [
  { to: '/', label: '首页', icon: Home, exact: true },
  { to: '/market', label: '二手市场', icon: ShoppingBag, sticker: 'bg-[#E4F2F8] text-[#176B98]' },
  { to: '/clubs', label: '社团', icon: Users, sticker: 'bg-[#E2F3F3] text-[#277C8A]' },
  { to: '/activities', label: '活动', icon: Calendar, sticker: 'bg-[#E8F0FA] text-[#466EAA]' },
  { to: '/wall', label: '校园墙', icon: MessageSquare, sticker: 'bg-[#E9F3F8] text-[#356F91]' },
]

const keyword = ref('')
const isHome = computed(() => route.name === 'home')
// 首页首屏已有大搜索框，顶部不再重复显示
const showTopSearch = computed(() => route.name !== 'home')

function isActive(n) {
  return n.exact ? route.path === n.to : route.path.startsWith(n.to)
}

function onSearch() {
  const k = keyword.value.trim()
  router.push({ name: 'market', query: k ? { keyword: k } : {} })
}

function goAuthRoute(name) {
  if (user.isLoggedIn) router.push({ name })
  else user.openLogin()
}

function go(name) {
  router.push({ name })
}

function logout() {
  user.logout()
  if (route.meta.auth) router.replace('/')
}
</script>

<template>
  <header
    class="sticky top-0 z-40 border-b bg-white/92 backdrop-blur supports-[backdrop-filter]:bg-white/80"
    :class="isHome ? 'border-[#DCEAF1] bg-white supports-[backdrop-filter]:bg-white' : ''"
  >
    <div class="container flex h-16 items-center gap-4" :class="isHome ? 'md:h-20 lg:h-[100px] lg:gap-8' : ''">
      <router-link to="/" class="group flex shrink-0 items-center gap-2.5">
        <span v-if="!isHome" class="grid size-8 place-items-center rounded-lg bg-ocean text-white transition-transform group-hover:rotate-12">
          <Compass class="size-4.5" />
        </span>
        <span v-else class="text-2xl font-bold leading-none text-[#176B98]" aria-hidden="true">≋</span>
        <span class="font-display text-2xl tracking-wide text-ocean" :class="isHome ? '!font-sans !text-[22px] !font-bold !tracking-normal !text-[#176B98] md:!text-[23px]' : ''">航海集市</span>
      </router-link>

      <nav class="hidden items-center gap-0.5 lg:gap-1 md:flex" aria-label="主导航">
        <router-link
          v-for="n in NAV"
          :key="n.to"
          :to="n.to"
          class="relative flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-lg px-2 py-2 text-sm transition-colors lg:px-2.5"
          :class="isHome
            ? n.exact
              ? 'font-semibold text-[#176B98]'
              : 'border border-[#D5E7EE] bg-white text-[#0E2A47] shadow-[0_1px_3px_rgba(14,42,71,0.04)] hover:border-[#91BFD2] hover:bg-[#F2F9FC]'
            : isActive(n) ? 'bg-ocean/[0.07] font-semibold text-ocean' : 'text-muted-foreground hover:bg-muted/70 hover:text-ocean'"
        >
          <component :is="n.icon" v-if="!isHome" class="size-4" :class="isActive(n) ? 'text-buoy' : 'opacity-75'" />
          <span v-else-if="!n.exact" class="hidden size-7 shrink-0 place-items-center rounded-md lg:grid" :class="n.sticker">
            <component :is="n.icon" class="size-4" aria-hidden="true" />
          </span>
          <span>{{ isHome && n.to === '/clubs' ? '社团招新' : isHome && n.to === '/activities' ? '校园活动' : n.label }}</span>
          <span v-if="isActive(n) && !isHome" class="absolute inset-x-3 -bottom-[11px] h-0.5 rounded-full bg-buoy" />
        </router-link>
      </nav>

      <form v-if="showTopSearch" class="relative ml-auto hidden w-56 xl:block" role="search" @submit.prevent="onSearch">
        <Search class="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input v-model="keyword" placeholder="搜闲置物品" class="h-9 rounded-full bg-sail pl-9 text-sm" aria-label="搜索闲置物品" />
      </form>

      <div class="ml-auto flex items-center gap-2" :class="showTopSearch ? 'xl:ml-0' : ''">
        <!-- 统一发布入口：二手闲置 + 校园墙投稿 -->
        <DropdownMenu>
          <DropdownMenuTrigger as-child>
            <Button size="sm" class="gap-1.5 rounded-full px-3.5" :class="isHome ? 'max-md:hidden rounded-md bg-[#E7F2F7] text-[#176B98] hover:bg-[#D8EAF2]' : ''">
              <Plus class="size-4" />
              <span>发布</span>
              <ChevronDown class="size-3.5 opacity-80" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" class="w-44">
            <DropdownMenuItem @select="goAuthRoute('publish')">
              <Package />发布二手闲置
            </DropdownMenuItem>
            <DropdownMenuItem @select="goAuthRoute('wall-new')">
              <PenLine />校园墙匿名投稿
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        <router-link
          v-if="user.isLoggedIn"
          to="/notifications"
          class="relative grid size-9 place-items-center rounded-full text-muted-foreground transition-colors hover:bg-muted hover:text-ocean"
          :class="isHome ? '!w-auto !rounded-none !text-[#0E2A47] hover:!bg-transparent hover:!text-[#176B98]' : ''"
          :aria-label="notices.unread ? `通知，${notices.unread} 条未读` : '通知'"
        >
          <Bell v-if="!isHome" class="size-5" />
          <span v-else class="whitespace-nowrap text-[13px]">通知 <span v-if="notices.unread" class="text-[#176B98]">({{ notices.unread }})</span></span>
          <span
            v-if="notices.unread && !isHome"
            class="absolute -right-0.5 -top-0.5 grid h-[18px] min-w-[18px] place-items-center rounded-full bg-buoy px-1 text-[11px] font-semibold leading-none text-white ring-2 ring-white"
          >
            {{ notices.unread > 99 ? '99+' : notices.unread }}
          </span>
        </router-link>

        <DropdownMenu v-if="user.isLoggedIn">
          <DropdownMenuTrigger as-child>
            <button type="button" class="flex items-center gap-2 rounded-full py-1 pl-1 pr-2 transition-colors hover:bg-muted" :class="isHome ? 'max-md:hidden' : ''">
              <span v-if="!isHome" class="grid size-8 place-items-center rounded-full bg-ocean text-sm font-semibold text-white">
                {{ user.profile?.nickname?.slice(0, 1) ?? '我' }}
              </span>
              <span v-if="isHome" class="text-[13px] text-[#0E2A47]">我的</span>
              <span v-else class="hidden max-w-24 truncate text-sm sm:inline">{{ user.profile?.nickname }}</span>
              <ChevronDown v-if="!isHome" class="size-4 text-muted-foreground" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" class="w-48">
            <DropdownMenuLabel class="font-normal">
              <div class="font-medium">{{ user.profile?.nickname }}</div>
              <div class="text-xs text-muted-foreground">学号 {{ user.profile?.student_no }}</div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem @select="go('me')"><User />个人中心</DropdownMenuItem>
            <DropdownMenuItem @select="go('my-items')"><Package />我发布的</DropdownMenuItem>
            <DropdownMenuItem @select="go('my-intents')"><ShoppingBag />我的意向</DropdownMenuItem>
            <DropdownMenuItem @select="go('my-clubs')"><Users />我的社团</DropdownMenuItem>
            <DropdownMenuItem @select="go('my-activities')"><CalendarCheck />我报名的活动</DropdownMenuItem>
            <DropdownMenuItem @select="go('my-posts')"><PenLine />我的投稿</DropdownMenuItem>
            <DropdownMenuItem @select="go('my-reports')"><Flag />我的举报</DropdownMenuItem>
            <DropdownMenuItem @select="go('notifications')"><Bell />消息通知</DropdownMenuItem>
            <template v-if="user.isAdmin">
              <DropdownMenuSeparator />
              <DropdownMenuItem @select="go('admin-dashboard')"><Settings />管理后台</DropdownMenuItem>
            </template>
            <DropdownMenuSeparator />
            <DropdownMenuItem @select="logout"><LogOut />退出登录</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        <template v-else>
          <Button variant="ghost" size="sm" class="hidden sm:inline-flex" @click="user.openLogin('register')">注册</Button>
          <Button variant="outline" size="sm" @click="user.openLogin('login')">登录</Button>
        </template>
      </div>
    </div>
  </header>

  <!-- 右上角登录弹窗：任何页面调用 user.openLogin() 都会打开它 -->
  <Dialog v-model:open="user.loginVisible">
    <DialogContent class="sm:max-w-sm">
      <DialogTitle class="sr-only">登录或注册</DialogTitle>
      <DialogDescription class="sr-only">使用学号和密码登录航海集市</DialogDescription>
      <LoginForm :key="user.loginMode" :initial-mode="user.loginMode" @success="user.loginVisible = false" />
    </DialogContent>
  </Dialog>
</template>
