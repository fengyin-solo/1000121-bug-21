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

    <form class="filter-bar" @submit.prevent="submitQuery">
      <label class="filter-item">
        <span>客户编码</span>
        <input v-model="filters.keyword" placeholder="按客户编码检索" />
      </label>
      <label class="filter-item">
        <span>客户名称</span>
        <input v-model="filters.name" placeholder="按客户名称检索" />
      </label>
      <button class="btn" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="toggleAdvanced">
        {{ showAdvanced ? '收起高级筛选' : '高级筛选' }}
      </button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>

      <template v-if="showAdvanced">
        <label class="filter-item">
          <span>客户类型</span>
          <select v-model="filters.customer_type">
            <option value="">全部类型</option>
            <option v-for="item in customerTypes" :key="item" :value="item">{{ item }}</option>
          </select>
        </label>
        <label class="filter-item">
          <span>合作状态</span>
          <select v-model="filters.status">
            <option value="">全部状态</option>
            <option v-for="item in statuses" :key="item" :value="item">{{ item }}</option>
          </select>
        </label>
      </template>
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
          <td v-for="column in columns" :key="column">
            <RouterLink
              v-if="column === '客户编码'"
              class="cell-link"
              :to="{ name: 'customer-detail', params: { id: row.id }, query: { returnTo: route.fullPath } }"
            >
              {{ row[column] ?? '—' }}
            </RouterLink>
            <template v-else>{{ displayValue(row, column) }}</template>
          </td>
          <td class="row-actions">
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
          <td :colspan="columns.length + 1" class="empty-state">没有符合条件的客户档案，请调整检索条件</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ total }} 条客户管理记录</span>
      <div v-if="total > 0" class="pager">
        <button class="btn" type="button" :disabled="page <= 1" @click="goPage(page - 1)">上一页</button>
        <span class="pager-info">第 {{ page }} / {{ pageCount }} 页</span>
        <button class="btn" type="button" :disabled="page >= pageCount" @click="goPage(page + 1)">下一页</button>
      </div>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { request } from '@/api/client'

type Row = Record<string, string | number | null>

const ENDPOINT = '/api/customer'
const PAGE_SIZE = 10
const columns = ["客户编码", "客户名称", "客户类型", "联系人", "联系电话", "结算方式", "合作状态"]
const actions = ["审核客户", "暂停合作", "终止合作"]
const customerTypes = ["连锁餐饮", "食品加工", "医药流通", "商超零售", "生鲜电商", "中央厨房"]
const statuses = ["待审核", "合作中", "已暂停", "已终止"]
const stats = [{"label": "合作客户", "value": 0}, {"label": "待审核客户", "value": 0}, {"label": "本月新增客户", "value": 0}]

const route = useRoute()
const router = useRouter()

const rows = ref<Row[]>([])
const total = ref(0)
const page = ref(1)
const errorMessage = ref('')
const showAdvanced = ref(false)
const filters = ref({ keyword: '', name: '', customer_type: '', status: '' })

const pageCount = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))

function displayValue(row: Row, column: string) {
  // 合作状态以后端流转字段 status 为统一口径，新登记档案没有冗余列时也能显示
  if (column === '合作状态' && (row[column] === null || row[column] === undefined || row[column] === '')) {
    return String(row.status ?? '—')
  }
  return row[column] ?? '—'
}

function readRoute() {
  const query = route.query
  filters.value = {
    keyword: typeof query.keyword === 'string' ? query.keyword : '',
    name: typeof query.name === 'string' ? query.name : '',
    customer_type: typeof query.customer_type === 'string' ? query.customer_type : '',
    status: typeof query.status === 'string' ? query.status : '',
  }
  page.value = Math.max(1, Number(query.page) || 1)
  showAdvanced.value = Boolean(filters.value.customer_type || filters.value.status)
}

function buildQuery() {
  const params = new URLSearchParams()
  const keyword = filters.value.keyword.trim()
  const name = filters.value.name.trim()
  if (keyword) params.set('keyword', keyword)
  if (name) params.set('name', name)
  if (filters.value.customer_type) params.set('customer_type', filters.value.customer_type)
  if (filters.value.status) params.set('status', filters.value.status)
  params.set('page', String(page.value))
  params.set('size', String(PAGE_SIZE))
  return params
}

function syncRoute() {
  const query: Record<string, string> = {}
  const params = buildQuery()
  params.forEach((value, key) => {
    if (key === 'page' && value === '1') return
    if (key === 'size') return
    query[key] = value
  })
  void router.replace({ name: 'customer', query })
}

function submitQuery() {
  page.value = 1
  syncRoute()
}

function goPage(target: number) {
  page.value = Math.min(Math.max(1, target), pageCount.value)
  syncRoute()
}

function resetFilters() {
  filters.value = { keyword: '', name: '', customer_type: '', status: '' }
  page.value = 1
  showAdvanced.value = false
  syncRoute()
}

function toggleAdvanced() {
  showAdvanced.value = !showAdvanced.value
  if (!showAdvanced.value) {
    filters.value.customer_type = ''
    filters.value.status = ''
    submitQuery()
  }
}

function exportRows() {
  const params = new URLSearchParams()
  const keyword = filters.value.keyword.trim()
  const name = filters.value.name.trim()
  if (keyword) params.set('keyword', keyword)
  if (name) params.set('name', name)
  if (filters.value.customer_type) params.set('customer_type', filters.value.customer_type)
  if (filters.value.status) params.set('status', filters.value.status)
  const query = params.toString()
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
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '客户管理操作失败'
  }
}

async function reload() {
  errorMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}?${buildQuery().toString()}`)
    if (!response.ok) {
      throw new Error('客户档案列表读取失败')
    }
    const payload = await response.json()
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
    // URL 里的页码超出范围（例如筛选后结果变少）时收敛到最后一页，避免空白页
    if (total.value > 0 && page.value > pageCount.value) {
      page.value = pageCount.value
      syncRoute()
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '客户管理列表读取失败'
  }
}

// 列表条件与页码全部挂在路由 query 上：进详情、按浏览器返回后都能原样恢复
watch(() => route.query, () => {
  readRoute()
  void reload()
})

onMounted(() => {
  readRoute()
  void reload()
})
</script>
