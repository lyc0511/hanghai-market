<!-- 网站外壳：顶部导航 + 内容区 + 页脚。除登录页和管理后台外，所有页面都在这里面 -->
<script setup>
import AppHeader from '@/components/AppHeader.vue'
import AssistantWidget from '@/components/AssistantWidget.vue'
</script>

<template>
  <div class="flex min-h-screen flex-col">
    <AppHeader />
    <main class="flex-1 pb-16 pt-6 md:pt-8">
      <router-view />
    </main>
    <footer class="border-t bg-white py-6 text-center text-xs text-muted-foreground">
      <div class="container">航海集市：广州航海学院校内二手交易与社团活动平台（本科毕业设计）</div>
    </footer>
    <AssistantWidget />
  </div>
</template>
