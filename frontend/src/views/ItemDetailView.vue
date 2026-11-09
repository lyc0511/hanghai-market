<script setup>
import { showConfirmDialog, showToast } from 'vant'
import 'vant/es/dialog/style'
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { intentApi, itemApi } from '@/api'
import { useMetaStore } from '@/stores/meta'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const user = useUserStore()
const meta = useMetaStore()

const item = ref(null)
const notFound = ref(false)
const showIntent = ref(false)
const message = ref('')
const sending = ref(false)

const discount = computed(() => {
  const it = item.value
  if (!it?.original_price || it.original_price <= it.price) return null
  return Math.round((it.price / it.original_price) * 100) / 10 // 例如 3.5 折
})

onMounted(async () => {
  meta.load().catch(() => {})
  try {
    item.value = await itemApi.detail(route.params.id)
  } catch {
    notFound.value = true
  }
})

function onWant() {
  if (!user.isLoggedIn) {
    router.push({ name: 'login', query: { redirect: route.fullPath } })
    return
  }
  showIntent.value = true
}

async function sendIntent() {
  sending.value = true
  try {
    await intentApi.create(item.value.id, message.value.trim())
    showIntent.value = false
    showToast({ type: 'success', message: '已告诉卖家，等待对方回复' })
  } catch (e) {
    // 没填微信号时，引导去个人中心填写
    if (e.code === 42202) {
      showIntent.value = false
      showConfirmDialog({ title: '还没有填写微信号', message: '卖家接受后需要互相添加微信，现在去填写吗？' })
        .then(() => router.push({ name: 'me' }))
        .catch(() => {})
    }
  } finally {
    sending.value = false
  }
}
</script>

<template>
  <div class="detail">
    <van-nav-bar title="物品详情" left-arrow fixed placeholder @click-left="router.back()" />

    <van-empty v-if="notFound" image="error" description="物品不存在或已下架">
      <van-button round type="primary" size="small" @click="router.replace('/')">回到首页</van-button>
    </van-empty>

    <van-skeleton v-else-if="!item" title :row="6" class="skeleton" />

    <template v-else>
      <van-swipe class="gallery" indicator-color="#fff" lazy-render>
        <van-swipe-item v-for="(src, i) in item.images" :key="i">
          <van-image :src="src" fit="cover" class="gallery-img">
            <template #error>
              <div class="placeholder"><van-icon name="photo-o" /></div>
            </template>
          </van-image>
        </van-swipe-item>
      </van-swipe>

      <section class="block price-block">
        <div class="price-line">
          <span v-if="item.price === 0" class="free">免费送</span>
          <span v-else class="price big">{{ item.price }}</span>
          <span v-if="item.original_price" class="original">原价 ¥{{ item.original_price }}</span>
          <span v-if="discount" class="discount">{{ discount }} 折</span>
        </div>
        <h1 class="title">{{ item.title }}</h1>
        <div v-if="item.tags.length" class="tags">
          <van-tag v-for="t in item.tags" :key="t" plain type="primary">{{ t }}</van-tag>
        </div>
        <van-notice-bar
          v-if="item.status !== 'online'"
          :left-icon="item.status === 'rejected' ? 'warning-o' : 'info-o'"
          :color="item.status === 'rejected' ? 'var(--danger)' : 'var(--warning)'"
          background="var(--accent-soft)"
          :text="item.status === 'rejected' ? `未通过审核：${item.reject_reason}` : `当前状态：${meta.label('content_status', item.status)}，仅你自己可见`"
          wrapable
          :scrollable="false"
          class="notice"
        />
      </section>

      <section class="block">
        <div class="facts">
          <div><span>成色</span>{{ meta.label('item_condition', item.condition) }}</div>
          <div><span>分类</span>{{ item.category?.name ?? '—' }}</div>
          <div><span>校区</span>{{ item.campus_area ?? '—' }}</div>
          <div><span>浏览</span>{{ item.view_count }}</div>
        </div>
        <p v-if="item.summary" class="summary">{{ item.summary }}</p>
      </section>

      <section class="block seller">
        <div class="avatar">{{ item.seller.nickname.slice(0, 1) }}</div>
        <div class="seller-info">
          <div class="seller-name">{{ item.seller.nickname }}</div>
          <div class="seller-sub">{{ item.seller.campus_area ?? '校内同学' }} · 发布于 {{ new Date(item.created_at).toLocaleDateString() }}</div>
        </div>
      </section>

      <van-action-bar safe-area-inset-bottom class="bar">
        <van-action-bar-icon icon="wap-home-o" text="首页" @click="router.push('/')" />
        <van-action-bar-button v-if="item.is_mine" type="default" text="这是你发布的物品" disabled />
        <van-action-bar-button v-else-if="item.status !== 'online'" type="default" text="暂不可交易" disabled />
        <van-action-bar-button v-else type="primary" text="我想要" @click="onWant" />
      </van-action-bar>
    </template>

    <van-dialog
      v-model:show="showIntent"
      title="给卖家留言"
      show-cancel-button
      confirm-button-text="发送意向"
      :before-close="(action) => (action === 'confirm' ? (sendIntent(), false) : true)"
      :confirm-button-disabled="sending"
    >
      <van-field
        v-model="message"
        rows="3"
        autosize
        type="textarea"
        maxlength="200"
        show-word-limit
        placeholder="例如：还在吗？今晚可以在图书馆门口面交"
        class="msg"
      />
    </van-dialog>
  </div>
