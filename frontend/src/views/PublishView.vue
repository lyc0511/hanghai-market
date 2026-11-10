<!--
  发布 / 编辑物品：网址里有 id 就是编辑模式（/items/:id/edit），会先把原内容填进表单。
  从 AI 助手的草稿卡片过来时（?draft=时间戳），用助手整理好的内容预填，照片仍需用户自己上传。
-->
<script setup>
import { ImagePlus, Loader2, Sparkles, X } from '@lucide/vue'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'

import { itemApi, uploadApi } from '@/api'
import PageHeader from '@/components/PageHeader.vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { Textarea } from '@/components/ui/textarea'
import { takeDraft } from '@/lib/assistantDraft'
import { useMetaStore } from '@/stores/meta'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const meta = useMetaStore()
const user = useUserStore()

const MAX_IMAGES = 9
const MAX_MB = 5

// 图片列表：每项 { url: 预览地址, path: 提交给后端的路径, status: uploading | done | failed }
const images = ref([])
const fileInput = ref()
const form = reactive({
  title: '',
  summary: '',
  categoryId: '',
  price: '',
  originalPrice: '',
  condition: 'good',
  campus: user.profile?.campus_area ?? '',
  tags: '',
})
const errors = reactive({})

const editId = computed(() => route.params.id ?? null)
const isEdit = computed(() => editId.value !== null)
const loadingItem = ref(false)
const submitting = ref(false)

const conditions = computed(() => Object.entries(meta.enums?.item_condition ?? {}))
const uploading = computed(() => images.value.some((f) => f.status === 'uploading'))
const tagList = computed(() => [...new Set(form.tags.split(/[\s,，、]+/).map((t) => t.trim()).filter(Boolean))])

/** 详情接口返回的是完整地址，提交时要换回 /uploads/... 形式的 path */
function toPath(url) {
  const i = url.indexOf('/uploads/')
  return i >= 0 ? url.slice(i) : url
}

async function loadForEdit() {
  loadingItem.value = true
  try {
    const it = await itemApi.detail(editId.value)
    if (!it.is_mine) {
      toast.error('只能编辑自己发布的物品')
      router.replace({ name: 'home' })
      return
    }
    Object.assign(form, {
      title: it.title,
      summary: it.summary ?? '',
      categoryId: it.category ? String(it.category.id) : '',
      price: String(it.price),
      originalPrice: it.original_price == null ? '' : String(it.original_price),
      condition: it.condition,
      campus: it.campus_area ?? '',
      tags: it.tags.join(' '),
    })
    images.value = it.images.map((url) => ({ url, path: toPath(url), status: 'done' }))
  } catch {
    router.replace({ name: 'my-items' })
  } finally {
    loadingItem.value = false
  }
}

// AI 助手的草稿：只在「发布」模式下使用；字段已经由后端按发布规则校验过
const fromAssistant = ref(false)
function applyDraft() {
  if (isEdit.value) return
  const d = takeDraft()
  if (!d) return
  Object.assign(form, {
    title: d.title ?? '',
    summary: d.summary ?? '',
    categoryId: d.category_id ? String(d.category_id) : '',
    price: d.price == null ? '' : String(d.price),
    originalPrice: d.original_price == null ? '' : String(d.original_price),
    condition: d.condition || 'good',
    campus: d.campus_area ?? form.campus,
    tags: (d.tags ?? []).join(' '),
  })
  fromAssistant.value = true
  toast.success('已填入小航整理的内容', { description: '上传照片、检查无误后再提交' })
}

onMounted(() => {
  meta.load().catch(() => {})
  if (isEdit.value) loadForEdit()
  else applyDraft()
})
// 已经在发布页时再点草稿卡片，页面不会重新加载，靠网址里的 draft 参数变化来触发
watch(() => route.query.draft, (v) => v && applyDraft())

// 第一步：选好图片后立即上传，拿到 path
async function onPick(e) {
  const picked = [...e.target.files].slice(0, MAX_IMAGES - images.value.length)
  e.target.value = '' // 清空，允许再次选择同一张图
  for (const file of picked) {
    if (file.size > MAX_MB * 1024 * 1024) {
      toast.error(`「${file.name}」超过 ${MAX_MB}MB`)
      continue
    }
    const entry = reactive({ url: URL.createObjectURL(file), path: '', status: 'uploading' })
    images.value.push(entry)
    uploadApi
      .image(file)
      .then(({ path }) => Object.assign(entry, { path, status: 'done' }))
      .catch(() => (entry.status = 'failed'))
  }
}

function removeImage(i) {
  images.value.splice(i, 1)
}

