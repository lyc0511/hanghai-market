<!--
  投稿 / 修改投稿：网址里有 id 就是修改模式（/wall/:id/edit），只有「审核中」「未通过」的帖子能改。
  设计目标是半分钟内发完：选标签、写内容、可选加图，没有别的必填项。

  图片的处理顺序（为了匿名）：
    选图 → 在浏览器里压缩并去掉照片的隐藏信息 → 留在本地，可以点「打码」涂抹 → 点提交时才上传。
  所以原图和没打码的图都不会到服务器。
-->
<script setup>
import { Eraser, ImagePlus, Loader2, ShieldCheck, X } from '@lucide/vue'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'

import { postApi, uploadApi } from '@/api'
import ImageMaskDialog from '@/components/ImageMaskDialog.vue'
import PageHeader from '@/components/PageHeader.vue'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Textarea } from '@/components/ui/textarea'
import { prepareImage } from '@/lib/image'
import { BODY_MAX, IMAGES_MAX, WALL_RULES } from '@/lib/wall'
import { useMetaStore } from '@/stores/meta'

const route = useRoute()
const router = useRouter()
const meta = useMetaStore()

const MAX_MB = 20 // 原图的大小上限；选好后会在浏览器里压缩，实际上传的通常不到 1MB

const editId = computed(() => route.params.id ?? null)
const isEdit = computed(() => editId.value !== null)

const form = reactive({ tagId: 0, body: '' })
// 图片列表：每项 { url: 预览地址, blob: 本地处理后的图, path: 提交给后端的路径, status }
//   status：local 还在本地（可打码）/ uploading 上传中 / done 已上传 / failed 上传失败（提交时会重试）
const images = ref([])
const preparing = ref(0) // 正在本地处理的图片数
const mask = reactive({ open: false, index: -1, source: null })
const fileInput = ref()
const errors = reactive({})
const rejectReason = ref('')
const loadingPost = ref(false)
const submitting = ref(false)

const hasLocal = computed(() => images.value.some((f) => f.status === 'local'))
const bodyLength = computed(() => form.body.trim().length)

/** 详情接口返回的是完整地址，提交时要换回 /uploads/... 形式的 path */
function toPath(url) {
  const i = url.indexOf('/uploads/')
  return i >= 0 ? url.slice(i) : url
}

async function loadForEdit() {
  loadingPost.value = true
  try {
    const p = await postApi.detail(editId.value)
    if (!p.is_mine || !['pending', 'rejected'].includes(p.status)) {
      toast.error(p.is_mine ? '已上墙的帖子不能修改，如需更改请撤回后重新投稿' : '只能修改自己的投稿')
      router.replace({ name: 'my-posts' })
      return
    }
    form.tagId = p.tag?.id ?? 0
    form.body = p.body
    rejectReason.value = p.status === 'rejected' ? (p.reject_reason ?? '') : ''
    images.value = p.images.map((url) => ({ url, path: toPath(url), status: 'done' }))
  } catch {
    router.replace({ name: 'my-posts' })
  } finally {
    loadingPost.value = false
  }
}

// 选好图片后只在本地处理，不上传
async function onPick(e) {
  const picked = [...e.target.files].slice(0, IMAGES_MAX - images.value.length - preparing.value)
  e.target.value = '' // 清空，允许再次选择同一张图
  for (const file of picked) {
    if (file.size > MAX_MB * 1024 * 1024) {
      toast.error(`「${file.name}」超过 ${MAX_MB}MB`)
      continue
    }
    preparing.value += 1
    try {
      const blob = await prepareImage(file)
      images.value.push(reactive({ url: URL.createObjectURL(blob), blob, path: '', status: 'local' }))
    } catch {
      toast.error(`「${file.name}」无法处理，请换一张`)
    } finally {
      preparing.value -= 1
    }
  }
}

function openMask(i) {
  Object.assign(mask, { open: true, index: i, source: images.value[i].blob })
}

