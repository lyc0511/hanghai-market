<!-- 物品卡片：首页货架和二手市场网格共用 -->
<script setup>
import { ImageOff } from '@lucide/vue'

import { useMetaStore } from '@/stores/meta'

defineProps({ item: { type: Object, required: true } })
const meta = useMetaStore()
</script>

<template>
  <router-link :to="{ name: 'item', params: { id: item.id } }" class="group block">
    <div class="relative aspect-square overflow-hidden rounded-lg border bg-secondary transition-colors group-hover:border-signal/40">
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
    <div class="mt-2 space-y-1">
      <h3 class="truncate text-sm text-ocean group-hover:text-signal">{{ item.title }}</h3>
      <div class="flex items-baseline gap-2">
        <span v-if="item.price === 0" class="text-sm font-semibold text-kelp">免费送</span>
        <span v-else class="text-lg font-semibold tabular-nums text-buoy">¥{{ item.price }}</span>
        <span v-if="item.original_price && item.original_price > item.price" class="text-xs text-muted-foreground line-through">
          ¥{{ item.original_price }}
        </span>
      </div>
      <p class="truncate text-xs text-muted-foreground">
        {{ meta.label('item_condition', item.condition) }}<template v-if="item.campus_area">，{{ item.campus_area }}</template>
      </p>
    </div>
  </router-link>
</template>