function validate() {
  for (const k of Object.keys(errors)) delete errors[k]
  const t = form.title.trim()
  if (t.length < 2 || t.length > 60) errors.title = '标题 2–60 个字'
  if (!images.value.some((f) => f.status === 'done')) errors.images = '至少上传一张图片'
  if (!form.categoryId) errors.category = '请选择分类'
  if (form.price === '' || Number(form.price) < 0 || Number(form.price) > 99999) errors.price = '售价 0–99999，填 0 表示免费送'
  if (form.originalPrice !== '' && Number(form.originalPrice) < Number(form.price || 0)) errors.originalPrice = '原价不能低于售价'
  if (tagList.value.length > 5 || tagList.value.some((x) => x.length > 10)) errors.tags = '最多 5 个标签，每个不超过 10 字'
  return Object.keys(errors).length === 0
}

// 第一次点「发布」之后，再改任何字段都实时重新检查，改对了错误提示立刻消失
const triedSubmit = ref(false)
watch([form, images], () => triedSubmit.value && validate(), { deep: true })

// 第二步：把表单和图片 path 一起提交
async function onSubmit() {
  triedSubmit.value = true
  if (uploading.value) {
    toast('图片还在上传，稍等一下')
    return
  }
  if (!validate()) return
  submitting.value = true
  try {
    const body = {
      title: form.title.trim(),
      summary: form.summary.trim(),
      category_id: Number(form.categoryId),
      price: Number(form.price),
      original_price: form.originalPrice === '' ? null : Number(form.originalPrice),
      condition: form.condition,
      images: images.value.filter((f) => f.status === 'done').map((f) => f.path),
      tags: tagList.value,
      campus_area: form.campus || null,
    }
    if (isEdit.value) {
      await itemApi.update(editId.value, body)
      toast.success('已保存，等待管理员重新审核')
    } else {
      await itemApi.create(body)
      toast.success('已提交，等待管理员审核')
    }
    router.replace({ name: 'my-items' })
  } catch {
    /* 提示已由 http.js 弹出 */
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="container narrow">
    <PageHeader :title="isEdit ? '编辑物品' : '发布闲置'" />

    <p v-if="fromAssistant && !isEdit" class="mb-6 flex items-start gap-2 rounded-lg border border-signal/20 bg-signal/5 px-3.5 py-2.5 text-sm text-ocean">
      <Sparkles class="mt-0.5 size-4 shrink-0 text-signal" />
      <span>下面的内容由小航根据你的描述整理，请<strong class="font-medium">上传照片</strong>并核对价格、成色后再提交。提交后需要管理员审核。</span>
    </p>

    <div v-if="loadingItem" class="space-y-4"><Skeleton class="h-10" /><Skeleton class="h-32" /><Skeleton class="h-24" /></div>

    <form v-else class="space-y-8" novalidate @submit.prevent="onSubmit">
      <!-- 图片 -->
      <section>
        <Label class="text-base">照片</Label>
        <p class="mt-1 text-sm text-muted-foreground">最多 {{ MAX_IMAGES }} 张，第一张作为封面；jpg、png、webp，每张不超过 {{ MAX_MB }}MB</p>
        <div class="mt-3 grid grid-cols-3 gap-3 sm:grid-cols-5">
          <div v-for="(f, i) in images" :key="f.url" class="group relative aspect-square overflow-hidden rounded-lg border bg-secondary">
            <img :src="f.url" alt="" class="size-full object-cover" :class="f.status !== 'done' ? 'opacity-50' : ''" />
            <span v-if="i === 0" class="absolute bottom-1 left-1 rounded bg-ocean/80 px-1.5 py-0.5 text-[11px] text-white">封面</span>
            <Loader2 v-if="f.status === 'uploading'" class="absolute inset-0 m-auto size-6 animate-spin text-ocean" />
            <span v-if="f.status === 'failed'" class="absolute inset-x-0 bottom-0 bg-destructive py-0.5 text-center text-[11px] text-white">上传失败</span>
            <button
              type="button"
              class="absolute right-1 top-1 grid size-6 place-items-center rounded-full bg-ocean/70 text-white opacity-100 transition-opacity hover:bg-ocean sm:opacity-0 sm:group-hover:opacity-100"
              aria-label="删除这张图"
              @click="removeImage(i)"
            >
              <X class="size-3.5" />
            </button>
          </div>
          <button
            v-if="images.length < MAX_IMAGES"
            type="button"
            class="flex aspect-square flex-col items-center justify-center gap-1 rounded-lg border-2 border-dashed text-muted-foreground transition-colors hover:border-signal hover:text-signal"
            @click="fileInput.click()"
          >
            <ImagePlus class="size-6" />
            <span class="text-xs">添加照片</span>
          </button>
        </div>
        <input ref="fileInput" type="file" accept="image/jpeg,image/png,image/webp" multiple class="hidden" @change="onPick" />
        <p v-if="errors.images" class="mt-2 text-sm text-destructive">{{ errors.images }}</p>
      </section>

      <!-- 标题与描述 -->
      <section class="space-y-4">
        <div class="space-y-1.5">
          <Label for="title" class="text-base">标题</Label>
          <Input id="title" v-model="form.title" maxlength="60" placeholder="品牌型号和新旧程度，一句话说清楚" class="h-11 text-base" :aria-invalid="!!errors.title" />
          <p v-if="errors.title" class="text-sm text-destructive">{{ errors.title }}</p>
        </div>
        <div class="space-y-1.5">
          <Label for="summary">描述（选填）</Label>
          <Textarea id="summary" v-model="form.summary" rows="4" maxlength="300" placeholder="使用情况、入手渠道、转手原因、交易方式……" />
          <p class="text-right text-xs text-muted-foreground">{{ form.summary.length }}/300</p>
        </div>
      </section>

      <!-- 价格与属性 -->
      <section class="grid gap-x-6 gap-y-5 sm:grid-cols-2">
        <div class="space-y-1.5">
          <Label for="price">售价</Label>
          <div class="relative">
            <span class="absolute left-3 top-1/2 -translate-y-1/2 font-semibold text-buoy">¥</span>
            <Input id="price" v-model="form.price" type="number" inputmode="decimal" min="0" placeholder="填 0 表示免费送" class="h-10 pl-7" :aria-invalid="!!errors.price" />
          </div>
          <p v-if="errors.price" class="text-sm text-destructive">{{ errors.price }}</p>
        </div>
        <div class="space-y-1.5">
          <Label for="original">原价（选填）</Label>
          <div class="relative">
            <span class="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">¥</span>
            <Input id="original" v-model="form.originalPrice" type="number" inputmode="decimal" min="0" placeholder="买的时候多少钱" class="h-10 pl-7" :aria-invalid="!!errors.originalPrice" />
          </div>
          <p v-if="errors.originalPrice" class="text-sm text-destructive">{{ errors.originalPrice }}</p>
        </div>
        <div class="space-y-1.5">
          <Label>分类</Label>
          <Select v-model="form.categoryId">
            <SelectTrigger class="h-10 w-full" :aria-invalid="!!errors.category"><SelectValue placeholder="选择分类" /></SelectTrigger>
            <SelectContent>
              <SelectItem v-for="c in meta.itemCategories" :key="c.id" :value="String(c.id)">{{ c.name }}</SelectItem>
            </SelectContent>
          </Select>
          <p v-if="errors.category" class="text-sm text-destructive">{{ errors.category }}</p>
        </div>
        <div class="space-y-1.5">
          <Label>交易校区</Label>
          <Select v-model="form.campus">
            <SelectTrigger class="h-10 w-full"><SelectValue placeholder="选择校区" /></SelectTrigger>
            <SelectContent>
              <SelectItem v-for="c in meta.enums?.campus_area ?? []" :key="c" :value="c">{{ c }}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div class="space-y-1.5 sm:col-span-2">
          <Label>成色</Label>
          <div class="flex flex-wrap gap-2" role="radiogroup" aria-label="成色">
            <button
              v-for="[v, t] in conditions"
              :key="v"
              type="button"
              role="radio"
              :aria-checked="form.condition === v"
              class="rounded-full border px-4 py-1.5 text-sm transition-colors"
              :class="form.condition === v ? 'border-ocean bg-ocean text-white' : 'hover:border-ocean'"
              @click="form.condition = v"
            >
              {{ t }}
            </button>
          </div>
        </div>
        <div class="space-y-1.5 sm:col-span-2">
          <Label for="tags">标签（选填）</Label>
          <Input id="tags" v-model="form.tags" placeholder="用空格分隔，如：考研 数学" class="h-10" :aria-invalid="!!errors.tags" />
          <p v-if="errors.tags" class="text-sm text-destructive">{{ errors.tags }}</p>
        </div>
      </section>

      <div class="border-t pt-6">
        <Button type="submit" size="lg" class="h-11 w-full text-base sm:w-auto sm:px-10" :disabled="submitting || uploading">
          <Loader2 v-if="submitting" class="animate-spin" />
          {{ isEdit ? '保存并重新提交审核' : '发布' }}
        </Button>
        <p class="mt-3 text-sm text-muted-foreground">
          {{ isEdit ? '修改后需要重新审核；进行中的交易意向会自动关闭并通知买家。' : '发布后需要管理员审核，通过后其他同学才能看到。' }}
        </p>
      </div>
    </form>
  </div>
</template>