// 打码完成：用涂抹后的图替换原来那张
function onMasked(blob) {
  const entry = images.value[mask.index]
  if (!entry) return
  URL.revokeObjectURL(entry.url)
  Object.assign(entry, { blob, url: URL.createObjectURL(blob) })
}

function removeImage(i) {
  const [removed] = images.value.splice(i, 1)
  if (removed?.blob) URL.revokeObjectURL(removed.url)
}

/** 把还在本地的图片依次上传；全部成功返回 true */
async function uploadLocalImages() {
  for (const entry of images.value) {
    if (entry.status === 'done') continue
    entry.status = 'uploading'
    try {
      const { path } = await uploadApi.image(new File([entry.blob], 'wall.jpg', { type: 'image/jpeg' }))
      Object.assign(entry, { path, status: 'done' })
    } catch {
      entry.status = 'failed'
      return false
    }
  }
  return true
}

function validate() {
  for (const k of Object.keys(errors)) delete errors[k]
  if (!form.tagId) errors.tag = '选一个标签'
  if (bodyLength.value < 2) errors.body = '至少写 2 个字'
  else if (bodyLength.value > BODY_MAX) errors.body = `最多 ${BODY_MAX} 个字`
  return Object.keys(errors).length === 0
}

async function onSubmit() {
  if (submitting.value || preparing.value) return
  if (!validate()) return
  submitting.value = true
  try {
    if (!(await uploadLocalImages())) {
      errors.images = '有图片上传失败，可以再点一次提交重试，或者删掉那张图'
      return
    }
    const body = {
      tag_id: form.tagId,
      body: form.body.trim(),
      images: images.value.filter((f) => f.status === 'done').map((f) => f.path),
    }
    if (isEdit.value) await postApi.update(editId.value, body)
    else await postApi.create(body)
    toast.success(isEdit.value ? '已重新提交' : '投稿成功', { description: '审核通过后会通知你' })
    router.replace({ name: 'my-posts' })
  } catch {
    /* 提示已由 http.js 弹出 */
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  meta.load().catch(() => {})
  if (isEdit.value) loadForEdit()
})
</script>

