<!--
  举报按钮 + 弹窗：物品 / 社团 / 活动详情页共用。
  未登录点击 → 先弹登录框；提交成功后按钮变成「已举报」。
-->
<script setup>
import { Flag } from '@lucide/vue'
import { computed, ref } from 'vue'
import { toast } from 'vue-sonner'

import { reportApi } from '@/api'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogTitle } from '@/components/ui/dialog'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'
import { useUserStore } from '@/stores/user'

const props = defineProps({
  targetType: { type: String, required: true }, // item | club | activity
  targetId: { type: Number, required: true },
  class: { type: String, default: '' },
})

const REASONS = [
  { value: 'fraud', label: '疑似诈骗' },
  { value: 'prohibited', label: '违禁物品' },
  { value: 'false_info', label: '虚假信息' },
  { value: 'spam', label: '广告刷屏' },
  { value: 'abuse', label: '辱骂骚扰' },
  { value: 'other', label: '其他' },
]
const NAMES = { item: '物品', club: '社团', activity: '活动' }

const user = useUserStore()
const open = ref(false)
const reason = ref('')
const desc = ref('')
const submitting = ref(false)
const done = ref(false)

const needDesc = computed(() => reason.value === 'other')
const canSubmit = computed(() => reason.value && (!needDesc.value || desc.value.trim()) && !submitting.value)

function start() {
  if (!user.isLoggedIn) return user.openLogin()
  reason.value = ''
  desc.value = ''
  open.value = true
}

async function submit() {
  submitting.value = true
  try {
    await reportApi.create({
      target_type: props.targetType,
      target_id: props.targetId,
      reason: reason.value,
      description: desc.value.trim() || null,
    })
    toast.success('举报已提交，管理员会尽快核实')
    open.value = false
    done.value = true
  } catch (e) {
    // 已经举报过（40951）也视为完成，按钮置灰
    if (e?.code === 40951) {
      open.value = false
      done.value = true
    }
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <Button
    variant="ghost"
    size="sm"
    :class="cn('text-muted-foreground hover:text-destructive', props.class)"
    :disabled="done"
    @click="start"
  >
    <Flag />{{ done ? '已举报' : '举报' }}
  </Button>

  <Dialog v-model:open="open">
    <DialogContent class="sm:max-w-md">
      <DialogTitle>举报这个{{ NAMES[targetType] }}</DialogTitle>
      <DialogDescription>管理员会核实处理，结果会通过站内通知告诉你。举报人信息不会透露给对方。</DialogDescription>

      <fieldset class="mt-2">
        <legend class="mb-2 text-sm font-medium">举报原因</legend>
        <div class="grid grid-cols-3 gap-2">
          <label
            v-for="r in REASONS"
            :key="r.value"
            class="cursor-pointer rounded-lg border px-3 py-2 text-center text-sm transition-colors has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-ring"
            :class="reason === r.value ? 'border-destructive bg-destructive/5 font-medium text-destructive' : 'hover:bg-muted'"
          >
            <input v-model="reason" type="radio" name="report-reason" :value="r.value" class="sr-only" />
            {{ r.label }}
          </label>
        </div>
      </fieldset>

      <div class="mt-3">
        <label for="report-desc" class="mb-2 block text-sm font-medium">
          补充说明<span class="font-normal text-muted-foreground">{{ needDesc ? '（必填）' : '（选填）' }}</span>
        </label>
        <Textarea id="report-desc" v-model="desc" rows="3" maxlength="300" placeholder="比如：价格明显低于市场价，要求先转账……" />
        <div class="mt-1 text-right text-xs text-muted-foreground">{{ desc.length }}/300</div>
      </div>

      <DialogFooter>
        <Button variant="outline" @click="open = false">取消</Button>
        <Button variant="destructive" :disabled="!canSubmit" @click="submit">{{ submitting ? '提交中…' : '提交举报' }}</Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
