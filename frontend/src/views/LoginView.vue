<!-- 独立登录页：访问需要登录的页面时会跳到这里，登录后回到原来的页面 -->
<script setup>
import { useRoute, useRouter } from 'vue-router'

import LoginForm from '@/components/LoginForm.vue'

const route = useRoute()
const router = useRouter()
</script>

<template>
  <div class="grid min-h-screen bg-white lg:grid-cols-2">
    <section class="relative flex flex-col justify-end bg-ocean px-8 pb-12 pt-24 text-white lg:justify-center lg:px-16">
      <router-link to="/" class="absolute left-8 top-7 font-display text-2xl lg:left-16">航海集市</router-link>
      <h1 class="font-display text-4xl leading-tight lg:text-6xl">
        今天港口<br />到了什么货？
      </h1>
      <p class="mt-4 max-w-sm text-white/70">二手闲置、社团招新、校园活动，在广航同学之间流转。</p>
    </section>
    <section class="flex items-center justify-center px-6 py-12">
      <div class="w-full max-w-sm">
        <p v-if="route.query.redirect" class="mb-4 rounded-lg bg-secondary px-3 py-2 text-sm text-ocean">这个页面需要先登录</p>
        <LoginForm @success="router.replace(route.query.redirect || '/')" />
      </div>
    </section>
  </div>
</template>
