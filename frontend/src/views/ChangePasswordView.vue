<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import { authApi } from '@/api'
import { useUserStore } from '@/stores/user'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

const user = useUserStore()
const router = useRouter()
const saving = ref(false)

async function save(event) {
  if (saving.value) return
  const form = event.currentTarget
  const fields = new FormData(form)
  if (fields.get('new_password') !== fields.get('confirm_password')) return toast.error('两次新密码不一致')
  saving.value = true
  try {
    await authApi.changePassword({ old_password: fields.get('old_password'), new_password: fields.get('new_password') })
    form.reset()
    user.logout()
    toast.success('新密码已设置，请重新登录')
    await router.replace({ name: 'login' })
  } catch {
    /* 统一拦截器显示错误 */
  } finally {
    saving.value = false
  }
}

function logout() {
  user.logout()
  router.replace({ name: 'login' })
}
</script>

<template>
  <main class="mx-auto max-w-md px-6 py-16">
    <h1 class="font-display text-3xl text-ocean">设置新密码</h1>
    <p class="my-4 text-muted-foreground">请将管理员提供的临时密码换成你自己的密码，完成后才能使用账号。</p>
    <form class="space-y-4" @submit.prevent="save">
      <Label for="reset-old">临时密码</Label>
      <Input id="reset-old" name="old_password" type="password" autocomplete="current-password" required />
      <Label for="reset-new">新密码（8–32 位，含字母和数字）</Label>
      <Input id="reset-new" name="new_password" type="password" autocomplete="new-password" minlength="8" maxlength="32" required />
      <Label for="reset-confirm">确认新密码</Label>
      <Input id="reset-confirm" name="confirm_password" type="password" autocomplete="new-password" maxlength="32" required />
      <Button type="submit" :disabled="saving" class="w-full">保存新密码</Button>
    </form>
    <Button variant="ghost" class="mt-4" :disabled="saving" @click="logout">退出登录</Button>
  </main>
</template>
