<!--
  活动航班表：像码头班次表一样一行一场活动。
  首页、活动列表、我报名的活动共用。compact 时隐藏地点列（首页用）。
-->
<script setup>
import { monthDay, signupState, TONE_CLASS, weekTime } from '@/lib/activity'

defineProps({
  items: { type: Array, required: true },
  compact: { type: Boolean, default: false },
  emptyText: { type: String, default: '暂时没有活动' },
})
</script>

<template>
  <table class="w-full text-left text-sm">
    <thead class="border-y text-muted-foreground">
      <tr>
        <th class="w-24 py-2 font-normal">日期</th>
        <th class="py-2 font-normal">活动</th>
        <th v-if="!compact" class="hidden w-40 py-2 font-normal md:table-cell">地点</th>
        <th class="w-24 py-2 text-right font-normal">名额</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="a in items" :key="a.id" class="group border-b">
        <td class="py-3 align-top">
          <router-link :to="{ name: 'activity', params: { id: a.id } }" class="block">
            <span class="font-display text-xl tabular-nums text-ocean">{{ monthDay(a.start_time) }}</span>
            <span class="block text-xs text-muted-foreground">{{ weekTime(a.start_time) }}</span>
          </router-link>
        </td>
        <td class="py-3 align-top">
          <router-link :to="{ name: 'activity', params: { id: a.id } }" class="block">
            <span class="font-medium text-ocean group-hover:text-signal">{{ a.title }}</span>
            <span class="mt-0.5 block text-xs text-muted-foreground">{{ a.club.title }}</span>
          </router-link>
        </td>
        <td v-if="!compact" class="hidden py-3 align-top text-muted-foreground md:table-cell">{{ a.location }}</td>
        <td class="py-3 text-right align-top">
          <span class="tabular-nums text-ocean">{{ a.enrolled_count }}/{{ a.capacity }}</span>
          <span class="mt-1 block">
            <span class="rounded px-1.5 py-0.5 text-xs" :class="TONE_CLASS[signupState(a).tone]">{{ signupState(a).text }}</span>
          </span>
        </td>
      </tr>
      <tr v-if="!items.length">
        <td :colspan="compact ? 3 : 4" class="border-b py-10 text-center text-muted-foreground">{{ emptyText }}</td>
      </tr>
    </tbody>
  </table>
</template>
