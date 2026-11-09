<script setup>
import { showConfirmDialog, showToast } from 'vant'
import 'vant/es/dialog/style'
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import { authApi } from '@/api'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const user = useUserStore()

const showWechat = ref(false)
const wechatInput = ref('')
const saving = ref(false)

function openWechat() {
  wechatInput.value = user.profile?.wechat_id ?? ''
  showWechat.value = true
}

async function saveWechat() {
  saving.value = true
  try {
    user.profile = await authApi.updateMe({ wechat_id: wechatInput.value.trim() })
    showWechat.value = false
    showToast({ type: 'success', message: '已保存' })
  } catch {
    /* 格式错误等提示已由 http.js 弹出 */
  } finally {
    saving.value = false
  }
}

function onLogout() {
  showConfirmDialog({ title: '退出登录', message: '确定要退出当前账号吗？' })
    .then(() => {
      user.logout()
      router.replace('/')
    })
    .catch(() => {})
}
</script>

<template>
  <div class="me">
    <header class="hero">
      <div class="avatar">{{ user.profile?.nickname?.slice(0, 1) ?? '?' }}</div>
      <div>
        <div class="name">
          {{ user.profile?.nickname }}
          <van-tag v-if="user.isAdmin" type="warning" round>管理员</van-tag>
        </div>
        <div class="sub">学号 {{ user.profile?.student_no }} · {{ user.profile?.campus_area ?? '未设置校区' }}</div>
      </div>
    </header>

    <van-cell-group inset class="group">
      <van-cell title="微信号" is-link icon="chat-o" @click="openWechat">
        <template #value>
          <span v-if="user.profile?.wechat_id">{{ user.profile.wechat_id }}</span>
          <span v-else class="warn">未填写，交易时需要</span>
        </template>
      </van-cell>
    </van-cell-group>
    <p class="privacy">
      <van-icon name="shield-o" /> 微信号加密保存，只有在卖家接受交易意向后才会展示给对方
    </p>

    <van-cell-group inset class="group">
      <van-cell title="退出登录" icon="revoke" is-link @click="onLogout" />
    </van-cell-group>

    <van-dialog
      v-model:show="showWechat"
      title="设置微信号"
      show-cancel-button
      :before-close="(action) => (action === 'confirm' ? (saveWechat(), false) : true)"
      :confirm-button-disabled="saving"
    >
      <van-field v-model="wechatInput" placeholder="字母开头的微信号，或 11 位手机号" maxlength="20" clearable class="input" />
    </van-dialog>
  </div>
</template>

<style scoped>
.hero {
  background: var(--brand);
  color: #fff;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 36px var(--page-x) 44px;
  border-radius: 0 0 24px 24px;
}
.avatar {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  display: grid;
  place-items: center;
  font-size: 24px;
  font-weight: 600;
}
.name {
  font-size: 19px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}
.sub {
  margin-top: 4px;
  font-size: 12px;
  opacity: 0.85;
}

.group {
  margin-top: 14px;
}
.hero + .group {
  margin-top: -22px;
  box-shadow: var(--shadow-card);
}
.warn {
  color: var(--accent);
}
.privacy {
  margin: 8px calc(var(--page-x) + 4px) 0;
  font-size: 12px;
  color: var(--text-3);
  display: flex;
  align-items: center;
  gap: 4px;
}
.input {
  padding: 16px;
}
</style>
