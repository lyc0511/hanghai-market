/** 活动相关的显示工具：日期格式、报名状态文案。时间一律按北京时间显示（见 lib/time.js）。 */
import { beijingInputToIso, bj } from '@/lib/time'

/** 11/15 */
export function monthDay(iso) {
  const t = bj(iso)
  return `${t.m}/${t.d}`
}

/** 周六 19:00 */
export function weekTime(iso) {
  const t = bj(iso)
  return `${t.week} ${t.hh}:${t.mm}`
}

/** 11 月 15 日 周六 19:00–22:00（跨天时显示两个日期） */
export function timeRange(startIso, endIso) {
  const s = bj(startIso)
  const e = bj(endIso)
  const head = `${s.m} 月 ${s.d} 日 ${s.week} ${s.hh}:${s.mm}`
  const sameDay = s.y === e.y && s.m === e.m && s.d === e.d
  const tail = sameDay ? `${e.hh}:${e.mm}` : `${e.m} 月 ${e.d} 日 ${e.hh}:${e.mm}`
  return `${head}–${tail}`
}

/**
 * 报名状态：{ text, tone }
 * tone 决定颜色：open 可报名（海藻绿）/ full 已满（浮标橙）/ muted 不可报名（灰）/ review 审核相关
 */
export function signupState(a) {
  if (a.status === 'pending') return { text: '待审核', tone: 'review' }
  if (a.status === 'rejected') return { text: '未通过', tone: 'rejected' }
  if (a.phase === 'ended') return { text: '已结束', tone: 'muted' }
  if (a.phase === 'ongoing') return { text: '进行中', tone: 'muted' }
  if (a.enrolled_count >= a.capacity) return { text: '已满员', tone: 'full' }
  if (!a.signup_open) return { text: '报名已截止', tone: 'muted' }
  return { text: '报名中', tone: 'open' }
}

export const TONE_CLASS = {
  open: 'bg-kelp/10 text-kelp',
  full: 'bg-buoy/10 text-[#B44A10]',
  muted: 'bg-secondary text-muted-foreground',
  review: 'bg-signal/10 text-signal',
  rejected: 'bg-destructive/10 text-destructive',
}

/** 发布表单里填的时间按北京时间理解 */
export const localToIso = beijingInputToIso
