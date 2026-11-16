/** 通知类型 → 图标颜色分组，让「好消息」「需要处理」「被拒绝」一眼能分开 */
const GOOD = new Set(['intent_accepted', 'intent_completed', 'content_approved', 'club_approved', 'report_resolved'])
const TODO = new Set(['intent_new', 'club_apply', 'post_comment', 'comment_reply'])
const BAD = new Set(['intent_rejected', 'intent_closed', 'content_rejected', 'club_rejected', 'content_takedown', 'report_dismissed'])

export function toneOf(type) {
  if (GOOD.has(type)) return 'bg-kelp'
  if (TODO.has(type)) return 'bg-buoy'
  if (BAD.has(type)) return 'bg-destructive'
  return 'bg-signal'
}
