<template>
  <section class="page" data-module="customer-detail">
    <header class="page-head">
      <div>
        <h2>客户档案详情</h2>
        <p class="page-desc">查看客户档案的完整资料，返回时保留列表页的检索条件、页码与每页条数。</p>
      </div>
      <div class="page-actions">
        <button class="btn" type="button" @click="goBack">返回列表</button>
      </div>
    </header>

    <p v-if="loading" class="page-desc">客户档案读取中……</p>
    <p v-else-if="errorMessage" class="error-text">{{ errorMessage }}</p>

    <table v-else-if="entry" class="data-table detail-table">
      <tbody>
        <tr v-for="field in detailFields" :key="field">
          <th>{{ field }}</th>
          <td>{{ entry[field] ?? '—' }}</td>
        </tr>
        <tr>
          <th>内部状态</th>
          <td>{{ entry.status ?? '—' }}</td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { request } from '@/api/client'

type Row = Record<string, string | number | boolean | null>

const route = useRoute()
const router = useRouter()

const detailFields = ['客户编码', '客户名称', '客户类型', '联系人', '联系电话', '结算方式', '合作状态']
const entry = ref<Row | null>(null)
const loading = ref(false)
const errorMessage = ref('')

const backHref = computed(() => {
  const returnTo = route.query.returnTo
  if (typeof returnTo === 'string' && returnTo.startsWith('/customer') && !returnTo.startsWith('//')) {
    return returnTo
  }
  return '/customer'
})

function goBack() {
  void router.push(backHref.value)
}

async function loadEntry() {
  loading.value = true
  errorMessage.value = ''
  entry.value = null
  try {
    const response = await request(`/api/customer/${route.params.id}`)
    if (!response.ok) {
      throw new Error('客户档案详情读取失败')
    }
    entry.value = await response.json()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '客户档案详情读取失败'
  } finally {
    loading.value = false
  }
}

watch(() => route.params.id, () => void loadEntry(), { immediate: true })
</script>
