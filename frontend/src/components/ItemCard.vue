<!-- 物品卡片：首页货架和二手市场网格共用 -->
<script setup>
import { ImageOff } from '@lucide/vue'

import { timeAgo } from '@/lib/time'
import { useMetaStore } from '@/stores/meta'

defineProps({
  item: { type: Object, required: true },
  variant: { type: String, default: 'default' },
})
const meta = useMetaStore()
</script>

<template>
  <router-link :to="{ name: 'item', params: { id: item.id } }" class="group block min-w-0">
    <div
      class="relative overflow-hidden transition-colors"
      :class="variant === 'home'
        ? 'aspect-[168/145] rounded-lg bg-[#E7F2F7] sm:aspect-[273/188]'
        : 'aspect-square rounded-lg border bg-secondary group-hover:border-signal/40'"
    >
      <img
        v-if="item.cover"
        :src="item.cover"
        :alt="item.title"
        loading="lazy"
        class="relative z-10 size-full object-cover"
        @error="(e) => (e.target.style.display = 'none')"
      />
      <!-- 图片缺失或加载失败时露出下面的占位图标 -->
      <ImageOff class="absolute inset-0 m-auto size-7 text-ocean/25" aria-hidden="true" />
    </div>
    <div :class="variant === 'home' ? 'mt-2.5 space-y-2' : 'mt-2 space-y-1'">
      <h3
        class="min-w-0 text-sm group-hover:text-signal"
        :class="variant === 'home' ? 'line-clamp-2 font-medium text-[#0E2A47] sm:line-clamp-1 sm:text-[15px]' : 'truncate text-ocean'"
      >{{ item.title }}</h3>
      <div class="flex items-baseline gap-2">
        <span v-if="item.price === 0" class="font-semibold" :class="variant === 'home' ? 'text-lg text-[#2B8897]' : 'text-sm text-kelp'">免费送</span>
        <span v-else class="font-semibold tabular-nums" :class="variant === 'home' ? 'text-xl text-[#C65D36] sm:text-[22px]' : 'text-lg text-buoy'">¥ {{ item.price }}</span>
        <span v-if="variant !== 'home' && item.original_price && item.original_price > item.price" class="text-xs text-muted-foreground line-through">
          ¥{{ item.original_price }}
        </span>
        <span v-if="variant === 'home' && item.created_at" class="ml-auto truncate text-[11px] text-[#607487]">{{ timeAgo(item.created_at) }}</span>
      </div>
      <p class="truncate text-xs" :class="variant === 'home' ? 'text-[#607487]' : 'text-muted-foreground'">
        {{ meta.label('item_condition', item.condition) }}<template v-if="item.campus_area"> · {{ item.campus_area }}</template>
      </p>
    </div>
  </router-link>
</template>
