/**
 * 全站共用的确认弹窗。
 * 用法：if (await confirm({ title: '下架物品', message: '……', confirmText: '下架' })) { ... }
 * 弹窗本身由 App.vue 里的 <ConfirmHost /> 负责显示。
 */
import { reactive } from 'vue'

export const confirmState = reactive({
  open: false,
  title: '',
  message: '',
  confirmText: '确定',
  danger: false,
  resolve: null,
})

export function confirm({ title, message = '', confirmText = '确定', danger = false }) {
  // 上一个还没答复就弹新的：按「取消」处理旧的
  confirmState.resolve?.(false)
  Object.assign(confirmState, { open: true, title, message, confirmText, danger })
  return new Promise((resolve) => {
    confirmState.resolve = resolve
  })
}

export function answerConfirm(ok) {
  confirmState.resolve?.(ok)
  confirmState.resolve = null
  confirmState.open = false
}
