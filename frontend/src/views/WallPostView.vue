<!--
  帖子详情：完整正文、图片、评论区。
  投稿人本人还能看到审核状态，可以修改（未上墙时）、撤回、标记「已解决」；其他人可以举报。
-->
<script setup>
import { CircleCheck, Loader2 } from '@lucide/vue'
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'

import { postApi } from '@/api'
import PageHeader from '@/components/PageHeader.vue'
import PostCard from '@/components/PostCard.vue'
import PostComments from '@/components/PostComments.vue'
import ReportButton from '@/components/ReportButton.vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { confirm } from '@/composables/confirm'
import { POST_STATUS } from '@/lib/wall'

const route = useRoute()
const router = useRouter()

const post = ref(null)
const loading = ref(true)
const busy = ref(false)

async function load() {
  loading.value = true
  try {
    post.value = await postApi.detail(route.params.id)
  } catch {
    // 不存在、已撤回或无权查看：回到墙
    router.replace({ name: 'wall' })
  } finally {
    loading.value = false
  }
}

async function withdraw() {
  const ok = await confirm({
    title: '撤回这条帖子',
    message: '撤回后大家都看不到它了，也不能恢复。',
    confirmText: '撤回',
    danger: true,
  })
  if (!ok) return
  busy.value = true
  try {
    await postApi.withdraw(post.value.id)
    toast.success('已撤回')
    router.replace({ name: 'my-posts' })
  } catch {
    /* 提示已由 http.js 弹出 */
  } finally {
    busy.value = false
  }
}

async function toggleResolved() {
  busy.value = true
  try {
    post.value = post.value.resolved ? await postApi.unresolve(post.value.id) : await postApi.resolve(post.value.id)
    toast.success(post.value.resolved ? '已标记为已解决' : '已取消标记')
  } catch {
    /* 提示已由 http.js 弹出 */
  } finally {
    busy.value = false
  }
}

onMounted(load)
// 从通知点进另一条帖子时，页面组件不会重建，靠 id 变化重新加载
watch(() => route.params.id, (id) => id && load())
</script>

<template>
  <div class="container narrow">
    <PageHeader title="帖子" />

    <div v-if="loading" class="rounded-2xl border bg-white p-5">
      <div class="flex items-center gap-3"><Skeleton class="size-10 rounded-full" /><Skeleton class="h-4 w-24" /></div>
      <Skeleton class="mt-4 h-4 w-full" /><Skeleton class="mt-2 h-4 w-2/3" />
    </div>

    <template v-else-if="post">
      <!-- 只有投稿人本人能看到这一块 -->
      <div v-if="post.is_mine" class="mb-3 rounded-xl border bg-white px-4 py-3">
        <div class="flex flex-wrap items-center gap-2">
          <span class="text-sm text-muted-foreground">这是你的投稿</span>
          <Badge :class="POST_STATUS[post.status]?.[1]">{{ POST_STATUS[post.status]?.[0] ?? post.status }}</Badge>
          <div class="ml-auto flex flex-wrap gap-2">
            <Button v-if="post.status === 'online'" size="sm" variant="outline" :disabled="busy" @click="toggleResolved">
              <CircleCheck />{{ post.resolved ? '取消已解决' : '标记已解决' }}
            </Button>
            <Button
              v-if="['pending', 'rejected'].includes(post.status)"
              size="sm"
              variant="outline"
              @click="router.push({ name: 'wall-edit', params: { id: post.id } })"
            >
              修改
            </Button>
            <Button size="sm" variant="outline" :disabled="busy" @click="withdraw"><Loader2 v-if="busy" class="animate-spin" />撤回</Button>
          </div>
        </div>
        <p v-if="['rejected', 'offline'].includes(post.status) && post.reject_reason" class="mt-2 rounded-md bg-destructive/10 px-2.5 py-1.5 text-sm text-destructive">
          {{ post.status === 'offline' ? '下架原因' : '未通过原因' }}：{{ post.reject_reason }}
        </p>
        <p v-else-if="post.status === 'pending'" class="mt-2 text-sm text-muted-foreground">正在等待管理员审核，通过后会通知你。</p>
      </div>

      <PostCard :post="post">
        <template #actions>
          <ReportButton v-if="!post.is_mine && post.status === 'online'" target-type="post" :target-id="post.id" class="-mr-2" />
        </template>
      </PostCard>

      <PostComments
        :post-id="post.id"
        :is-mine="post.is_mine"
        :can-comment="post.status === 'online'"
        @count="(n) => (post.comment_count = n)"
      />
    </template>
  </div>
</template>
