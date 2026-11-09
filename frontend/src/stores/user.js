/**
 * 登录状态：令牌和当前用户信息。
 * 令牌存在 localStorage，刷新页面后仍保持登录（有效期由后端控制，默认 24 小时）。
 */
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { authApi } from '@/api'

const TOKEN_KEY = 'campus_token'

function readToken() {
  try {
    return localStorage.getItem(TOKEN_KEY) || ''
  } catch {
    return ''
  }
}

export const useUserStore = defineStore('user', () => {
  const token = ref(readToken())
  const profile = ref(null)

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => profile.value?.role === 'admin')

  function setSession(data) {
    token.value = data.access_token
    profile.value = data.user
    try {
      localStorage.setItem(TOKEN_KEY, data.access_token)
    } catch {
      /* 隐私模式下 localStorage 不可用，只在内存中保持登录 */
    }
  }

  async function login(studentNo, password) {
    setSession(await authApi.login(studentNo, password))
  }

  async function register(body) {
    setSession(await authApi.register(body))
  }

  /** 页面刷新后用令牌换回用户信息 */
  async function fetchProfile() {
    if (!token.value) return null
    profile.value = await authApi.me()
    return profile.value
  }

  function logout() {
    token.value = ''
    profile.value = null
    try {
      localStorage.removeItem(TOKEN_KEY)
    } catch {
      /* 忽略 */
    }
  }

  return { token, profile, isLoggedIn, isAdmin, login, register, fetchProfile, logout }
})
