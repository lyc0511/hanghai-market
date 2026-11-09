<script setup>
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'vue-sonner/style.css'

import ConfirmHost from '@/components/ConfirmHost.vue'
import { Toaster } from '@/components/ui/sonner'
</script>

<template>
  <!-- Element Plus（只用于管理后台）默认英文，在最外层统一切换为中文 -->
  <el-config-provider :locale="zhCn">
    <router-view />
  </el-config-provider>
  <!-- 全站共用：顶部提示（toast）和确认弹窗 -->
  <Toaster position="top-center" rich-colors />
  <ConfirmHost />
</template>
