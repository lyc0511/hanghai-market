<!--
  手机端外壳：内容区 + 底部标签栏。
  在电脑上打开时，页面居中显示为手机宽度，两侧留白。
-->
<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const showTabbar = computed(() => route.meta.tab === true)
</script>

<template>
  <div class="shell">
    <main class="content" :class="{ 'with-tabbar': showTabbar }">
      <router-view />
    </main>
    <van-tabbar v-if="showTabbar" route fixed placeholder safe-area-inset-bottom>
      <van-tabbar-item to="/" icon="shop-o">首页</van-tabbar-item>
      <van-tabbar-item to="/me" icon="user-o">我的</van-tabbar-item>
    </van-tabbar>
  </div>
</template>

<style scoped>
.shell {
  max-width: 480px;
  min-height: 100vh;
  margin: 0 auto;
  background: var(--bg-page);
  position: relative;
}

/* 电脑上：手机宽度居中，加一点阴影和外部背景，像一台手机 */
@media (min-width: 520px) {
  .shell {
    box-shadow: 0 0 0 1px var(--border), 0 10px 40px rgba(23, 32, 43, 0.08);
  }
  :global(body) {
    background: #e9edf2;
  }
}

/*
 * 固定在底部 / 顶部的栏在电脑上也要和内容区同宽居中。
 * 注意样式要加在 fixed 元素本身：如果加在它的父元素上，transform 会让 fixed 失效。
 */
.shell :deep(.van-tabbar--fixed),
.shell :deep(.van-nav-bar--fixed) {
  max-width: 480px;
  left: 50%;
  transform: translateX(-50%);
}
</style>
