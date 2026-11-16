<!--
  数据看板（后台首页）：待办事项 + 平台概况 + 最近 30 天趋势。
  趋势图拆成两张单系列柱状图（新增物品 / 新增意向），量级不同不放同一个坐标轴。
-->
<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { adminApi } from '@/api'

const router = useRouter()
const data = ref(null)
const loading = ref(true)
const hover = ref({ chart: null, i: -1 })

const TODOS = computed(() => {
  const d = data.value
  if (!d) return []
  return [
    { label: '待审核物品', value: d.todo_items, to: { name: 'admin-items' } },
    { label: '待审核活动', value: d.todo_activities, to: { name: 'admin-activities' } },
    { label: '待审核投稿', value: d.todo_posts, to: { name: 'admin-posts' } },
    { label: '待处理举报', value: d.todo_reports, to: { name: 'admin-reports' } },
  ]
})

const STATS = computed(() => {
  const d = data.value
  if (!d) return []
  return [
    { label: '注册用户', value: d.users_total, sub: `近 7 天新增 ${d.users_new_7d} · 封禁 ${d.users_banned}` },
    { label: '在售物品', value: d.items_online, sub: `已成交 ${d.items_sold} 件` },
    { label: '交易意向', value: d.intents_total, sub: `成交 ${d.intents_completed} 单` },
    { label: '社团', value: d.clubs_total, sub: `招新中 ${d.clubs_recruiting} 个 · 待审入社 ${d.todo_clubs}` },
    { label: '即将开始的活动', value: d.activities_upcoming, sub: `累计报名 ${d.signups_total} 人次` },
  ]
})

const CHARTS = computed(() => {
  const t = data.value?.trend ?? []
  return [
    { key: 'items', title: '每日新发布物品', unit: '件' },
    { key: 'intents', title: '每日新交易意向', unit: '个' },
  ].map((c) => {
    const values = t.map((d) => d[c.key])
    const max = Math.max(1, ...values)
    return { ...c, values, max, total: values.reduce((a, b) => a + b, 0) }
  })
})

const days = computed(() => (data.value?.trend ?? []).map((d) => d.day))

function shortDay(day) {
  const [, m, d] = day.split('-')
  return `${Number(m)}/${Number(d)}`
}

