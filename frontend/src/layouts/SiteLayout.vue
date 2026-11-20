<!-- 网站外壳：顶部导航 + 内容区 + 页脚 + 手机端底部主导航。除登录页和管理后台外，所有页面都在这里面 -->
<script setup>
import { Calendar, Home, MessageSquare, ShoppingBag, Users } from '@lucide/vue'
import { useRoute } from 'vue-router'

import AppHeader from '@/components/AppHeader.vue'
import AssistantWidget from '@/components/AssistantWidget.vue'

const route = useRoute()

const MOBILE_NAV = [
  { to: '/', label: '首页', icon: Home, exact: true },
  { to: '/market', label: '二手', icon: ShoppingBag },
  { to: '/clubs', label: '社团', icon: Users },
  { to: '/activities', label: '活动', icon: Calendar },
  { to: '/wall', label: '校园墙', icon: MessageSquare },
]

function isActive(n) {
  return n.exact ? route.path === n.to : route.path.startsWith(n.to)
}
</script>

<template>
  <div class="flex min-h-screen flex-col">
    <AppHeader />
    <main class="flex-1 pb-24 pt-6 md:pb-16 md:pt-8">
      <router-view />
    </main>
    <footer class="border-t bg-white pb-20 pt-6 text-center text-xs text-muted-foreground md:pb-6">
      <div class="container">航海集市：广州航海学院校内二手交易与社团活动平台（本科毕业设计）</div>
    </footer>

    <!-- 手机端底部固定导航栏：五大板块一键直达 -->
    <nav
      class="fixed inset-x-0 bottom-0 z-40 grid h-16 grid-cols-5 border-t bg-white/95 backdrop-blur md:hidden"
      aria-label="底部主导航"
    >
      <router-link
        v-for="n in MOBILE_NAV"
        :key="n.to"
        :to="n.to"
        class="relative flex flex-col items-center justify-center gap-0.5 text-[11px] transition-colors"
        :class="isActive(n) ? 'font-semibold text-ocean' : 'text-muted-foreground'"
      >
        <span v-if="isActive(n)" class="absolute top-0 h-0.5 w-8 rounded-full bg-buoy" />
        <component :is="n.icon" class="size-5" :class="isActive(n) ? 'text-buoy' : ''" />
        <span>{{ n.label }}</span>
      </router-link>
    </nav>

    <AssistantWidget />
  </div>
</template>
