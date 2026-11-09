/**
 * 页面路由：网址 → 页面组件。
 * meta.auth = true 的页面需要登录，未登录时先跳到登录页，登录后再回来。
 * meta.admin = true 的页面只有管理员能进。
 */
import { showToast } from 'vant'
import 'vant/es/toast/style'
import { createRouter, createWebHistory } from 'vue-router'

import { useUserStore } from '@/stores/user'

const routes = [
  {
    path: '/',
    component: () => import('@/layouts/MobileLayout.vue'),
    children: [
      { path: '', name: 'home', component: () => import('@/views/HomeView.vue'), meta: { title: '首页', tab: true } },
      { path: 'publish', name: 'publish', component: () => import('@/views/PublishView.vue'), meta: { title: '发布闲置', auth: true } },
      { path: 'me', name: 'me', component: () => import('@/views/MeView.vue'), meta: { title: '我的', tab: true, auth: true } },
      { path: 'me/items', name: 'my-items', component: () => import('@/views/MyItemsView.vue'), meta: { title: '我发布的', auth: true } },
      { path: 'me/intents', name: 'my-intents', component: () => import('@/views/MyIntentsView.vue'), meta: { title: '我的意向', auth: true } },
      { path: 'items/:id', name: 'item', component: () => import('@/views/ItemDetailView.vue'), meta: { title: '物品详情' } },
    ],
  },
  {
    path: '/admin',
    component: () => import('@/layouts/AdminLayout.vue'),
    meta: { auth: true, admin: true },
    children: [
      { path: '', redirect: { name: 'admin-items' } },
      { path: 'items', name: 'admin-items', component: () => import('@/views/admin/ItemReviewView.vue'), meta: { title: '物品审核' } },
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
  // to.meta 会合并父路由的 meta，所以 /admin 下的子页面也带 auth、admin
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
  if (to.meta.admin && !user.isAdmin) {
    showToast('需要管理员账号')
    return { name: 'home' }
  }
})

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} · 航海集市` : '航海集市'
})

export default router
