<!--
  图片打码：用手指或鼠标在图片上涂抹，涂过的地方变成马赛克。用来盖住聊天截图里的头像、名字、人脸。
  用法：<ImageMaskDialog v-model:open="open" :source="blob" @done="(newBlob) => ..." />

  做法：先把整张图缩小再放大，得到一张「全图马赛克」备用；涂抹时把笔刷经过的圆形区域换成这张备用图上的同一块。
  撤销不保存整张图的快照（太占内存），而是记录每一笔的轨迹，撤销时从原图开始把剩下的笔画重画一遍。
  全程在浏览器里完成，点「完成」后交给调用方的是已经打好码的图。
-->
<script setup>
import { Loader2, RotateCcw, Undo2 } from '@lucide/vue'
import { nextTick, ref, watch } from 'vue'
import { toast } from 'vue-sonner'

import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogTitle } from '@/components/ui/dialog'
import { canvasToJpeg, loadImage } from '@/lib/image'

const props = defineProps({
  open: { type: Boolean, default: false },
  source: { type: Object, default: null }, // Blob
})
const emit = defineEmits(['update:open', 'done'])

// 笔刷半径占图片长边的比例
const BRUSHES = [
  { value: 0.022, label: '细' },
  { value: 0.045, label: '中' },
  { value: 0.08, label: '粗' },
]

const canvas = ref()
const brush = ref(BRUSHES[1].value)
const strokeCount = ref(0)
const loading = ref(false)
const saving = ref(false)

let original = null // 原图 <img>
let mosaic = null // 全图马赛克（离屏 canvas）
let strokes = [] // 每一笔：{ r, points: [[x, y], ...] }
let current = null // 正在画的这一笔
let ctx = null

async function setup() {
  loading.value = true
  strokes = []
  strokeCount.value = 0
  try {
    original = await loadImage(props.source)
    await nextTick()
    const c = canvas.value
    const w = (c.width = original.naturalWidth)
    const h = (c.height = original.naturalHeight)
    ctx = c.getContext('2d')
    ctx.drawImage(original, 0, 0)

    // 马赛克块要足够大：一个头像、一行名字会被平均成几个色块，看不出原来的内容
    const block = Math.max(16, Math.round(Math.max(w, h) / 32))
    const small = document.createElement('canvas')
    small.width = Math.max(1, Math.ceil(w / block))
    small.height = Math.max(1, Math.ceil(h / block))
    small.getContext('2d').drawImage(original, 0, 0, small.width, small.height)
    mosaic = document.createElement('canvas')
    mosaic.width = w
    mosaic.height = h
    const mctx = mosaic.getContext('2d')
    mctx.imageSmoothingEnabled = false
    mctx.drawImage(small, 0, 0, w, h)
  } catch {
    toast.error('这张图片无法处理，请换一张')
    emit('update:open', false)
  } finally {
    loading.value = false
  }
}

watch(
  () => props.open,
  (v) => v && props.source && setup(),
)

/** 屏幕上的触点位置 → 图片上的像素坐标（图片在屏幕上是缩小显示的） */
function toImagePoint(e) {
  const rect = canvas.value.getBoundingClientRect()
  const k = canvas.value.width / rect.width
  return [(e.clientX - rect.left) * k, (e.clientY - rect.top) * k]
}

function stamp(x, y, r) {
  ctx.save()
  ctx.beginPath()
  ctx.arc(x, y, r, 0, Math.PI * 2)
  ctx.clip()
  ctx.drawImage(mosaic, x - r, y - r, r * 2, r * 2, x - r, y - r, r * 2, r * 2)
  ctx.restore()
}

/** 从上一个点到这个点之间补上若干个圆，手指划得快也不会留下空隙 */
function drawSegment(from, to, r) {
  const dist = Math.hypot(to[0] - from[0], to[1] - from[1])
  const steps = Math.max(1, Math.ceil(dist / (r / 2)))
  for (let i = 1; i <= steps; i += 1) {
    stamp(from[0] + ((to[0] - from[0]) * i) / steps, from[1] + ((to[1] - from[1]) * i) / steps, r)
  }
}

function onDown(e) {
  if (loading.value || !ctx) return
  e.preventDefault()
  // 捕获指针：手指滑出图片范围后松开，也能收到「抬起」事件。个别浏览器不支持时忽略即可
  try {
    canvas.value.setPointerCapture(e.pointerId)
  } catch {
    /* 不影响涂抹 */
  }
  const p = toImagePoint(e)
  current = { r: Math.max(canvas.value.width, canvas.value.height) * brush.value, points: [p] }
  stamp(p[0], p[1], current.r)
}

function onMove(e) {
  if (!current) return
  e.preventDefault()
  const p = toImagePoint(e)
  drawSegment(current.points.at(-1), p, current.r)
  current.points.push(p)
}

function onUp() {
  if (!current) return
  strokes.push(current)
  strokeCount.value = strokes.length
  current = null
}

function redraw() {
  ctx.drawImage(original, 0, 0)
  for (const s of strokes) {
    stamp(s.points[0][0], s.points[0][1], s.r)
    for (let i = 1; i < s.points.length; i += 1) drawSegment(s.points[i - 1], s.points[i], s.r)
  }
  strokeCount.value = strokes.length
}

function undo() {
  strokes.pop()
  redraw()
}

function reset() {
  strokes = []
  redraw()
}

async function finish() {
  saving.value = true
  try {
    emit('done', await canvasToJpeg(canvas.value))
    emit('update:open', false)
  } catch {
    toast.error('图片导出失败，请重试')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <Dialog :open="open" @update:open="(v) => emit('update:open', v)">
    <DialogContent class="sm:max-w-2xl">
      <DialogTitle>给图片打码</DialogTitle>
      <DialogDescription>在需要遮住的地方涂抹，比如聊天截图里的头像和名字、照片里别人的脸。</DialogDescription>

      <div class="relative grid min-h-40 place-items-center overflow-hidden rounded-lg bg-secondary">
        <!-- touch-none：在图片上滑动手指是涂抹，不是滚动页面 -->
        <canvas
          ref="canvas"
          class="block max-h-[55vh] max-w-full cursor-crosshair touch-none select-none"
          @pointerdown="onDown"
          @pointermove="onMove"
          @pointerup="onUp"
          @pointercancel="onUp"
        />
        <Loader2 v-if="loading" class="absolute size-6 animate-spin text-ocean" />
      </div>

      <div class="flex flex-wrap items-center gap-x-4 gap-y-2">
        <div class="flex items-center gap-1.5" role="radiogroup" aria-label="笔刷粗细">
          <span class="text-sm text-muted-foreground">笔刷</span>
          <button
            v-for="b in BRUSHES"
            :key="b.value"
            type="button"
            role="radio"
            :aria-checked="brush === b.value"
            class="rounded-full border px-3 py-1 text-sm transition-colors"
            :class="brush === b.value ? 'border-ocean bg-ocean text-white' : 'hover:border-ocean'"
            @click="brush = b.value"
          >
            {{ b.label }}
          </button>
        </div>
        <div class="ml-auto flex gap-2">
          <Button variant="outline" size="sm" :disabled="!strokeCount" @click="undo"><Undo2 />撤销</Button>
          <Button variant="outline" size="sm" :disabled="!strokeCount" @click="reset"><RotateCcw />重置</Button>
        </div>
      </div>

      <DialogFooter>
        <Button variant="outline" @click="emit('update:open', false)">取消</Button>
        <Button :disabled="loading || saving" @click="finish"><Loader2 v-if="saving" class="animate-spin" />完成</Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
