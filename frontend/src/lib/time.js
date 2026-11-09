/**
 * 时间显示工具。
 * 平台在广州，所有时间一律按北京时间显示和输入，不跟随浏览器所在时区——
 * 否则时区设置不同的电脑会看到错误的活动时间（例如设成悉尼时区会快 3 小时）。
 */
const TZ = 'Asia/Shanghai'
const WEEK = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']

const partsFmt = new Intl.DateTimeFormat('en-US', {
  timeZone: TZ,
  year: 'numeric',
  month: 'numeric',
  day: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  weekday: 'short',
  hourCycle: 'h23',
})
const WEEK_EN = { Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6 }

/** 拆出北京时间的年月日时分和星期：{ y, m, d, hh, mm, week } */
export function bj(iso) {
  const p = Object.fromEntries(partsFmt.formatToParts(new Date(iso)).map((x) => [x.type, x.value]))
  return { y: Number(p.year), m: Number(p.month), d: Number(p.day), hh: p.hour, mm: p.minute, week: WEEK[WEEK_EN[p.weekday]] }
}

/** 2026/11/11 */
export function formatDate(iso) {
  const t = bj(iso)
  return `${t.y}/${t.m}/${t.d}`
}

/** 2026/11/11 19:00 */
export function formatDateTime(iso) {
  const t = bj(iso)
  return `${t.y}/${t.m}/${t.d} ${t.hh}:${t.mm}`
}

/** 相对时间：刚刚 / 5 分钟前 / 3 小时前 / 2 天前，超过 30 天显示日期 */
export function timeAgo(iso) {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000
  if (diff < 60) return '刚刚'
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`
  if (diff < 86400 * 30) return `${Math.floor(diff / 86400)} 天前`
  return formatDate(iso)
}

/**
 * <input type="datetime-local"> 的值（如 2026-11-20T19:00）按北京时间理解，
 * 转成带时区的 ISO 字符串 2026-11-20T19:00:00+08:00；空值返回 null。
 */
export function beijingInputToIso(v) {
  return v ? `${v}:00+08:00` : null
}
