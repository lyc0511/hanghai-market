<script setup>
import { showConfirmDialog, showToast } from 'vant'
import 'vant/es/dialog/style'
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { intentApi } from '@/api'
import { useMetaStore } from '@/stores/meta'

const route = useRoute()
const router = useRouter()
const meta = useMetaStore()

const STATUS_STYLE = { pending: 'warning', accepted: 'primary', completed: 'success', rejected: 'default', cancelled: 'default' }

const role = ref(route.query.role === 'seller' ? 'seller' : 'buyer')
const list = ref([])
const page = ref(0)
const loading = ref(false)
const finished = ref(false)
const error = ref(false)
const busyId = ref(null)

async function loadMore() {
  try {
    const data = await intentApi.mine({ role: role.value, page: page.value + 1, page_size: 20 })
    list.value.push(...data.items)
    page.value = data.page
    finished.value = list.value.length >= data.total
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}

function reload() {
  router.replace({ query: { role: role.value } })
  list.value = []
  page.value = 0
  finished.value = false
  error.value = false
  loading.value = true
  loadMore()
}

// 每个操作：确认 → 调接口 → 用返回的最新数据替换列表里那一条
const ACTIONS = {
  accept: { api: intentApi.accept, confirm: '接受后，你们可以互相看到对方的微信号。', done: '已接受' },
  reject: { api: intentApi.reject, confirm: '确定不考虑这位同学的意向吗？', done: '已拒绝' },
  cancel: { api: intentApi.cancel, confirm: '确定取消这次意向吗？', done: '已取消' },
  complete: { api: intentApi.complete, confirm: '确认已经线下完成交易？物品会自动下架，其他同学的意向会自动关闭。', done: '已成交' },
}

async function act(t, name) {
  const a = ACTIONS[name]
  try {
    await showConfirmDialog({ title: '请确认', message: a.confirm })
  } catch {
    return // 用户点了取消
  }
  busyId.value = t.id
  try {
    const fresh = await a.api(t.id)
    const i = list.value.findIndex((x) => x.id === t.id)
    if (i >= 0) list.value[i] = fresh
    showToast({ type: 'success', message: a.done })
  } catch {
    /* 提示已由 http.js 弹出 */
  } finally {
    busyId.value = null
  }
}

async function copyWechat(text) {
  try {
    await navigator.clipboard.writeText(text)
    showToast({ type: 'success', message: '微信号已复制' })
  } catch {
    showToast(`微信号：${text}`)
  }
}

onMounted(() => meta.load().catch(() => {}))
</script>

<template>
  <div>
    <van-nav-bar title="我的意向" left-arrow fixed placeholder @click-left="router.back()" />
    <van-tabs v-model:active="role" sticky offset-top="46" @change="reload">
      <van-tab name="buyer" title="我想要的" />
      <van-tab name="seller" title="找我买的" />
    </van-tabs>

    <van-list
      v-model:loading="loading"
      v-model:error="error"
      :finished="finished"
      :finished-text="list.length ? '没有更多了' : ''"
      error-text="加载失败，点击重试"
      @load="loadMore"
    >
      <article v-for="t in list" :key="t.id" class="card">
        <header class="head">
          <span class="who">
            {{ t.my_role === 'buyer' ? '卖家' : '买家' }}：<b>{{ t.counterpart.nickname }}</b>
          </span>
          <van-tag :type="STATUS_STYLE[t.status]" plain>{{ meta.label('intent_status', t.status) }}</van-tag>
        </header>

        <router-link :to="{ name: 'item', params: { id: t.item.id } }" class="item">
          <van-image :src="t.item.cover" fit="cover" class="thumb" radius="8">
            <template #error><van-icon name="photo-o" class="ph" /></template>
          </van-image>
          <div class="item-info">
            <div class="line-1">{{ t.item.title }}</div>
            <span class="price">{{ t.item.price }}</span>
          </div>
        </router-link>

        <p v-if="t.message" class="msg"><van-icon name="chat-o" /> {{ t.message }}</p>

        <div v-if="t.counterpart_wechat" class="wechat">
          <van-icon name="friends-o" />
          <span>对方微信号 <b>{{ t.counterpart_wechat }}</b></span>
          <van-button size="mini" round plain type="primary" @click="copyWechat(t.counterpart_wechat)">复制</van-button>
        </div>

        <footer class="actions">
          <span class="time">{{ new Date(t.updated_at).toLocaleString() }}</span>
          <template v-if="t.my_role === 'seller' && t.status === 'pending'">
            <van-button size="small" round :disabled="busyId === t.id" @click="act(t, 'reject')">拒绝</van-button>
            <van-button size="small" round type="primary" :loading="busyId === t.id" @click="act(t, 'accept')">接受</van-button>
          </template>
          <van-button
            v-else-if="t.my_role === 'seller' && t.status === 'accepted'"
            size="small"
            round
            type="primary"
            :loading="busyId === t.id"
            @click="act(t, 'complete')"
          >
            已成交
          </van-button>
          <van-button
            v-if="t.my_role === 'buyer' && (t.status === 'pending' || t.status === 'accepted')"
            size="small"
            round
            :loading="busyId === t.id"
            @click="act(t, 'cancel')"
          >
            取消意向
          </van-button>
        </footer>
      </article>

      <van-empty
        v-if="finished && !list.length"
        :description="role === 'buyer' ? '还没有想要的物品，去首页逛逛吧' : '还没有人对你的物品感兴趣'"
      />
    </van-list>
  </div>
</template>

<style scoped>
.card {
  background: var(--bg-card);
  margin: 10px var(--page-x) 0;
  padding: 12px;
  border-radius: var(--radius);
}
.head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  color: var(--text-2);
}
.who b {
  color: var(--text-1);
  font-weight: 500;
}
.item {
  display: flex;
  gap: 10px;
  margin-top: 10px;
  padding: 8px;
  border-radius: var(--radius-sm);
  background: var(--bg-page);
}
.thumb {
  flex-shrink: 0;
  width: 52px;
  height: 52px;
  background: var(--brand-soft);
}
.ph {
  font-size: 20px;
  color: var(--brand);
  opacity: 0.45;
}
.item-info {
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}
.msg {
  margin: 10px 0 0;
  color: var(--text-2);
  font-size: 13px;
}
.wechat {
  margin-top: 10px;
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  background: var(--brand-soft);
  color: var(--brand-dark);
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}
.wechat span {
  flex: 1;
}
.actions {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.time {
  flex: 1;
  color: var(--text-3);
  font-size: 12px;
}
</style>
