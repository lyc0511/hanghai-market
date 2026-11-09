/**
 * 未读通知数：顶部铃铛红点用。
 * 登录后每 60 秒刷新一次；切换页面、读完通知时也会主动刷新。
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'

import { notificationApi } from '@/api'

export const useNotificationStore = defineStore('notifications', () => {
  const unread = ref(0)
  let timer = null

  async function refresh() {
    try {
      unread.value = (await notificationApi.unreadCount()).count
    } catch {
      /* 未登录或网络问题时保持原值，不打扰用户 */
    }
  }

  function start() {
    stop()
    refresh()
    timer = setInterval(refresh, 60_000)
  }

  function stop() {
    if (timer) clearInterval(timer)
    timer = null
    unread.value = 0
  }

  return { unread, refresh, start, stop }
})
