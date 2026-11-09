<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useMetaStore } from '@/stores/meta'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const user = useUserStore()
const meta = useMetaStore()

const mode = ref('login') // login | register
const submitting = ref(false)
const showCampus = ref(false)
const form = reactive({ studentNo: '', password: '', nickname: '', campus: '' })

const campusColumns = computed(() => (meta.enums?.campus_area ?? []).map((c) => ({ text: c, value: c })))

onMounted(() => meta.load().catch(() => {}))

// 前端先做一遍和后端相同的格式检查，提示更及时；最终以后端校验为准
const rules = {
  studentNo: [{ pattern: /^\d{6,20}$/, message: '学号应为 6–20 位数字' }],
  password: [{ required: true, message: '请输入密码' }],
  newPassword: [
    { pattern: /^[\x21-\x7E]{8,32}$/, message: '密码 8–32 位，不能含空格或中文' },
    { validator: (v) => /[a-zA-Z]/.test(v) && /\d/.test(v), message: '密码需同时包含字母和数字' },
  ],
  nickname: [{ required: true, message: '请输入昵称' }],
}

async function onSubmit() {
  submitting.value = true
  try {
    if (mode.value === 'login') {
      await user.login(form.studentNo, form.password)
    } else {
      await user.register({
        student_no: form.studentNo,
        password: form.password,
        nickname: form.nickname,
        campus_area: form.campus || null,
      })
    }
    router.replace(route.query.redirect || '/')
  } catch {
    /* 错误提示已由 http.js 弹出 */
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="page">
    <header class="hero">
      <div class="logo">
        <van-icon name="guide-o" />
      </div>
      <h1>航海集市</h1>
      <p>校内二手交易 · 社团 · 活动，一站搞定</p>
    </header>

    <section class="card">
      <van-tabs v-model:active="mode" shrink line-width="24" class="tabs">
        <van-tab title="登录" name="login" />
        <van-tab title="注册" name="register" />
      </van-tabs>

      <van-form :key="mode" @submit="onSubmit">
        <van-cell-group inset class="fields">
          <van-field
            v-model.trim="form.studentNo"
            name="studentNo"
            label="学号"
            placeholder="请输入学号"
            type="digit"
            maxlength="20"
            :rules="rules.studentNo"
          />
          <van-field
            v-if="mode === 'register'"
            v-model.trim="form.nickname"
            name="nickname"
            label="昵称"
            placeholder="给自己起个名字"
            maxlength="30"
            :rules="rules.nickname"
          />
          <van-field
            v-model="form.password"
            name="password"
            label="密码"
            type="password"
            :placeholder="mode === 'login' ? '请输入密码' : '8–32 位，含字母和数字'"
            maxlength="32"
            :rules="mode === 'login' ? rules.password : rules.newPassword"
          />
          <van-field
            v-if="mode === 'register'"
            :model-value="form.campus"
            is-link
            readonly
            name="campus"
            label="校区"
            placeholder="选择所在校区（可不填）"
            @click="showCampus = true"
          />
        </van-cell-group>

        <div class="actions">
          <van-button round block type="primary" native-type="submit" :loading="submitting">
            {{ mode === 'login' ? '登录' : '注册并登录' }}
          </van-button>
          <p v-if="mode === 'login'" class="hint">演示账号：20230002 / Test1234</p>
        </div>
      </van-form>
    </section>

    <van-popup v-model:show="showCampus" round position="bottom">
      <van-picker
        title="选择校区"
        :columns="campusColumns"
        @confirm="({ selectedValues }) => ((form.campus = selectedValues[0]), (showCampus = false))"
        @cancel="showCampus = false"
      />
    </van-popup>
  </div>
</template>

<style scoped>
.page {
  max-width: 480px;
  min-height: 100vh;
  margin: 0 auto;
  background: var(--bg-page);
}

.hero {
  background: var(--brand);
  color: #fff;
  padding: 56px 24px 72px;
  text-align: center;
  border-radius: 0 0 28px 28px;
}
.logo {
  width: 56px;
  height: 56px;
  margin: 0 auto 12px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.16);
  display: grid;
  place-items: center;
  font-size: 30px;
}
.hero h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  letter-spacing: 2px;
}
.hero p {
  margin: 6px 0 0;
  font-size: 13px;
  opacity: 0.85;
}

.card {
  margin: -40px var(--page-x) 0;
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
  padding: 8px 0 20px;
}
.tabs {
  margin: 0 8px 8px;
}
.fields {
  margin: 0;
}
.actions {
  padding: 20px 16px 0;
}
.hint {
  margin: 12px 0 0;
  text-align: center;
  color: var(--text-3);
  font-size: 12px;
}
</style>
