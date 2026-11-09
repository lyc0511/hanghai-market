<!-- 全站唯一的确认弹窗实例，由 composables/confirm.js 控制 -->
<script setup>
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { answerConfirm, confirmState } from '@/composables/confirm'

function onOpenChange(open) {
  if (!open) setTimeout(() => answerConfirm(false))
}
</script>

<template>
  <!--
    点按钮时组件库会先关闭弹窗（触发 update:open=false），再执行按钮自己的 @click。
    所以「关闭」延后一拍再当作取消：点了「确定」时 answerConfirm(true) 先生效，这里就什么也不做；
    按 Esc、点遮罩关闭时没有按钮回调，才会按「取消」处理。
  -->
  <AlertDialog :open="confirmState.open" @update:open="onOpenChange">
    <AlertDialogContent>
      <AlertDialogHeader>
        <AlertDialogTitle>{{ confirmState.title }}</AlertDialogTitle>
        <AlertDialogDescription v-if="confirmState.message">{{ confirmState.message }}</AlertDialogDescription>
      </AlertDialogHeader>
      <AlertDialogFooter>
        <AlertDialogCancel @click="answerConfirm(false)">取消</AlertDialogCancel>
        <AlertDialogAction
          :class="confirmState.danger ? 'bg-destructive text-white hover:bg-destructive/90' : ''"
          @click="answerConfirm(true)"
        >
          {{ confirmState.confirmText }}
        </AlertDialogAction>
      </AlertDialogFooter>
    </AlertDialogContent>
  </AlertDialog>
</template>
