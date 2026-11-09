<!-- 管理后台外壳（电脑端）：左侧菜单 + 顶栏 + 内容区，使用 Element Plus -->
<script setup>
import { Calendar, DataAnalysis, Document, Goods, User, Warning, HomeFilled, SwitchButton } from '@element-plus/icons-vue'
import { useRoute, useRouter } from 'vue-router'

import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const user = useUserStore()

function logout() {
  user.logout()
  router.replace({ name: 'login' })
}
</script>

<template>
  <el-container class="admin">
    <el-aside width="208px" class="aside">
      <div class="logo">
        <span class="mark">航</span>
        <div>
          <div class="name">航海集市</div>
          <div class="sub">管理后台</div>
        </div>
      </div>
      <el-menu :default-active="route.name" router class="menu">
        <el-menu-item index="admin-dashboard" :route="{ name: 'admin-dashboard' }">
          <el-icon><DataAnalysis /></el-icon>
          <span>数据看板</span>
        </el-menu-item>
        <el-menu-item index="admin-items" :route="{ name: 'admin-items' }">
          <el-icon><Goods /></el-icon>
          <span>物品审核</span>
        </el-menu-item>
        <el-menu-item index="admin-activities" :route="{ name: 'admin-activities' }">
          <el-icon><Calendar /></el-icon>
          <span>活动审核</span>
        </el-menu-item>
        <el-menu-item index="admin-reports" :route="{ name: 'admin-reports' }">
          <el-icon><Warning /></el-icon>
          <span>举报处理</span>
        </el-menu-item>
        <el-menu-item index="admin-users" :route="{ name: 'admin-users' }">
          <el-icon><User /></el-icon>
          <span>用户管理</span>
        </el-menu-item>
        <el-menu-item index="admin-audit-logs" :route="{ name: 'admin-audit-logs' }">
          <el-icon><Document /></el-icon>
          <span>操作日志</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <h1>{{ route.meta.title }}</h1>
        <div class="right">
          <el-button text :icon="HomeFilled" @click="router.push('/')">回到前台</el-button>
          <el-divider direction="vertical" />
          <span class="who">{{ user.profile?.nickname }}</span>
          <el-button text :icon="SwitchButton" @click="logout">退出</el-button>
        </div>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.admin {
  min-height: 100vh;
  background: var(--bg-page);
}
.aside {
  background: #10233f;
  color: #fff;
}
.logo {
  height: 64px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
.mark {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: var(--brand);
  display: grid;
  place-items: center;
  font-weight: 600;
}
.name {
  font-weight: 600;
  letter-spacing: 1px;
}
.sub {
  font-size: 12px;
  opacity: 0.6;
}
.menu {
  border-right: 0;
  --el-menu-bg-color: transparent;
  --el-menu-text-color: rgba(255, 255, 255, 0.72);
  --el-menu-hover-bg-color: rgba(255, 255, 255, 0.06);
  --el-menu-active-color: #fff;
  padding-top: 8px;
}
.menu :deep(.el-menu-item.is-active) {
  background: var(--brand);
  margin: 0 10px;
  border-radius: 8px;
}
.header {
  height: 64px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--line);
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.header h1 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}
.right {
  display: flex;
  align-items: center;
}
.who {
  color: var(--text-2);
  margin: 0 4px 0 8px;
}
.main {
  padding: 20px;
}
</style>
