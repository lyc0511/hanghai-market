/**
 * 页面路由：网址 → 页面组件。
 * meta.auth = true 的页面需要登录，未登录时先跳到登录页，登录后再回来。
 * meta.admin = true 的页面只有管理员能进。
 */
import { toast } from 'vue-sonner'
import { createRouter, createWebHistory } from 'vue-router'

import { useUserStore } from '@/stores/user'

const routes = [
  {
    path: '/',
    component: () => import('@/layouts/SiteLayout.vue'),
    children: [
      { path: '', name: 'home', component: () => import('@/views/HomeView.vue'), meta: { title: '首页' } },
      { path: 'market', name: 'market', component: () => import('@/views/MarketView.vue'), meta: { title: '二手交易' } },
      { path: 'clubs', name: 'clubs', component: () => import('@/views/ClubsView.vue'), meta: { title: '社团' } },
      { path: 'clubs/:id/applications', name: 'club-applications', component: () => import('@/views/ClubApplicationsView.vue'), meta: { title: '入社申请', auth: true } },
      { path: 'clubs/:id', name: 'club', component: () => import('@/views/ClubDetailView.vue'), meta: { title: '社团详情' } },
      { path: 'activities', name: 'activities', component: () => import('@/views/ActivitiesView.vue'), meta: { title: '活动' } },
      { path: 'activities/:id', name: 'activity', component: () => import('@/views/ActivityDetailView.vue'), meta: { title: '活动详情' } },
      // 校园墙：wall/new 必须写在 wall/:id 前面，否则 "new" 会被当成帖子 id
      { path: 'wall', name: 'wall', component: () => import('@/views/WallView.vue'), meta: { title: '墙' } },
      { path: 'wall/new', name: 'wall-new', component: () => import('@/views/WallSubmitView.vue'), meta: { title: '投稿', auth: true } },
      { path: 'wall/:id/edit', name: 'wall-edit', component: () => import('@/views/WallSubmitView.vue'), meta: { title: '修改投稿', auth: true } },
      { path: 'wall/:id', name: 'wall-post', component: () => import('@/views/WallPostView.vue'), meta: { title: '帖子', auth: true } },
      { path: 'me/posts', name: 'my-posts', component: () => import('@/views/MyPostsView.vue'), meta: { title: '我的投稿', auth: true } },
      { path: 'publish', name: 'publish', component: () => import('@/views/PublishView.vue'), meta: { title: '发布闲置', auth: true } },
      { path: 'me', name: 'me', component: () => import('@/views/MeView.vue'), meta: { title: '个人中心', auth: true } },
      { path: 'me/activities', name: 'my-activities', component: () => import('@/views/MyActivitiesView.vue'), meta: { title: '我报名的活动', auth: true } },
      { path: 'me/clubs', name: 'my-clubs', component: () => import('@/views/MyClubsView.vue'), meta: { title: '我的社团', auth: true } },
      { path: 'me/items', name: 'my-items', component: () => import('@/views/MyItemsView.vue'), meta: { title: '我发布的', auth: true } },
      { path: 'notifications', name: 'notifications', component: () => import('@/views/NotificationsView.vue'), meta: { title: '消息通知', auth: true } },
      { path: 'me/reports', name: 'my-reports', component: () => import('@/views/MyReportsView.vue'), meta: { title: '我的举报', auth: true } },
      { path: 'me/intents', name: 'my-intents', component: () => import('@/views/MyIntentsView.vue'), meta: { title: '我的意向', auth: true } },
      { path: 'items/:id/edit', name: 'item-edit', component: () => import('@/views/PublishView.vue'), meta: { title: '编辑物品', auth: true } },
      { path: 'items/:id', name: 'item', component: () => import('@/views/ItemDetailView.vue'), meta: { title: '物品详情' } },
    ],
  },
  {
    path: '/admin',
    component: () => import('@/layouts/AdminLayout.vue'),
    meta: { auth: true, admin: true },
    children: [
      { path: '', name: 'admin-dashboard', component: () => import('@/views/admin/DashboardView.vue'), meta: { title: '数据看板' } },
      { path: 'items', name: 'admin-items', component: () => import('@/views/admin/ItemReviewView.vue'), meta: { title: '物品审核' } },
      { path: 'activities', name: 'admin-activities', component: () => import('@/views/admin/ActivityReviewView.vue'), meta: { title: '活动审核' } },
      { path: 'posts', name: 'admin-posts', component: () => import('@/views/admin/PostReviewView.vue'), meta: { title: '墙审核' } },
      { path: 'reports', name: 'admin-reports', component: () => import('@/views/admin/ReportView.vue'), meta: { title: '举报处理' } },
      { path: 'users', name: 'admin-users', component: () => import('@/views/admin/UserManageView.vue'), meta: { title: '用户管理' } },
      { path: 'audit-logs', name: 'admin-audit-logs', component: () => import('@/views/admin/AuditLogView.vue'), meta: { title: '操作日志' } },
    ],
  },
  { path: '/change-password', name: 'change-password', component: () => import('@/views/ChangePasswordView.vue'), meta: { title: '设置新密码', auth: true } },
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
  if (user.profile?.must_change_password && to.name !== 'change-password') {
    return { name: 'change-password' }
  }
  if (to.meta.admin && !user.isAdmin) {
    toast.error('需要管理员账号')
    return { name: 'home' }
  }
})

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} · 航海集市` : '航海集市'
})

export default router
