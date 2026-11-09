/**
 * 请求封装：所有接口都通过这里发出。
 * - 自动带上登录令牌（Authorization: Bearer xxx）
 * - 后端统一返回 {code, message, data}：code 为 0 时直接返回 data，否则弹出 message 并抛错
 * - 401 表示未登录或令牌过期：清除登录状态并跳转登录页
 */
import axios from 'axios'
import { showToast } from 'vant'
import 'vant/es/toast/style'

import router from '@/router'
import { useUserStore } from '@/stores/user'

const http = axios.create({ baseURL: '/api', timeout: 15000 })

http.interceptors.request.use((config) => {
  const user = useUserStore()
  if (user.token) {
    config.headers.Authorization = `Bearer ${user.token}`
  }
  return config
})

http.interceptors.response.use(
  (res) => {
    const { code, message, data } = res.data
    if (code === 0) return data
    // 业务错误（HTTP 200 但 code 不为 0），例如「学号或密码错误」
    showToast(message)
    return Promise.reject(Object.assign(new Error(message), { code }))
  },
  (err) => {
    const status = err.response?.status
    const body = err.response?.data
    if (status === 401) {
      useUserStore().logout()
      const current = router.currentRoute.value
      if (current.name !== 'login') {
        router.push({ name: 'login', query: { redirect: current.fullPath } })
      }
    }
    showToast(body?.message || (status ? `请求失败（${status}）` : '网络异常，请检查后端是否启动'))
    return Promise.reject(Object.assign(new Error(body?.message || err.message), { code: body?.code }))
  },
)

export default http
