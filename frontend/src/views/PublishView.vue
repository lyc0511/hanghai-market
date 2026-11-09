<script setup>
import { showToast } from 'vant'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { itemApi, uploadApi } from '@/api'
import { useMetaStore } from '@/stores/meta'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const meta = useMetaStore()
const user = useUserStore()

const files = ref([]) // van-uploader 的文件列表，每项上传成功后带上 path
const form = reactive({
  title: '',
  summary: '',
  categoryId: null,
  price: '',
  originalPrice: '',
  condition: 'good',
  campus: user.profile?.campus_area ?? '',
  tags: '',
})
const showCategory = ref(false)
const showCampus = ref(false)
const submitting = ref(false)

const categoryName = computed(() => meta.itemCategories.find((c) => c.id === form.categoryId)?.name ?? '')
const categoryColumns = computed(() => meta.itemCategories.map((c) => ({ text: c.name, value: c.id })))
const campusColumns = computed(() => (meta.enums?.campus_area ?? []).map((c) => ({ text: c, value: c })))
const conditions = computed(() => Object.entries(meta.enums?.item_condition ?? {}))
const uploading = computed(() => files.value.some((f) => f.status === 'uploading'))

onMounted(() => meta.load().catch(() => {}))

// 第一步：选好图片后立即上传，拿到 path
async function afterRead(entry) {
  const list = Array.isArray(entry) ? entry : [entry]
  await Promise.all(
    list.map(async (f) => {
      f.status = 'uploading'
      f.message = '上传中'
      try {
        const { path } = await uploadApi.image(f.file)
        f.path = path
        f.status = 'done'
      } catch {
        f.status = 'failed'
        f.message = '上传失败'
      }
    }),
  )
}

function onOversize() {
  showToast('图片不能超过 5MB')
}

const tagList = computed(() =>
  [...new Set(form.tags.split(/[\s,，、]+/).map((t) => t.trim()).filter(Boolean))],
)

const rules = {
  title: [{ validator: (v) => v.trim().length >= 2 && v.trim().length <= 60, message: '标题 2–60 个字' }],
  category: [{ validator: () => !!form.categoryId, message: '请选择分类' }],
  price: [{ validator: (v) => v !== '' && Number(v) >= 0 && Number(v) <= 99999, message: '价格 0–99999，0 表示免费送' }],
  originalPrice: [
    {
      // 原价为空时 Vant 会跳过非必填规则；填了才检查
      validator: (v) => v === '' || v == null || Number(v) >= Number(form.price || 0),
      message: '原价不能低于售价',
    },
  ],
  tags: [{ validator: () => tagList.value.length <= 5 && tagList.value.every((t) => t.length <= 10), message: '最多 5 个标签，每个不超过 10 字' }],
}

