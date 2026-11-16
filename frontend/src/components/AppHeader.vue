<!--
  全站顶部导航：左侧 logo + 板块导航，中间搜索，右上角登录 / 用户菜单。
  手机宽度下，导航和搜索收进左侧抽屉菜单。
-->
<script setup>
import { Bell, ChevronDown, LogOut, Menu, Package, PenLine, Plus, Search, Settings, ShoppingBag, User, Users } from '@lucide/vue'
import { ref, watch } from 'vue'
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
import { Sheet, SheetContent, SheetTitle } from '@/components/ui/sheet'
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
  { to: '/', label: '首页', exact: true },
  { to: '/market', label: '二手' },
  { to: '/clubs', label: '社团' },
  { to: '/activities', label: '活动' },
  { to: '/wall', label: '墙' },
]

const keyword = ref('')
const drawer = ref(false)

function isActive(n) {
  return n.exact ? route.path === n.to : route.path.startsWith(n.to)
}

function onSearch() {
  drawer.value = false
  const k = keyword.value.trim()
  router.push({ name: 'market', query: k ? { keyword: k } : {} })
}

function onPublish() {
  drawer.value = false
  if (user.isLoggedIn) router.push({ name: 'publish' })
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
  <header class="sticky top-0 z-40 border-b bg-white/90 backdrop-blur supports-[backdrop-filter]:bg-white/75">
    <div class="container flex h-16 items-center gap-6">
      <Button variant="ghost" size="icon" class="-ml-2 md:hidden" aria-label="打开菜单" @click="drawer = true">
        <Menu class="size-5" />
      </Button>

      <router-link to="/" class="shrink-0 font-display text-2xl tracking-wide text-ocean">航海集市</router-link>

      <nav class="hidden items-center gap-1 md:flex" aria-label="主导航">
        <router-link
          v-for="n in NAV"
          :key="n.to"
          :to="n.to"
          class="relative px-3 py-2 text-[15px] transition-colors"
          :class="isActive(n) ? 'font-semibold text-ocean' : 'text-muted-foreground hover:text-ocean'"
        >
          {{ n.label }}
          <!-- 当前板块：浮标橙下划线 -->
          <span v-if="isActive(n)" class="absolute inset-x-3 -bottom-[13px] h-0.5 rounded-full bg-buoy" />
        </router-link>
      </nav>

      <form class="relative ml-auto hidden w-64 lg:block" role="search" @submit.prevent="onSearch">
        <Search class="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input v-model="keyword" placeholder="搜闲置物品" class="h-9 rounded-full bg-sail pl-9" aria-label="搜索闲置物品" />
      </form>

      <div class="ml-auto flex items-center gap-2 lg:ml-0">
        <Button class="hidden md:inline-flex" @click="onPublish"><Plus />发布闲置</Button>

        <router-link
          v-if="user.isLoggedIn"
          to="/notifications"
          class="relative grid size-9 place-items-center rounded-full text-muted-foreground transition-colors hover:bg-muted hover:text-ocean"
          :aria-label="notices.unread ? `通知，${notices.unread} 条未读` : '通知'"
        >
          <Bell class="size-5" />
          <span
            v-if="notices.unread"
            class="absolute -right-0.5 -top-0.5 grid h-[18px] min-w-[18px] place-items-center rounded-full bg-buoy px-1 text-[11px] font-semibold leading-none text-white ring-2 ring-white"
          >
            {{ notices.unread > 99 ? '99+' : notices.unread }}
          </span>
        </router-link>

        <DropdownMenu v-if="user.isLoggedIn">
          <DropdownMenuTrigger as-child>
            <button type="button" class="flex items-center gap-2 rounded-full py-1 pl-1 pr-2 transition-colors hover:bg-muted">
              <span class="grid size-8 place-items-center rounded-full bg-ocean font-semibold text-white">
                {{ user.profile?.nickname?.slice(0, 1) ?? '我' }}
              </span>
              <span class="hidden max-w-24 truncate text-sm sm:inline">{{ user.profile?.nickname }}</span>
              <ChevronDown class="size-4 text-muted-foreground" />
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
            <DropdownMenuItem @select="go('my-posts')"><PenLine />我的投稿</DropdownMenuItem>
            <DropdownMenuItem @select="go('my-clubs')"><Users />我的社团</DropdownMenuItem>
            <DropdownMenuItem @select="go('my-intents')"><ShoppingBag />我的意向</DropdownMenuItem>
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
          <Button variant="ghost" class="hidden sm:inline-flex" @click="user.openLogin('register')">注册</Button>
          <Button variant="outline" @click="user.openLogin('login')">登录</Button>
        </template>
      </div>
    </div>
  </header>

  <!-- 手机端：抽屉菜单 -->
  <Sheet v-model:open="drawer">
    <SheetContent side="left" class="w-72 p-6">
      <SheetTitle class="font-display text-2xl font-normal text-ocean">航海集市</SheetTitle>
      <form class="relative mt-6" role="search" @submit.prevent="onSearch">
        <Search class="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input v-model="keyword" placeholder="搜闲置物品" class="h-10 rounded-full pl-9" />
      </form>
      <nav class="mt-4 flex flex-col">
        <router-link
          v-for="n in NAV"
          :key="n.to"
          :to="n.to"
          class="rounded-lg px-3 py-2.5 text-base"
          :class="isActive(n) ? 'bg-secondary font-semibold text-ocean' : 'text-muted-foreground'"
          @click="drawer = false"
        >
          {{ n.label }}
        </router-link>
      </nav>
      <Button class="mt-4 w-full" @click="onPublish"><Plus />发布闲置</Button>
    </SheetContent>
  </Sheet>

  <!-- 右上角登录弹窗：任何页面调用 user.openLogin() 都会打开它 -->
  <Dialog v-model:open="user.loginVisible">
    <DialogContent class="sm:max-w-sm">
      <DialogTitle class="sr-only">登录或注册</DialogTitle>
      <DialogDescription class="sr-only">使用学号和密码登录航海集市</DialogDescription>
      <LoginForm :key="user.loginMode" :initial-mode="user.loginMode" @success="user.loginVisible = false" />
    </DialogContent>
  </Dialog>
</template>
