/**
 * 页面路由：网址 → 页面组件。
 * meta.auth = true 的页面需要登录，未登录时先跳到登录页，登录后再回来。
 */
import { createRouter, createWebHistory } from 'vue-router'

import { useUserStore } from '@/stores/user'

const routes = [
  {
    path: '/',
    component: () => import('@/layouts/MobileLayout.vue'),
    children: [
      { path: '', name: 'home', component: () => import('@/views/HomeView.vue'), meta: { title: '首页', tab: true } },
      { path: 'me', name: 'me', component: () => import('@/views/MeView.vue'), meta: { title: '我的', tab: true, auth: true } },
      { path: 'items/:id', name: 'item', component: () => import('@/views/ItemDetailView.vue'), meta: { title: '物品详情' } },
    ],
  },
  { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue'), meta: { title: '登录' } },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: (to, from, saved) => saved || { top: 0 },
})

router.beforeEach(async (to) => {
  const user = useUserStore()
  if (to.meta.auth && !user.isLoggedIn) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  // 有令牌但还没拿到用户信息（刷新页面后），先补齐
  if (user.isLoggedIn && !user.profile) {
    try {
      await user.fetchProfile()
    } catch {
      /* 令牌失效时 http.js 已处理跳转 */
    }
  }
})

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} · 航海集市` : '航海集市'
})

export default router