// 第二步：把表单和图片 path 一起提交
async function onSubmit() {
  const images = files.value.filter((f) => f.status === 'done').map((f) => f.path)
  if (!images.length) {
    showToast('请至少上传一张图片')
    return
  }
  if (uploading.value) {
    showToast('图片还在上传，请稍等')
    return
  }
  submitting.value = true
  try {
    await itemApi.create({
      title: form.title.trim(),
      summary: form.summary.trim(),
      category_id: form.categoryId,
      price: Number(form.price),
      original_price: form.originalPrice === '' ? null : Number(form.originalPrice),
      condition: form.condition,
      images,
      tags: tagList.value,
      campus_area: form.campus || null,
    })
    showToast({ type: 'success', message: '已提交，等待管理员审核' })
    router.replace({ name: 'my-items' })
  } catch {
    /* 提示已由 http.js 弹出 */
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="publish">
    <van-nav-bar title="发布闲置" left-arrow fixed placeholder @click-left="router.back()" />

    <van-form @submit="onSubmit">
      <section class="block">
        <van-field v-model="form.title" :rules="rules.title" placeholder="品牌型号、新旧程度，一句话说清楚" maxlength="60" class="title-field" />
        <van-field
          v-model="form.summary"
          type="textarea"
          rows="3"
          autosize
          maxlength="300"
          show-word-limit
          placeholder="描述一下使用情况、入手渠道、转手原因、交易方式……"
        />
        <div class="uploader">
          <van-uploader
            v-model="files"
            multiple
            :max-count="9"
            :max-size="5 * 1024 * 1024"
            accept="image/jpeg,image/png,image/webp"
            :after-read="afterRead"
            @oversize="onOversize"
          />
          <p class="hint">最多 9 张，第一张作为封面；支持 jpg、png、webp，每张不超过 5MB</p>
        </div>
      </section>

      <section class="block">
        <!-- 用了自定义输入框，要把值同时传给 van-field，校验规则才能拿到 -->
        <van-field label="售价" :model-value="form.price" :rules="rules.price" required>
          <template #input>
            <span class="yuan">¥</span>
            <input v-model="form.price" type="number" inputmode="decimal" min="0" placeholder="0 表示免费送" class="num" />
          </template>
        </van-field>
        <van-field label="原价" :model-value="form.originalPrice" :rules="rules.originalPrice">
          <template #input>
            <span class="yuan">¥</span>
            <input v-model="form.originalPrice" type="number" inputmode="decimal" min="0" placeholder="选填" class="num" />
          </template>
        </van-field>
        <van-field label="成色" required>
          <template #input>
            <div class="chips">
              <button
                v-for="[value, text] in conditions"
                :key="value"
                type="button"
                class="chip"
                :class="{ active: form.condition === value }"
                @click="form.condition = value"
              >
                {{ text }}
              </button>
            </div>
          </template>
        </van-field>
        <van-field
          :model-value="categoryName"
          label="分类"
          placeholder="请选择"
          is-link
          readonly
          required
          :rules="rules.category"
          @click="showCategory = true"
        />
        <van-field
          :model-value="form.campus"
          label="交易校区"
          placeholder="请选择"
          is-link
          readonly
          @click="showCampus = true"
        />
        <van-field v-model="form.tags" label="标签" placeholder="用空格分隔，如：考研 数学" :rules="rules.tags" />
      </section>

      <div class="submit">
        <van-button round block type="primary" native-type="submit" :loading="submitting" :disabled="uploading">
          发布
        </van-button>
        <p class="hint center">发布后需管理员审核，通过后其他同学才能看到</p>
      </div>
    </van-form>

    <van-popup v-model:show="showCategory" round position="bottom">
      <van-picker
        title="选择分类"
        :columns="categoryColumns"
        @confirm="({ selectedValues }) => ((form.categoryId = selectedValues[0]), (showCategory = false))"
        @cancel="showCategory = false"
      />
    </van-popup>
    <van-popup v-model:show="showCampus" round position="bottom">
      <van-picker
        title="交易校区"
        :columns="campusColumns"
        @confirm="({ selectedValues }) => ((form.campus = selectedValues[0]), (showCampus = false))"
        @cancel="showCampus = false"
      />
    </van-popup>
  </div>
</template>

<style scoped>
.publish {
  padding-bottom: 32px;
}
.block {
  background: var(--bg-card);
  margin: 10px var(--page-x) 0;
  border-radius: var(--radius);
  overflow: hidden;
}
.title-field {
  --van-field-input-text-color: var(--text-1);
  font-size: 16px;
  font-weight: 500;
}
.uploader {
  padding: 4px 16px 12px;
}
.hint {
  margin: 4px 0 0;
  color: var(--text-3);
  font-size: 12px;
}
.center {
  text-align: center;
  margin-top: 10px;
}
.yuan {
  color: var(--accent);
  font-weight: 600;
  margin-right: 4px;
}
.num {
  flex: 1;
  min-width: 0;
  border: 0;
  outline: 0;
  background: transparent;
  font: inherit;
  color: var(--text-1);
}
.num::placeholder {
  color: var(--text-3);
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.chip {
  border: 1px solid var(--border);
  background: var(--bg-card);
  color: var(--text-2);
  border-radius: 999px;
  padding: 3px 10px;
  font-size: 12px;
  font-family: inherit;
  cursor: pointer;
}
.chip.active {
  border-color: var(--brand);
  background: var(--brand-soft);
  color: var(--brand-dark);
  font-weight: 500;
}
.submit {
  padding: 20px var(--page-x) 0;
}
</style>
