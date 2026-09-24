<template>
  <section class="page" data-module="customer-detail">
    <header class="page-head">
      <div>
        <h2>客户档案详情</h2>
        <p class="page-desc">查看客户档案的完整信息，返回时保留列表页的检索条件、高级筛选与页码。</p>
      </div>
      <div class="page-actions">
        <button class="btn" type="button" @click="goBack">返回列表</button>
      </div>
    </header>

    <article v-if="entry" class="detail-card">
      <dl class="detail-grid">
        <template v-for="field in detailFields" :key="field">
          <dt>{{ field }}</dt>
          <dd>{{ field === '合作状态' ? displayStatus : (entry[field] ?? '—') }}</dd>
        </template>
        <template v-if="entry.id !== undefined">
          <dt>档案ID</dt>
          <dd>{{ entry.id }}</dd>
        </template>
      </dl>
    </article>

    <div v-else-if="!errorMessage" class="detail-card empty-state">客户档案加载中…</div>
    <footer class="page-foot">
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { request } from '@/api/client'

type Entry = Record<string, string | number | null>

const detailFields = ["客户编码", "客户名称", "客户类型", "联系人", "联系电话", "结算方式", "合作状态"]

const route = useRoute()
const router = useRouter()

const entry = ref<Entry | null>(null)
const errorMessage = ref('')

const displayStatus = computed(() => {
  const value = entry.value
  if (!value) return '—'
  return value['合作状态'] ?? value.status ?? '—'
})

function goBack() {
  // returnTo 是列表页带来的完整地址（含检索条件与页码），缺失时退回不带条件的列表
  const returnTo = typeof route.query.returnTo === 'string' ? route.query.returnTo : '/customer'
  void router.push(returnTo)
}

async function load() {
  errorMessage.value = ''
  try {
    const response = await request(`/api/customer/${route.params.id}`)
    if (!response.ok) {
      throw new Error('客户档案详情读取失败')
    }
    entry.value = await response.json()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '客户档案详情读取失败'
  }
}

onMounted(load)
</script>
