<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { itemApi } from '@/api'
import { useMetaStore } from '@/stores/meta'

const router = useRouter()
const meta = useMetaStore()

const tabs = [
  { name: '', title: '全部' },
  { name: 'pending', title: '审核中' },
  { name: 'online', title: '在售' },
  { name: 'rejected', title: '未通过' },
  { name: 'offline', title: '已下架' },
]
const STATUS_STYLE = { pending: 'warning', online: 'success', rejected: 'danger', offline: 'default' }

const status = ref('')
const items = ref([])
const page = ref(0)
const loading = ref(false)
const finished = ref(false)
const error = ref(false)

async function loadMore() {
  try {
    const params = { page: page.value + 1, page_size: 20 }
    if (status.value) params.status = status.value
    const data = await itemApi.mine(params)
    items.value.push(...data.items)
    page.value = data.page
    finished.value = items.value.length >= data.total
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}

function reload() {
  items.value = []
  page.value = 0
  finished.value = false
  error.value = false
  loading.value = true
  loadMore()
}

onMounted(() => meta.load().catch(() => {}))
</script>

<template>
  <div>
    <van-nav-bar title="我发布的" left-arrow fixed placeholder @click-left="router.back()" />
    <van-tabs v-model:active="status" sticky offset-top="46" @change="reload">
      <van-tab v-for="t in tabs" :key="t.name" :name="t.name" :title="t.title" />
    </van-tabs>

    <van-list
      v-model:loading="loading"
      v-model:error="error"
      :finished="finished"
      :finished-text="items.length ? '没有更多了' : ''"
      error-text="加载失败，点击重试"
      @load="loadMore"
    >
      <router-link v-for="it in items" :key="it.id" :to="{ name: 'item', params: { id: it.id } }" class="row">
        <van-image :src="it.cover" fit="cover" class="thumb" radius="8">
          <template #error><van-icon name="photo-o" class="ph" /></template>
        </van-image>
        <div class="info">
          <div class="top">
            <h3 class="title line-1">{{ it.title }}</h3>
            <van-tag :type="STATUS_STYLE[it.status]" plain>{{ meta.label('content_status', it.status) }}</van-tag>
          </div>
          <div class="price-line">
            <span v-if="it.price === 0" class="free">免费送</span>
            <span v-else class="price">{{ it.price }}</span>
            <span class="views"><van-icon name="eye-o" /> {{ it.view_count }}</span>
          </div>
          <p v-if="it.status === 'rejected' && it.reject_reason" class="reason line-2">
            <van-icon name="warning-o" /> {{ it.reject_reason }}
          </p>
          <p v-else-if="it.status === 'pending'" class="sub">提交于 {{ new Date(it.created_at).toLocaleString() }}，等待审核</p>
        </div>
      </router-link>

      <van-empty v-if="finished && !items.length" description="这里还没有物品">
        <van-button round type="primary" size="small" @click="router.push({ name: 'publish' })">去发布</van-button>
      </van-empty>
    </van-list>
  </div>
</template>

<style scoped>
.row {
  display: flex;
  gap: 12px;
  background: var(--bg-card);
  margin: 10px var(--page-x) 0;
  padding: 12px;
  border-radius: var(--radius);
}
.thumb {
  flex-shrink: 0;
  width: 84px;
  height: 84px;
  background: var(--brand-soft);
}
.ph {
  font-size: 26px;
  color: var(--brand);
  opacity: 0.45;
}
.info {
  flex: 1;
  min-width: 0;
}
.top {
  display: flex;
  align-items: center;
  gap: 8px;
}
.title {
  flex: 1;
  margin: 0;
  font-size: 15px;
  font-weight: 500;
}
.price-line {
  margin-top: 8px;
  display: flex;
  align-items: baseline;
  justify-content: space-between;
}
.price {
  font-size: 17px;
}
.free {
  color: var(--success);
  font-weight: 600;
}
.views {
  color: var(--text-3);
  font-size: 12px;
}
.reason {
  margin: 8px 0 0;
  padding: 6px 8px;
  border-radius: 6px;
  background: #fdeeee;
  color: var(--danger);
  font-size: 12px;
}
.sub {
  margin: 8px 0 0;
  color: var(--text-3);
  font-size: 12px;
}
</style>