<template>
  <div class="container narrow">
    <PageHeader :title="isEdit ? '修改投稿' : '投稿'" />

    <div v-if="loadingPost" class="space-y-4"><Skeleton class="h-10" /><Skeleton class="h-40" /></div>

    <form v-else class="space-y-6" novalidate @submit.prevent="onSubmit">
      <p v-if="rejectReason" class="rounded-lg bg-destructive/10 px-3.5 py-2.5 text-sm text-destructive">
        上次未通过的原因：{{ rejectReason }}
      </p>

      <!-- 标签 -->
      <section>
        <div class="flex flex-wrap gap-2" role="radiogroup" aria-label="标签">
          <button
            v-for="t in meta.postTags"
            :key="t.id"
            type="button"
            role="radio"
            :aria-checked="form.tagId === t.id"
            class="rounded-full border px-4 py-1.5 text-sm transition-colors"
            :class="form.tagId === t.id ? 'border-ocean bg-ocean text-white' : 'bg-white hover:border-ocean'"
            @click="form.tagId = t.id"
          >
            {{ t.name }}
          </button>
        </div>
        <p v-if="errors.tag" class="mt-2 text-sm text-destructive">{{ errors.tag }}</p>
      </section>

      <!-- 正文 -->
      <section>
        <Textarea
          v-model="form.body"
          rows="7"
          :maxlength="BODY_MAX"
          placeholder="想说点什么？写清楚时间、地点会更容易得到回应。"
          class="bg-white text-[15px] leading-relaxed"
          aria-label="正文"
          :aria-invalid="!!errors.body"
        />
        <div class="mt-1.5 flex justify-between text-xs">
          <span class="text-destructive">{{ errors.body }}</span>
          <span :class="bodyLength > BODY_MAX ? 'text-destructive' : 'text-muted-foreground'">{{ bodyLength }}/{{ BODY_MAX }}</span>
        </div>
      </section>

      <!-- 图片 -->
      <section>
        <div class="grid grid-cols-4 gap-2 sm:max-w-md">
          <div v-for="(f, i) in images" :key="f.url" class="group relative aspect-square overflow-hidden rounded-lg border bg-secondary">
            <img :src="f.url" alt="" class="size-full object-cover" :class="f.status === 'uploading' ? 'opacity-50' : ''" />
            <Loader2 v-if="f.status === 'uploading'" class="absolute inset-0 m-auto size-6 animate-spin text-ocean" />
            <span v-if="f.status === 'failed'" class="absolute inset-x-0 bottom-0 bg-destructive py-0.5 text-center text-[11px] text-white">上传失败</span>
            <!-- 只有还在本地的图能打码；已经上传过的（修改投稿时的旧图）想打码请删掉重新添加 -->
            <button
              v-else-if="f.status === 'local' && !submitting"
              type="button"
              class="absolute inset-x-0 bottom-0 flex items-center justify-center gap-1 bg-ocean/75 py-1 text-xs text-white hover:bg-ocean"
              @click="openMask(i)"
            >
              <Eraser class="size-3.5" />打码
            </button>
            <button
              v-if="!submitting"
              type="button"
              class="absolute right-1 top-1 grid size-6 place-items-center rounded-full bg-ocean/70 text-white hover:bg-ocean"
              aria-label="删除这张图"
              @click="removeImage(i)"
            >
              <X class="size-3.5" />
            </button>
          </div>
          <div v-for="n in preparing" :key="`p${n}`" class="grid aspect-square place-items-center rounded-lg border bg-secondary">
            <Loader2 class="size-5 animate-spin text-ocean" />
          </div>
          <button
            v-if="images.length + preparing < IMAGES_MAX"
            type="button"
            class="flex aspect-square flex-col items-center justify-center gap-1 rounded-lg border-2 border-dashed bg-white text-muted-foreground transition-colors hover:border-signal hover:text-signal"
            @click="fileInput.click()"
          >
            <ImagePlus class="size-5" />
            <span class="text-xs">加图片</span>
          </button>
        </div>
        <input ref="fileInput" type="file" accept="image/jpeg,image/png,image/webp" multiple class="hidden" @change="onPick" />
        <p class="mt-2 text-xs text-muted-foreground">
          选填，最多 {{ IMAGES_MAX }} 张。{{ hasLocal ? '图里有别人的头像、名字或脸？点图片下方的「打码」涂掉。' : '照片的拍摄地点等隐藏信息会自动去掉。' }}
        </p>
        <p v-if="errors.images" class="mt-1 text-sm text-destructive">{{ errors.images }}</p>
      </section>

      <!-- 匿名说明与规则 -->
      <section class="rounded-xl border bg-white px-4 py-3 text-sm">
        <p class="flex items-start gap-2 text-ocean">
          <ShieldCheck class="mt-0.5 size-4 shrink-0 text-kelp" />
          <span>投稿匿名显示，其他同学看不到是谁发的。管理员审核时能看到投稿人，用于处理违规内容。</span>
        </p>
        <p class="mt-2 pl-6 text-muted-foreground">{{ WALL_RULES }}</p>
      </section>

      <div>
        <Button type="submit" size="lg" class="h-11 w-full text-base sm:w-auto sm:px-10" :disabled="submitting || preparing > 0">
          <Loader2 v-if="submitting" class="animate-spin" />
          {{ isEdit ? '重新提交' : '提交投稿' }}
        </Button>
        <p class="mt-3 text-sm text-muted-foreground">提交后由管理员审核，通过后才会出现在墙上，结果会通过消息通知告诉你。</p>
      </div>
    </form>

    <ImageMaskDialog v-model:open="mask.open" :source="mask.source" @done="onMasked" />
  </div>
</template>
