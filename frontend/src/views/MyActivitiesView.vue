<!-- 我报名的活动：即将参加 / 已结束 -->
<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { activityApi } from '@/api'
import ActivityTable from '@/components/ActivityTable.vue'
import PageHeader from '@/components/PageHeader.vue'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'

const router = useRouter()
const when = ref('upcoming')
const items = ref([])
const loading = ref(true)

async function load() {
  loading.value = true
  try {
    items.value = (await activityApi.mine({ when: when.value, page_size: 50 })).items
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="container narrow">
    <PageHeader title="我报名的活动">
      <Button variant="outline" @click="router.push({ name: 'activities' })">找活动</Button>
    </PageHeader>
    <Tabs v-model="when" @update:model-value="load">
      <TabsList>
        <TabsTrigger value="upcoming">即将参加</TabsTrigger>
        <TabsTrigger value="ended">已结束</TabsTrigger>
      </TabsList>
    </Tabs>
    <div class="mt-4">
      <div v-if="loading" class="space-y-3"><Skeleton v-for="i in 3" :key="i" class="h-14" /></div>
      <ActivityTable v-else :items="items" compact :empty-text="when === 'upcoming' ? '还没有报名即将开始的活动' : '还没有参加过的活动'" />
    </div>
  </div>
</template>
