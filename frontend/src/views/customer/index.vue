<template>
  <section class="page" data-module="customer">
    <header class="page-head">
      <div>
        <h2>客户管理管理</h2>
        <p class="page-desc">维护客户档案，围绕客户编码、客户名称、客户类型、联系人做登记、筛选与状态流转。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" @click="openCreate">登记客户档案</button>
        <button class="btn" type="button" @click="exportRows">导出客户管理清单</button>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="item in stats" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <form class="filter-bar" @submit.prevent="applyFilters">
      <label v-for="field in filterFields" :key="field.key" class="filter-item">
        <span>{{ field.label }}</span>
        <input v-model="filters[field.key]" :placeholder="`按${field.label}检索`" />
      </label>
      <button class="btn" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
    </form>

    <table class="data-table">
      <thead>
        <tr>
          <th v-for="column in columns" :key="column">{{ column }}</th>
          <th>可执行动作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="String(row.id)">
          <td v-for="column in columns" :key="column">{{ row[column] ?? '—' }}</td>
          <td class="row-actions">
            <RouterLink class="link" :to="detailHref(row)">查看详情</RouterLink>
            <button
              v-for="action in actions"
              :key="action"
              class="link"
              type="button"
              @click="runAction(action, row)"
            >
              {{ action }}
            </button>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="columns.length + 1" class="empty-state">暂无客户管理数据，可先登记客户档案</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ total }} 条客户管理记录</span>
      <div class="pagination">
        <button class="btn" type="button" :disabled="page <= 1 || loading" @click="goPage(page - 1)">上一页</button>
        <span>第 {{ page }} / {{ totalPages }} 页</span>
        <label>
          每页
          <select :value="size" @change="changeSize">
            <option v-for="option in pageSizeOptions" :key="option" :value="option">{{ option }} 条</option>
          </select>
        </label>
        <button class="btn" type="button" :disabled="page >= totalPages || loading" @click="goPage(page + 1)">下一页</button>
      </div>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { request } from '@/api/client'

type Row = Record<string, string | number | null>
type PageResult = {
  items?: Row[]
  total?: number
  page?: number
  size?: number
}

const ENDPOINT = '/api/customer'
const columns = ['客户编码', '客户名称', '客户类型', '联系人', '联系电话', '结算方式', '合作状态']
const actions = ['审核客户', '暂停合作', '终止合作']
const statuses = ['待审核', '合作中', '已暂停', '已终止']
const stats = [{ label: '合作客户', value: 0 }, { label: '待审核客户', value: 0 }, { label: '本月新增客户', value: 0 }]
const filterFields = [
  { label: '客户编码', key: 'customer_code' },
  { label: '客户名称', key: 'customer_name' },
  { label: '客户类型', key: 'customer_type' },
] as const
const pageSizeOptions = [10, 20, 50, 100]

const route = useRoute()
const router = useRouter()

const rows = ref<Row[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(20)
const loading = ref(false)
let loadSequence = 0
const errorMessage = ref('')
const filters = ref<Record<string, string>>({
  customer_code: '',
  customer_name: '',
  customer_type: '',
})

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / size.value)))

function queryText(key: string) {
  const value = route.query[key]
  return Array.isArray(value) ? value[0] ?? '' : value ?? ''
}

function syncFromRoute() {
  filters.value = {
    customer_code: queryText('customer_code'),
    customer_name: queryText('customer_name'),
    customer_type: queryText('customer_type'),
  }
  page.value = Math.max(Number.parseInt(queryText('page')) || 1, 1)
  size.value = Math.min(Math.max(Number.parseInt(queryText('size')) || 20, 1), 200)
}

function activeFilters() {
  const query: Record<string, string> = {}
  for (const field of filterFields) {
    const value = filters.value[field.key].trim()
    if (value) {
      query[field.key] = value
    }
  }
  return query
}

function listQuery(forCurrentPage: boolean) {
  const query = activeFilters()
  if (forCurrentPage) {
    query.page = String(page.value)
    query.size = String(size.value)
  }
  return new URLSearchParams(query)
}

async function loadRows() {
  const sequence = ++loadSequence
  loading.value = true
  errorMessage.value = ''
  const query = listQuery(true).toString()
  try {
    const response = await request(`${ENDPOINT}?${query}`)
    if (!response.ok) {
      throw new Error('客户档案列表读取失败')
    }
    const payload = (await response.json()) as PageResult
    if (sequence !== loadSequence) {
      return
    }
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
    page.value = payload.page ?? page.value
    size.value = payload.size ?? size.value

    const lastPage = Math.max(1, Math.ceil(total.value / size.value))
    if (total.value > 0 && page.value > lastPage) {
      await router.replace({ name: 'customer', query: { ...activeFilters(), page: String(lastPage), size: String(size.value) } })
      return
    }
  } catch (error) {
    if (sequence !== loadSequence) {
      return
    }
    errorMessage.value = error instanceof Error ? error.message : '客户管理列表读取失败'
  } finally {
    if (sequence === loadSequence) {
      loading.value = false
    }
  }
}

function applyFilters() {
  void router.push({
    name: 'customer',
    query: { ...activeFilters(), page: '1', size: String(size.value) },
  })
}

function resetFilters() {
  void router.push({ name: 'customer', query: { page: '1', size: String(size.value) } })
}

function goPage(targetPage: number) {
  if (targetPage < 1 || targetPage > totalPages.value) {
    return
  }
  void router.push({
    name: 'customer',
    query: { ...activeFilters(), page: String(targetPage), size: String(size.value) },
  })
}

function changeSize(event: Event) {
  const targetSize = Number((event.target as HTMLSelectElement).value)
  size.value = targetSize
  void router.push({
    name: 'customer',
    query: { ...activeFilters(), page: '1', size: String(targetSize) },
  })
}

function detailHref(row: Row) {
  return {
    name: 'customer-detail',
    params: { id: String(row.id) },
    query: { returnTo: route.fullPath },
  }
}

function exportRows() {
  const query = listQuery(false).toString()
  window.open(query ? `${ENDPOINT}/export?${query}` : `${ENDPOINT}/export`, '_blank')
}

function openCreate() {
  errorMessage.value = '客户档案登记入口尚未接入审批流'
}

async function runAction(action: string, row: Row) {
  errorMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${row.id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ action }),
    })
    if (!response.ok) {
      throw new Error('客户管理动作未生效，请稍后重试')
    }
    await loadRows()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '客户管理操作失败'
  }
}

watch(() => route.fullPath, () => {
  syncFromRoute()
  void loadRows()
}, { immediate: true })
</script>
