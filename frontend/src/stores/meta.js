/**
 * 字典数据：枚举中文名、校区、物品类目、校园墙标签。只请求一次，全站共用。
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'

import { metaApi } from '@/api'

export const useMetaStore = defineStore('meta', () => {
  const enums = ref(null)
  const itemCategories = ref([])
  const postTags = ref([])
  let loading = null

  function load() {
    if (!loading) {
      loading = Promise.all([metaApi.enums(), metaApi.categories('item'), metaApi.categories('post')])
        .then(([e, cats, tags]) => {
          enums.value = e
          itemCategories.value = cats
          postTags.value = tags
        })
        .catch((err) => {
          loading = null // 失败时允许下次重试
          throw err
        })
    }
    return loading
  }

  /** 枚举值转中文，如 label('item_condition', 'like_new') → 几乎全新 */
  function label(group, value) {
    return enums.value?.[group]?.[value] ?? value
  }

  return { enums, itemCategories, postTags, load, label }
})
