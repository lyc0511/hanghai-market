<!--
  墙上的一条帖子。信息流和详情页共用：
    clamp  = true 时正文最多显示 6 行（信息流里用），点正文进详情
  匿名：帖子数据里本来就没有投稿人信息，这里统一显示「匿名同学」。
-->
<script setup>
import { CircleCheck, Heart, MessageCircle, Megaphone, Pin, UserRound } from '@lucide/vue'
import { computed } from 'vue'

import { tagClass } from '@/lib/wall'
import { timeAgo } from '@/lib/time'

const props = defineProps({
  post: { type: Object, required: true },
  clamp: { type: Boolean, default: false },
})

// 1 张图放大显示；2 张或 4 张排两列；3 张排三列
const gridClass = computed(() => {
  const n = props.post.images.length
  if (n === 1) return 'grid-cols-1 max-w-sm'
  return n === 3 ? 'grid-cols-3' : 'grid-cols-2 max-w-md'
})
</script>

<template>
  <article class="rounded-2xl border bg-white p-4 sm:p-5">
    <header class="flex items-center gap-3">
      <span
        class="grid size-10 shrink-0 place-items-center rounded-full"
        :class="post.is_official ? 'bg-signal text-white' : 'bg-secondary text-ocean/50'"
        aria-hidden="true"
      >
        <Megaphone v-if="post.is_official" class="size-5" />
        <UserRound v-else class="size-5" />
      </span>
      <div class="min-w-0 flex-1">
        <div class="flex items-center gap-1.5 text-[15px] font-medium text-ocean">
          {{ post.is_official ? '官方' : '匿名同学' }}
          <span v-if="post.is_mine" class="rounded bg-ocean/10 px-1.5 py-px text-[11px] font-normal text-ocean">我</span>
          <span v-if="post.pinned" class="inline-flex items-center gap-0.5 text-xs font-normal text-buoy"><Pin class="size-3" />置顶</span>
        </div>
        <div class="text-xs text-muted-foreground">
          {{ post.published_at ? timeAgo(post.published_at) : '尚未上墙' }}
        </div>
      </div>
      <span v-if="post.tag" class="shrink-0 rounded-full px-2.5 py-1 text-xs font-medium" :class="tagClass(post.tag.slug)">
        {{ post.tag.name }}
      </span>
    </header>

    <component
      :is="clamp ? 'router-link' : 'div'"
      :to="clamp ? { name: 'wall-post', params: { id: post.id } } : undefined"
      class="mt-3 block"
    >
      <p class="whitespace-pre-line break-words text-[15px] leading-relaxed text-foreground" :class="clamp ? 'line-clamp-6' : ''">
        {{ post.body }}
      </p>
    </component>

    <div v-if="post.images.length" class="mt-3 grid gap-1.5" :class="gridClass">
      <a
        v-for="src in post.images"
        :key="src"
        :href="src"
        target="_blank"
        rel="noopener"
        class="block overflow-hidden rounded-lg border bg-secondary"
        :class="post.images.length === 1 ? '' : 'aspect-square'"
        aria-label="查看大图"
      >
        <img :src="src" alt="" loading="lazy" class="size-full object-cover" :class="post.images.length === 1 ? 'max-h-96' : ''" />
      </a>
    </div>

    <footer class="mt-3 flex items-center gap-5 text-sm text-muted-foreground">
      <span class="inline-flex items-center gap-1.5"><Heart class="size-4" />{{ post.like_count || '赞' }}</span>
      <span class="inline-flex items-center gap-1.5"><MessageCircle class="size-4" />{{ post.comment_count || '评论' }}</span>
      <span v-if="post.resolved" class="ml-auto inline-flex items-center gap-1 text-kelp"><CircleCheck class="size-4" />已解决</span>
    </footer>
  </article>
</template>
