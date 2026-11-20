<!-- 板块页头：统一二手市场、社团目录、活动航班表、校园墙的顶部视觉与操作入口 -->
<script setup>
defineProps({
  eyebrow: { type: String, default: '' },
  title: { type: String, required: true },
  description: { type: String, default: '' },
})
</script>

<template>
  <section class="harbor-grid relative overflow-hidden rounded-2xl border bg-white px-5 py-5 sm:px-6 sm:py-6">
    <span class="pointer-events-none absolute inset-y-0 left-0 w-1 bg-ocean" aria-hidden="true" />
    <div class="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div class="min-w-0">
        <div v-if="eyebrow" class="mb-1.5 inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
          <span class="size-1.5 rounded-full bg-buoy" aria-hidden="true" />
          <span>{{ eyebrow }}</span>
        </div>
        <h1 class="font-display text-3xl leading-tight text-ocean sm:text-4xl">{{ title }}</h1>
        <p v-if="description || $slots.description" class="mt-1.5 text-sm text-muted-foreground">
          <slot name="description">{{ description }}</slot>
        </p>
      </div>
      <div v-if="$slots.actions" class="flex shrink-0 flex-wrap items-center gap-2">
        <slot name="actions" />
      </div>
    </div>
  </section>
</template>