onMounted(async () => {
  try {
    data.value = await adminApi.dashboard({ days: 30 })
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div v-loading="loading" class="dash">
    <template v-if="data">
      <section class="todos">
        <button v-for="t in TODOS" :key="t.label" type="button" class="todo" :class="{ hot: t.value > 0 }" @click="router.push(t.to)">
          <span class="todo-label">{{ t.label }}</span>
          <span class="todo-value">{{ t.value }}</span>
          <span class="todo-go">{{ t.value > 0 ? '去处理 →' : '已清空' }}</span>
        </button>
      </section>

      <section class="stats">
        <div v-for="s in STATS" :key="s.label" class="stat">
          <div class="stat-label">{{ s.label }}</div>
          <div class="stat-value">{{ s.value }}</div>
          <div class="stat-sub">{{ s.sub }}</div>
        </div>
      </section>

      <section class="charts">
        <el-card v-for="c in CHARTS" :key="c.key" shadow="never" class="chart-card">
          <div class="chart-head">
            <h2>{{ c.title }}</h2>
            <span class="chart-total">近 {{ days.length }} 天共 {{ c.total }} {{ c.unit }}</span>
          </div>
          <div class="chart" role="img" :aria-label="`${c.title}，近 ${days.length} 天共 ${c.total} ${c.unit}，单日最多 ${c.max} ${c.unit}`">
            <div class="grid-line top"><span>{{ c.max }}</span></div>
            <div class="grid-line base"><span>0</span></div>
            <div class="bars" @mouseleave="hover = { chart: null, i: -1 }">
              <div
                v-for="(v, i) in c.values"
                :key="i"
                class="slot"
                @mouseenter="hover = { chart: c.key, i }"
              >
                <div class="bar" :class="{ active: hover.chart === c.key && hover.i === i }" :style="{ height: v ? `${(v / c.max) * 100}%` : '0' }" />
                <div v-if="hover.chart === c.key && hover.i === i" class="tip" :class="{ left: i > c.values.length - 6 }">
                  <div class="tip-day">{{ days[i] }}</div>
                  <div><b>{{ v }}</b> {{ c.unit }}</div>
                </div>
              </div>
            </div>
          </div>
          <div class="axis">
            <span>{{ shortDay(days[0]) }}</span>
            <span>{{ shortDay(days[Math.floor(days.length / 2)]) }}</span>
            <span>{{ shortDay(days[days.length - 1]) }}</span>
          </div>
        </el-card>
      </section>
    </template>
  </div>
</template>

<style scoped>
.dash {
  min-height: 300px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.todos {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}
.todo {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: end;
  gap: 4px 12px;
  padding: 18px 20px;
  border: 1px solid var(--line);
  border-radius: var(--r);
  background: #fff;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.15s;
}
.todo:hover {
  border-color: var(--brand);
}
.todo-label {
  color: var(--text-2);
  font-size: 13px;
}
.todo-value {
  grid-row: span 2;
  font-size: 32px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  color: var(--text-3);
}
.todo.hot .todo-value {
  color: var(--hot);
}
.todo-go {
  font-size: 12px;
  color: var(--text-3);
}
.todo.hot .todo-go {
  color: var(--brand);
}
.stats {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
}
.stat {
  padding: 16px 20px;
  border: 1px solid var(--line);
  border-radius: var(--r);
  background: #fff;
}
.stat-label {
  font-size: 13px;
  color: var(--text-2);
}
.stat-value {
  margin-top: 6px;
  font-size: 26px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  color: var(--text-1);
}
.stat-sub {
  margin-top: 4px;
  font-size: 12px;
  color: var(--text-3);
}
.charts {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.chart-card {
  border-radius: var(--r);
}
.chart-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 16px;
}
.chart-head h2 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-1);
}
.chart-total {
  font-size: 12px;
  color: var(--text-3);
}
.chart {
  position: relative;
  height: 160px;
  margin-left: 24px;
}
.grid-line {
  position: absolute;
  left: 0;
  right: 0;
  border-top: 1px solid #eef1f4;
}
.grid-line span {
  position: absolute;
  left: -24px;
  top: -8px;
  width: 18px;
  text-align: right;
  font-size: 11px;
  color: var(--text-3);
  font-variant-numeric: tabular-nums;
}
.grid-line.top {
  top: 0;
}
.grid-line.base {
  bottom: 0;
  border-top-color: #d7dee6;
}
.bars {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: flex-end;
}
/* 每天一个格子，整格都能触发悬停，比细柱子好指 */
.slot {
  position: relative;
  flex: 1;
  height: 100%;
  display: flex;
  align-items: flex-end;
  padding: 0 1px;
}
.bar {
  width: 100%;
  border-radius: 4px 4px 0 0;
  background: #1d5fd1;
  opacity: 0.85;
  transition: opacity 0.1s;
}
.bar.active {
  opacity: 1;
}
.slot:hover {
  background: rgba(29, 95, 209, 0.06);
}
.tip {
  position: absolute;
  bottom: calc(100% + 6px);
  left: 50%;
  z-index: 2;
  padding: 6px 10px;
  border-radius: 6px;
  background: #0e2a47;
  color: #fff;
  font-size: 12px;
  white-space: nowrap;
  pointer-events: none;
  transform: translateX(-50%);
}
.tip.left {
  left: auto;
  right: 0;
  transform: none;
}
.tip-day {
  color: #b9c6d6;
}
.axis {
  display: flex;
  justify-content: space-between;
  margin: 6px 0 0 24px;
  font-size: 11px;
  color: var(--text-3);
}
@media (max-width: 1100px) {
  .stats {
    grid-template-columns: repeat(3, 1fr);
  }
  .charts {
    grid-template-columns: 1fr;
  }
}
</style>
