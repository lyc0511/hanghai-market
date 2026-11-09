<!--
  社团详情页里的「社团活动」区块：列出这个社团的活动；会长还能看到待审核 / 被驳回的，并能发布新活动。
  发布后进入待审核，管理员在后台「活动审核」里通过后才对所有人可见。
-->
<script setup>
import { Loader2, Plus } from '@lucide/vue'
import { onMounted, reactive, ref, watch } from 'vue'
import { toast } from 'vue-sonner'

import { activityApi } from '@/api'
import ActivityTable from '@/components/ActivityTable.vue'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { localToIso } from '@/lib/activity'

const props = defineProps({
  clubId: { type: [Number, String], required: true },
  isPresident: { type: Boolean, default: false },
})

const items = ref([])
const open = ref(false)
const saving = ref(false)
const form = reactive({ title: '', summary: '', location: '', start: '', end: '', deadline: '', capacity: '', tags: '' })
const errors = reactive({})

async function load() {
  try {
    items.value = (await activityApi.ofClub(props.clubId, { page_size: 50 })).items
  } catch {
    items.value = []
  }
}
onMounted(load)
// 会长身份变化（登录 / 退出）时，能看到的活动范围也会变
watch(() => [props.clubId, props.isPresident], load)

function openForm() {
  Object.assign(form, { title: '', summary: '', location: '', start: '', end: '', deadline: '', capacity: '', tags: '' })
  for (const k of Object.keys(errors)) delete errors[k]
  open.value = true
}

function validate() {
  for (const k of Object.keys(errors)) delete errors[k]
  const now = Date.now()
  if (form.title.trim().length < 2 || form.title.trim().length > 60) errors.title = '活动名称 2–60 个字'
  if (!form.location.trim()) errors.location = '请填写地点'
  // 输入框里的时间按北京时间理解，转成时间戳再比较
  const at = (v) => new Date(localToIso(v)).getTime()
  if (!form.start || at(form.start) <= now) errors.start = '开始时间要晚于现在（北京时间）'
  if (!form.end || (form.start && at(form.end) <= at(form.start))) errors.end = '结束时间要晚于开始时间'
  if (form.deadline && form.start && at(form.deadline) > at(form.start)) errors.deadline = '截止时间不能晚于开始时间'
  const cap = Number(form.capacity)
  if (!Number.isInteger(cap) || cap < 1 || cap > 1000) errors.capacity = '名额 1–1000 之间的整数'
  return Object.keys(errors).length === 0
}

async function submit() {
  if (!validate()) return
  saving.value = true
  try {
    await activityApi.create(props.clubId, {
      title: form.title.trim(),
      summary: form.summary.trim(),
      location: form.location.trim(),
      start_time: localToIso(form.start),
      end_time: localToIso(form.end),
      signup_deadline: localToIso(form.deadline),
      capacity: Number(form.capacity),
      tags: [...new Set(form.tags.split(/[\s,，、]+/).filter(Boolean))],
    })
    open.value = false
    toast.success('活动已提交，等待管理员审核')
    load()
  } catch {
    /* 校验提示已由 http.js 弹出 */
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <section class="mt-10">
    <div class="mb-3 flex items-end justify-between">
      <h2 class="font-display text-2xl text-ocean">社团活动</h2>
      <Button v-if="isPresident" size="sm" @click="openForm"><Plus />发布活动</Button>
    </div>
    <ActivityTable :items="items" empty-text="这个社团还没有发布活动" />

    <Dialog v-model:open="open">
      <DialogContent class="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>发布活动</DialogTitle>
          <DialogDescription>时间按北京时间填写。提交后需要管理员审核，通过后全校同学都能报名。</DialogDescription>
        </DialogHeader>
        <form class="grid gap-4 sm:grid-cols-2" novalidate @submit.prevent="submit">
          <div class="space-y-1.5 sm:col-span-2">
            <Label for="a-title">活动名称</Label>
            <Input id="a-title" v-model="form.title" maxlength="60" placeholder="例如：秋日校园扫街外拍" :aria-invalid="!!errors.title" />
            <p v-if="errors.title" class="text-sm text-destructive">{{ errors.title }}</p>
          </div>
          <div class="space-y-1.5">
            <Label for="a-start">开始时间</Label>
            <Input id="a-start" v-model="form.start" type="datetime-local" :aria-invalid="!!errors.start" />
            <p v-if="errors.start" class="text-sm text-destructive">{{ errors.start }}</p>
          </div>
          <div class="space-y-1.5">
            <Label for="a-end">结束时间</Label>
            <Input id="a-end" v-model="form.end" type="datetime-local" :aria-invalid="!!errors.end" />
            <p v-if="errors.end" class="text-sm text-destructive">{{ errors.end }}</p>
          </div>
          <div class="space-y-1.5">
            <Label for="a-loc">地点</Label>
            <Input id="a-loc" v-model="form.location" maxlength="128" placeholder="例如：南门集合" :aria-invalid="!!errors.location" />
            <p v-if="errors.location" class="text-sm text-destructive">{{ errors.location }}</p>
          </div>
          <div class="space-y-1.5">
            <Label for="a-cap">名额</Label>
            <Input id="a-cap" v-model="form.capacity" type="number" min="1" max="1000" placeholder="例如 30" :aria-invalid="!!errors.capacity" />
            <p v-if="errors.capacity" class="text-sm text-destructive">{{ errors.capacity }}</p>
          </div>
          <div class="space-y-1.5 sm:col-span-2">
            <Label for="a-dl">报名截止（选填，不填就是开始前都能报）</Label>
            <Input id="a-dl" v-model="form.deadline" type="datetime-local" :aria-invalid="!!errors.deadline" />
            <p v-if="errors.deadline" class="text-sm text-destructive">{{ errors.deadline }}</p>
          </div>
          <div class="space-y-1.5 sm:col-span-2">
            <Label for="a-sum">活动介绍（选填）</Label>
            <Textarea id="a-sum" v-model="form.summary" rows="3" maxlength="300" placeholder="内容安排、需要带什么、适合哪些同学……" />
          </div>
          <div class="space-y-1.5 sm:col-span-2">
            <Label for="a-tags">标签（选填）</Label>
            <Input id="a-tags" v-model="form.tags" placeholder="用空格分隔，如：摄影 外拍" />
          </div>
        </form>
        <DialogFooter>
          <Button variant="outline" @click="open = false">取消</Button>
          <Button :disabled="saving" @click="submit"><Loader2 v-if="saving" class="animate-spin" />提交审核</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </section>
</template>
