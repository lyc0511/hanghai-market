<!-- 内页标题栏：返回 + 标题 + 右侧操作（可选） -->
<script setup>
import { ArrowLeft } from '@lucide/vue'
import { useRouter } from 'vue-router'

import { Button } from '@/components/ui/button'

defineProps({ title: { type: String, required: true } })
const router = useRouter()

function back() {
  // 直接打开的页面没有上一页时，回首页
  if (window.history.state?.back) router.back()
  else router.push('/')
}
</script>

<template>
  <div class="mb-5 flex items-center gap-2">
    <Button variant="ghost" size="icon" class="-ml-2" aria-label="返回" @click="back"><ArrowLeft class="size-5" /></Button>
    <h1 class="font-display text-3xl text-ocean">{{ title }}</h1>
    <div class="ml-auto flex gap-2"><slot /></div>
  </div>
</template>
