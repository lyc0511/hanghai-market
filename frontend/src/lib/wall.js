/**
 * 校园墙的显示规则：标签颜色、帖子状态的文字和颜色。
 * 标签本身（名字、顺序）来自后端 categories 表，这里只按 slug 配颜色；没配到的用「其他」的灰色。
 */
const TAG_CLASS = {
  lost_found: 'bg-buoy/10 text-[#B44A10]',
  help: 'bg-signal/10 text-signal',
  buddy: 'bg-kelp/10 text-kelp',
  confession: 'bg-rose-50 text-rose-600',
  rant: 'bg-violet-50 text-violet-600',
  other: 'bg-secondary text-muted-foreground',
}

export function tagClass(slug) {
  return TAG_CLASS[slug] ?? TAG_CLASS.other
}

/** 帖子状态 → [文字, 颜色] */
export const POST_STATUS = {
  pending: ['审核中', 'bg-buoy/10 text-[#B44A10]'],
  online: ['已上墙', 'bg-kelp/10 text-kelp'],
  rejected: ['未通过', 'bg-destructive/10 text-destructive'],
  offline: ['已下架', 'bg-secondary text-muted-foreground'],
}

export const BODY_MAX = 500
export const IMAGES_MAX = 4

/** 投稿页和详情页共用的社区规则 */
export const WALL_RULES = '不挂人，不发他人隐私（姓名、宿舍、联系方式），不发广告。图片里有别人的头像或名字，请先打码。'
