<!-- 网站外壳：顶部导航 + 内容区 + 页脚 + 手机端底部主导航。除登录页和管理后台外，所有页面都在这里面 -->
<script setup>
import { Home, MessageSquare, Plus, ShoppingBag, UserRound } from '@lucide/vue'
import { useRoute, useRouter } from 'vue-router'

import AppHeader from '@/components/AppHeader.vue'
import AssistantWidget from '@/components/AssistantWidget.vue'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const user = useUserStore()

const MOBILE_NAV = [
  { to: '/', label: '首页', icon: Home, exact: true },
  { to: '/market', label: '二手', icon: ShoppingBag },
  { to: '/publish', label: '发布', icon: Plus, auth: true },
  { to: '/wall', label: '校园墙', icon: MessageSquare },
  { to: '/me', label: '我的', icon: UserRound, auth: true },
]

function isActive(n) {
  return n.exact ? route.path === n.to : route.path.startsWith(n.to)
}

function goMobile(n) {
  if (n.auth && !user.isLoggedIn) user.openLogin()
  else router.push(n.to)
}
</script>

<template>
  <div class="flex min-h-screen flex-col">
    <AppHeader />
    <main class="flex-1" :class="route.name === 'home' ? 'bg-[#F7FAFC] pb-16 md:pb-0' : 'pb-24 pt-6 md:pb-16 md:pt-8'">
      <router-view />
    </main>
    <footer
      class="border-t bg-white pb-20 pt-6 text-center text-xs text-muted-foreground md:pb-6"
      :class="route.name === 'home' ? '!border-0 !bg-[#F7FAFC] !text-[#607487]' : ''"
    >
      <div class="container" :class="route.name === 'home' ? 'md:text-left' : ''">
        {{ route.name === 'home' ? '航海集市 · 广州航海学院校园社区' : '航海集市：广州航海学院校内二手交易与社团活动平台（本科毕业设计）' }}
      </div>
    </footer>

    <!-- 手机端底部固定导航栏：五大板块一键直达 -->
    <nav
      class="fixed inset-x-0 bottom-0 z-40 grid h-16 grid-cols-5 border-t bg-white/95 backdrop-blur md:hidden"
      :class="route.name === 'home' ? '!border-[#DCEAF1] !bg-white' : ''"
      aria-label="底部主导航"
    >
      <button
        v-for="n in MOBILE_NAV"
        :key="n.to"
        type="button"
        @click="goMobile(n)"
        class="relative flex flex-col items-center justify-center gap-0.5 text-[11px] transition-colors"
        :class="route.name === 'home'
          ? isActive(n) ? 'font-semibold text-[#176B98]' : 'text-[#607487]'
          : isActive(n) ? 'font-semibold text-ocean' : 'text-muted-foreground'"
      >
        <span v-if="isActive(n) && route.name !== 'home'" class="absolute top-0 h-0.5 w-8 rounded-full bg-buoy" />
        <component :is="n.icon" class="size-5" :class="isActive(n) ? route.name === 'home' ? 'text-[#176B98]' : 'text-buoy' : ''" />
        <span>{{ n.label }}</span>
      </button>
    </nav>

    <AssistantWidget v-if="route.name !== 'home'" />
  </div>
</template>