</template>

<style scoped>
.detail {
  padding-bottom: 72px;
}
.skeleton {
  padding-top: 20px;
}
.gallery {
  background: var(--brand-soft);
}
.gallery-img {
  display: block;
  width: 100%;
  aspect-ratio: 1 / 1;
}
.placeholder {
  width: 100%;
  height: 100%;
  display: grid;
  place-items: center;
  color: var(--brand);
  opacity: 0.4;
  font-size: 56px;
}

.block {
  background: var(--bg-card);
  margin: 10px var(--page-x) 0;
  border-radius: var(--radius);
  padding: 14px;
}
.price-block {
  margin-top: -16px;
  position: relative;
  z-index: 1;
  box-shadow: var(--shadow-card);
}
.price-line {
  display: flex;
  align-items: baseline;
  gap: 8px;
}
.big {
  font-size: 26px;
}
.free {
  color: var(--success);
  font-size: 22px;
  font-weight: 600;
}
.original {
  color: var(--text-3);
  font-size: 12px;
  text-decoration: line-through;
}
.discount {
  font-size: 11px;
  color: var(--accent);
  background: var(--accent-soft);
  padding: 1px 6px;
  border-radius: 4px;
}
.title {
  margin: 8px 0 0;
  font-size: 17px;
  font-weight: 600;
  line-height: 1.45;
}
.tags {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.notice {
  margin-top: 10px;
  border-radius: var(--radius-sm);
}

.facts {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  text-align: center;
  font-weight: 500;
}
.facts span {
  display: block;
  color: var(--text-3);
  font-size: 12px;
  font-weight: 400;
  margin-bottom: 2px;
}
.summary {
  margin: 14px 0 0;
  padding-top: 12px;
  border-top: 1px solid var(--border);
  color: var(--text-2);
  line-height: 1.7;
  white-space: pre-wrap;
}

.seller {
  display: flex;
  align-items: center;
  gap: 12px;
}
.avatar {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  background: var(--brand-soft);
  color: var(--brand-dark);
  display: grid;
  place-items: center;
  font-weight: 600;
  font-size: 17px;
}
.seller-name {
  font-weight: 500;
}
.seller-sub {
  color: var(--text-3);
  font-size: 12px;
}

.bar {
  max-width: 480px;
  left: 50%;
  transform: translateX(-50%);
}
.msg {
  padding: 12px 16px;
}
</style>
