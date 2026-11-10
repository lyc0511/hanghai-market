/**
 * AI 助手生成的发布草稿：聊天窗点「去发布页确认」时存一份，发布页打开时取出并预填表单。
 * 存在 sessionStorage（只在本标签页有效），取出后立即删除，避免下次打开发布页又被填一遍。
 */
const KEY = 'hhjs-publish-draft'

export function saveDraft(draft) {
  try {
    sessionStorage.setItem(KEY, JSON.stringify(draft))
    return true
  } catch {
    return false
  }
}

export function takeDraft() {
  try {
    const raw = sessionStorage.getItem(KEY)
    sessionStorage.removeItem(KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}
