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

export const itemApi = {
  list: (params) => http.get('/items', { params }),
  detail: (id) => http.get(`/items/${id}`),
  mine: (params) => http.get('/items/mine', { params }),
  create: (body) => http.post('/items', body),
}

export const intentApi = {
  create: (itemId, message) => http.post('/intents', { item_id: itemId, message }),
}
