/**
 * 接口清单：一个函数对应后端一个接口，页面里只调用这些函数，不直接写 URL。
 * 后端路径见 backend/app/api/*.py
 */
import http from './http'

export const authApi = {
  login: (studentNo, password) => http.post('/auth/login', { student_no: studentNo, password }),
  register: (body) => http.post('/auth/register', body),
  me: () => http.get('/auth/me'),
  updateMe: (body) => http.patch('/auth/me', body),
}

export const metaApi = {
  enums: () => http.get('/meta/enums'),
  categories: (type) => http.get('/meta/categories', { params: { type } }),
}

export const uploadApi = {
  /** 上传一张图片，返回 {path, url}：path 用来提交给后端，url 用来预览 */
  image(file) {
    const form = new FormData()
    form.append('file', file)
    return http.post('/upload/image', form)
  },
}

export const itemApi = {
  list: (params) => http.get('/items', { params }),
  detail: (id) => http.get(`/items/${id}`),
  mine: (params) => http.get('/items/mine', { params }),
  create: (body) => http.post('/items', body),
  update: (id, body) => http.put(`/items/${id}`, body),
  offline: (id) => http.post(`/items/${id}/offline`),
  relist: (id) => http.post(`/items/${id}/relist`),
  remove: (id) => http.delete(`/items/${id}`),
}

export const postApi = {
  list: (params) => http.get('/posts', { params }),
  /** 游客也能调用：只有数字（今天新增、总数、各标签数量），没有帖子内容 */
  summary: () => http.get('/posts/summary'),
  detail: (id) => http.get(`/posts/${id}`),
  mine: (params) => http.get('/posts/mine', { params }),
  create: (body) => http.post('/posts', body),
  update: (id, body) => http.put(`/posts/${id}`, body),
  withdraw: (id) => http.delete(`/posts/${id}`),
  like: (id) => http.post(`/posts/${id}/like`),
  unlike: (id) => http.delete(`/posts/${id}/like`),
  resolve: (id) => http.post(`/posts/${id}/resolve`),
  unresolve: (id) => http.delete(`/posts/${id}/resolve`),
  comments: (id, params) => http.get(`/posts/${id}/comments`, { params }),
  addComment: (id, body, replyToId) => http.post(`/posts/${id}/comments`, { body, reply_to_id: replyToId ?? null }),
  removeComment: (id, commentId) => http.delete(`/posts/${id}/comments/${commentId}`),
}

export const intentApi = {
  create: (itemId, message) => http.post('/intents', { item_id: itemId, message }),
  mine: (params) => http.get('/intents/mine', { params }),
  accept: (id) => http.post(`/intents/${id}/accept`),
  reject: (id) => http.post(`/intents/${id}/reject`),
  cancel: (id) => http.post(`/intents/${id}/cancel`),
  complete: (id) => http.post(`/intents/${id}/complete`),
}

export const clubApi = {
  list: (params) => http.get('/clubs', { params }),
  mine: (params) => http.get('/clubs/mine', { params }),
  detail: (id) => http.get(`/clubs/${id}`),
  update: (id, body) => http.put(`/clubs/${id}`, body),
  members: (id, params) => http.get(`/clubs/${id}/members`, { params }),
  apply: (id, reason) => http.post(`/clubs/${id}/applications`, { reason }),
  applications: (id, params) => http.get(`/clubs/${id}/applications`, { params }),
  leave: (id) => http.post(`/clubs/${id}/leave`),
  myApplications: (params) => http.get('/club-applications/mine', { params }),
  approve: (id) => http.post(`/club-applications/${id}/approve`),
  reject: (id, note) => http.post(`/club-applications/${id}/reject`, { note }),
}

export const adminApi = {
  items: (params) => http.get('/admin/items', { params }),
  approveItem: (id) => http.post(`/admin/items/${id}/approve`),
  rejectItem: (id, reason) => http.post(`/admin/items/${id}/reject`, { reason }),
  activities: (params) => http.get('/admin/activities', { params }),
  approveActivity: (id) => http.post(`/admin/activities/${id}/approve`),
  rejectActivity: (id, reason) => http.post(`/admin/activities/${id}/reject`, { reason }),
  posts: (params) => http.get('/admin/posts', { params }),
  approvePost: (id) => http.post(`/admin/posts/${id}/approve`),
  rejectPost: (id, reason) => http.post(`/admin/posts/${id}/reject`, { reason }),
  offlinePost: (id, reason) => http.post(`/admin/posts/${id}/offline`, { reason }),
  createOfficialPost: (body) => http.post('/admin/posts', body),
  pinPost: (id) => http.post(`/admin/posts/${id}/pin`),
  unpinPost: (id) => http.delete(`/admin/posts/${id}/pin`),
  reports: (params) => http.get('/admin/reports', { params }),
  handleReport: (id, data) => http.post(`/admin/reports/${id}/handle`, data),
  dashboard: (params) => http.get('/admin/dashboard', { params }),
  users: (params) => http.get('/admin/users', { params }),
  banUser: (id, data) => http.post(`/admin/users/${id}/ban`, data),
  unbanUser: (id) => http.post(`/admin/users/${id}/unban`),
  auditLogs: (params) => http.get('/admin/audit-logs', { params }),
}

export const activityApi = {
  list: (params) => http.get('/activities', { params }),
  mine: (params) => http.get('/activities/mine', { params }),
  detail: (id) => http.get(`/activities/${id}`),
  signup: (id) => http.post(`/activities/${id}/signup`),
  cancel: (id) => http.delete(`/activities/${id}/signup`),
  signups: (id, params) => http.get(`/activities/${id}/signups`, { params }),
  ofClub: (clubId, params) => http.get(`/clubs/${clubId}/activities`, { params }),
  create: (clubId, body) => http.post(`/clubs/${clubId}/activities`, body),
}


export const notificationApi = {
  list: (params) => http.get('/notifications', { params }),
  unreadCount: () => http.get('/notifications/unread-count'),
  read: (id) => http.post(`/notifications/${id}/read`),
  readAll: () => http.post('/notifications/read-all'),
}

export const reportApi = {
  create: (data) => http.post('/reports', data),
  mine: (params) => http.get('/reports/mine', { params }),
}

export const assistantApi = {
  /** 大模型可能要查好几次数据，给 60 秒超时（默认 15 秒不够） */
  chat: (sessionId, messages) => http.post('/assistant/chat', { session_id: sessionId, messages }, { timeout: 60000 }),
}
