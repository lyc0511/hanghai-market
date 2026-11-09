<!-- 物品卡片：首页两列网格里的一格 -->
<script setup>
import { useMetaStore } from '@/stores/meta'

defineProps({ item: { type: Object, required: true } })
const meta = useMetaStore()
</script>

<template>
  <router-link :to="{ name: 'item', params: { id: item.id } }" class="card">
    <van-image :src="item.cover" fit="cover" class="cover" loading="lazy">
      <template #error>
        <div class="placeholder"><van-icon name="photo-o" /></div>
      </template>
      <template #loading>
        <div class="placeholder"><van-loading size="20" /></div>
      </template>
    </van-image>
    <div class="body">
      <h3 class="title line-2">{{ item.title }}</h3>
      <div class="price-row">
        <span v-if="item.price === 0" class="free">免费送</span>
        <span v-else class="price">{{ item.price }}</span>
        <span v-if="item.original_price && item.original_price > item.price" class="original">
          ¥{{ item.original_price }}
        </span>
      </div>
      <div class="meta">
        <span class="tag">{{ meta.label('item_condition', item.condition) }}</span>
        <span class="campus line-1">{{ item.campus_area }}</span>
      </div>
    </div>
  </router-link>
</template>

<style scoped>
.card {
  display: block;
  background: var(--bg-card);
  border-radius: var(--radius);
  overflow: hidden;
  box-shadow: var(--shadow-card);
  transition: transform 0.15s ease;
}
.card:active {
  transform: scale(0.98);
}

.cover {
  display: block;
  width: 100%;
  aspect-ratio: 1 / 1;
  background: var(--brand-soft);
}
.placeholder {
  width: 100%;
  height: 100%;
  display: grid;
  place-items: center;
  color: var(--brand);
  opacity: 0.45;
  font-size: 32px;
}

.body {
  padding: 8px 10px 10px;
}
.title {
  margin: 0;
  font-size: 14px;
  font-weight: 500;
  line-height: 1.4;
  min-height: 2.8em;
}
.price-row {
  margin-top: 6px;
  display: flex;
  align-items: baseline;
  gap: 6px;
}
.price {
  font-size: 17px;
}
.free {
  color: var(--success);
  font-weight: 600;
  font-size: 14px;
}
.original {
  color: var(--text-3);
  font-size: 12px;
  text-decoration: line-through;
}
.meta {
  margin-top: 6px;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--text-3);
}
.tag {
  flex-shrink: 0;
  padding: 1px 6px;
  border-radius: 4px;
  background: var(--brand-soft);
  color: var(--brand-dark);
}
</style>
