<!-- 社团、活动板块的占位页：后端接口完成后替换为真实页面 -->
<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import { Button } from '@/components/ui/button'

const route = useRoute()
const isClubs = computed(() => route.meta.section === 'clubs')
</script>

<template>
  <div class="container">
    <div class="mx-auto max-w-lg py-20 text-center">
      <h1 class="font-display text-4xl text-ocean">{{ isClubs ? '社团' : '活动' }}板块正在建设</h1>
      <p class="mt-4 leading-relaxed text-muted-foreground">
        {{ isClubs ? '上线后可以浏览全校社团、查看招新信息、在线申请入社。' : '上线后可以浏览社团活动、查看名额、在线报名。' }}
      </p>
      <Button class="mt-8" @click="$router.push({ name: 'market' })">先去二手市场看看</Button>
    </div>
  </div>
</template>
