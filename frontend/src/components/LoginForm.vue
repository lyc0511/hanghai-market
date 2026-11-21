<!--
  登录 / 注册表单：右上角弹窗和独立登录页共用同一个组件。
  成功后触发 success 事件，由使用方决定接下来去哪。
-->
<script setup>
import { Loader2 } from '@lucide/vue'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useMetaStore } from '@/stores/meta'
import { useUserStore } from '@/stores/user'

const props = defineProps({ initialMode: { type: String, default: 'login' } })
const emit = defineEmits(['success'])

const user = useUserStore()
const router = useRouter()
const meta = useMetaStore()

const mode = ref(props.initialMode) // login | register
const submitting = ref(false)
const form = reactive({ studentNo: '', password: '', nickname: '', campus: '' })
const errors = reactive({})

const isRegister = computed(() => mode.value === 'register')

onMounted(() => meta.load().catch(() => {}))

// 前端先做一遍和后端相同的格式检查，提示更及时；最终以后端校验为准
function validate() {
  for (const k of Object.keys(errors)) delete errors[k]
  if (!/^\d{6,20}$/.test(form.studentNo)) errors.studentNo = '学号应为 6–20 位数字'
  if (isRegister.value) {
    if (!form.nickname.trim()) errors.nickname = '请输入昵称'
    if (!/^[\x21-\x7E]{8,32}$/.test(form.password)) errors.password = '密码 8–32 位，不能含空格或中文'
    else if (!/[a-zA-Z]/.test(form.password) || !/\d/.test(form.password)) errors.password = '密码需同时包含字母和数字'
  } else if (!form.password) {
    errors.password = '请输入密码'
  }
  return Object.keys(errors).length === 0
}

function switchMode(m) {
  mode.value = m
  for (const k of Object.keys(errors)) delete errors[k]
}

async function onSubmit() {
  if (!validate()) return
  submitting.value = true
  try {
    if (isRegister.value) {
      await user.register({
        student_no: form.studentNo,
        password: form.password,
        nickname: form.nickname.trim(),
        campus_area: form.campus || null,
      })
    } else {
      await user.login(form.studentNo, form.password)
    }
    emit('success')
    if (user.profile?.must_change_password) await router.replace({ name: 'change-password' })
  } catch {
    /* 错误提示已由 http.js 弹出 */
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div>
    <div class="mb-6 flex gap-6" role="tablist">
      <button
        v-for="[m, label] in [['login', '登录'], ['register', '注册']]"
        :key="m"
        type="button"
        role="tab"
        :aria-selected="mode === m"
        class="border-b-2 pb-1.5 font-display text-2xl transition-colors"
        :class="mode === m ? 'border-buoy text-ocean' : 'border-transparent text-muted-foreground hover:text-ocean'"
        @click="switchMode(m)"
      >
        {{ label }}
      </button>
    </div>

    <p v-if="!isRegister" class="mb-4 text-sm text-muted-foreground">忘记密码？请联系管理员核实学生身份，领取临时密码后登录并设置新密码。</p>
    <form class="space-y-4" novalidate @submit.prevent="onSubmit">
      <div class="space-y-1.5">
        <Label for="studentNo">学号</Label>
        <Input id="studentNo" v-model.trim="form.studentNo" inputmode="numeric" maxlength="20" placeholder="请输入学号" :aria-invalid="!!errors.studentNo" class="h-10" />
        <p v-if="errors.studentNo" class="text-sm text-destructive">{{ errors.studentNo }}</p>
      </div>

      <div v-if="isRegister" class="space-y-1.5">
        <Label for="nickname">昵称</Label>
        <Input id="nickname" v-model="form.nickname" maxlength="30" placeholder="其他同学看到的名字" :aria-invalid="!!errors.nickname" class="h-10" />
        <p v-if="errors.nickname" class="text-sm text-destructive">{{ errors.nickname }}</p>
      </div>

      <div class="space-y-1.5">
        <Label for="password">密码</Label>
        <Input
          id="password"
          v-model="form.password"
          type="password"
          maxlength="32"
          :placeholder="isRegister ? '8–32 位，同时包含字母和数字' : '请输入密码'"
          :aria-invalid="!!errors.password"
          class="h-10"
        />
        <p v-if="errors.password" class="text-sm text-destructive">{{ errors.password }}</p>
      </div>

      <div v-if="isRegister" class="space-y-1.5">
        <Label>所在校区（可不填）</Label>
        <Select v-model="form.campus">
          <SelectTrigger class="h-10 w-full"><SelectValue placeholder="选择校区" /></SelectTrigger>
          <SelectContent>
            <SelectItem v-for="c in meta.enums?.campus_area ?? []" :key="c" :value="c">{{ c }}</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <Button type="submit" class="h-10 w-full text-base" :disabled="submitting">
        <Loader2 v-if="submitting" class="animate-spin" />
        {{ isRegister ? '注册并登录' : '登录' }}
      </Button>
    </form>
  </div>
</template>
