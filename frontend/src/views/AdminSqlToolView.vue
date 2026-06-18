<template>
  <AppLayout>
    <section class="card hero-panel">
      <div class="toolbar">
        <div>
          <h1>Admin SQL Tool</h1>
          <p class="hero-subtitle">
            Run read-only SQL against the MCH database for troubleshooting and analysis.
            Write statements are blocked at API level and should also be blocked by the read-only DB user.
          </p>
        </div>
        <span class="badge blue">Admin only</span>
      </div>
    </section>

    <section class="grid admin-sql-grid section-gap">
      <aside class="card flat schema-card">
        <div class="card-title">
          <h2>Database Tables</h2>
          <button class="btn btn-sm btn-secondary" type="button" @click="loadTables">Refresh</button>
        </div>

        <p v-if="tablesLoading" class="muted">Loading tables...</p>
        <p v-else-if="!tables.length" class="muted">No tables found.</p>

        <div v-else class="schema-list">
          <button
            v-for="table in tables"
            :key="`${table.table_schema}.${table.table_name}`"
            class="schema-item"
            type="button"
            @click="selectTable(table)"
          >
            <strong>{{ table.table_schema }}.{{ table.table_name }}</strong>
            <span>{{ table.table_type }}</span>
          </button>
        </div>

        <div v-if="selectedTable" class="column-panel">
          <div class="toolbar column-toolbar">
            <h3>{{ selectedTable.table_schema }}.{{ selectedTable.table_name }}</h3>
            <button class="btn btn-sm btn-outline" type="button" @click="insertSelectQuery">Insert SELECT</button>
          </div>

          <p v-if="columnsLoading" class="muted">Loading columns...</p>
          <ul v-else class="column-list">
            <li v-for="column in columns" :key="column.column_name">
              <strong>{{ column.column_name }}</strong>
              <small>{{ column.data_type }}</small>
            </li>
          </ul>
        </div>
      </aside>

      <main class="grid query-grid">
        <section class="card flat">
          <div class="toolbar">
            <label class="limit-field">
              <span class="label">Row limit</span>
              <input v-model.number="limit" class="input" type="number" min="1" max="5000" />
            </label>

            <div class="toolbar-actions">
              <button class="btn btn-muted" type="button" @click="clearQuery">Clear</button>
              <button class="btn btn-primary" type="button" :disabled="running" @click="runQuery">
                {{ running ? 'Running...' : 'Run Query' }}
              </button>
            </div>
          </div>

          <textarea
            v-model="sql"
            class="input sql-editor"
            spellcheck="false"
            placeholder="SELECT * FROM inspections LIMIT 20;"
          ></textarea>

          <div class="sample-box">
            <button
              v-for="sample in samples"
              :key="sample.label"
              class="btn btn-sm btn-outline"
              type="button"
              @click="sql = sample.sql"
            >
              {{ sample.label }}
            </button>
          </div>
        </section>

        <p v-if="error" class="card error-card">{{ error }}</p>

        <section v-if="result" class="card flat">
          <div class="card-title">
            <div>
              <h2>Result</h2>
              <p class="muted">
                {{ result.row_count }} row(s) · {{ result.duration_ms }} ms
                <span v-if="result.truncated"> · truncated</span>
              </p>
            </div>
            <button v-if="result.rows.length" class="btn btn-secondary" type="button" @click="downloadCsv">Download CSV</button>
          </div>

          <p v-if="!result.rows.length" class="muted">Query executed, but no rows were returned.</p>

          <div v-else class="table-wrap">
            <table class="table sql-result-table">
              <thead>
                <tr>
                  <th v-for="column in result.columns" :key="column">{{ column }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, rowIndex) in result.rows" :key="rowIndex">
                  <td v-for="column in result.columns" :key="column" :title="formatValue(row[column])">
                    {{ formatValue(row[column]) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </section>
  </AppLayout>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import AppLayout from '../components/AppLayout.vue'
import { executeAdminSql, getAdminSqlColumns, getAdminSqlTables } from '../services/adminSqlApi'

const sql = ref('SELECT *\nFROM inspections\nLIMIT 20;')
const limit = ref(100)
const running = ref(false)
const error = ref('')
const result = ref(null)

const tables = ref([])
const tablesLoading = ref(false)
const selectedTable = ref(null)
const columns = ref([])
const columnsLoading = ref(false)

const samples = [
  {
    label: 'Latest inspections',
    sql: 'SELECT id, inspection_no, status, inspection_date, created_at\nFROM inspections\nORDER BY created_at DESC\nLIMIT 20;'
  },
  {
    label: 'Table list',
    sql: "SELECT table_schema, table_name\nFROM information_schema.tables\nWHERE table_schema = 'public'\nORDER BY table_name;"
  },
  {
    label: 'Users by role',
    sql: 'SELECT r.code AS role, COUNT(*) AS total_users\nFROM users u\nJOIN roles r ON r.id = u.role_id\nGROUP BY r.code\nORDER BY r.code;'
  }
]

async function loadTables() {
  tablesLoading.value = true
  error.value = ''

  try {
    tables.value = await getAdminSqlTables()
  } catch (err) {
    error.value = err?.response?.data?.detail || 'Unable to load database tables.'
  } finally {
    tablesLoading.value = false
  }
}

async function selectTable(table) {
  selectedTable.value = table
  columns.value = []
  columnsLoading.value = true
  error.value = ''

  try {
    columns.value = await getAdminSqlColumns(table.table_schema, table.table_name)
  } catch (err) {
    error.value = err?.response?.data?.detail || 'Unable to load table columns.'
  } finally {
    columnsLoading.value = false
  }
}

function quoteIdentifier(value) {
  return `"${String(value).replaceAll('"', '""')}"`
}

function insertSelectQuery() {
  if (!selectedTable.value) return

  sql.value = `SELECT *\nFROM ${quoteIdentifier(selectedTable.value.table_schema)}.${quoteIdentifier(selectedTable.value.table_name)}\nLIMIT 20;`
}

async function runQuery() {
  running.value = true
  error.value = ''
  result.value = null

  try {
    result.value = await executeAdminSql(sql.value, limit.value)
  } catch (err) {
    error.value = err?.response?.data?.detail || 'SQL query failed.'
  } finally {
    running.value = false
  }
}

function clearQuery() {
  sql.value = ''
  result.value = null
  error.value = ''
}

function formatValue(value) {
  if (value === null || value === undefined) return ''
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

function downloadCsv() {
  if (!result.value?.rows?.length) return

  const columns = result.value.columns
  const escapeCsv = (value) => `"${formatValue(value).replaceAll('"', '""')}"`
  const lines = [
    columns.map(escapeCsv).join(','),
    ...result.value.rows.map((row) => columns.map((column) => escapeCsv(row[column])).join(','))
  ]

  const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'mch-admin-sql-result.csv'
  link.click()
  URL.revokeObjectURL(url)
}

onMounted(loadTables)
</script>

<style scoped>
.admin-sql-grid {
  grid-template-columns: 340px minmax(0, 1fr);
  align-items: start;
}

.schema-card {
  max-height: calc(100vh - 160px);
  overflow: auto;
}

.schema-list {
  display: grid;
  gap: 8px;
}

.schema-item {
  width: 100%;
  text-align: left;
  border: 1px solid var(--line);
  background: #f8fbff;
  border-radius: 14px;
  padding: 10px 12px;
}

.schema-item strong,
.schema-item span {
  display: block;
}

.schema-item span {
  margin-top: 4px;
  color: var(--muted);
  font-size: 12px;
}

.column-panel {
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px solid var(--line);
}

.column-toolbar {
  align-items: flex-start;
}

.column-list {
  list-style: none;
  padding: 0;
  margin: 12px 0 0;
}

.column-list li {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid #edf2f7;
}

.column-list small {
  color: var(--muted);
}

.query-grid {
  gap: 16px;
}

.limit-field {
  width: 160px;
}

.toolbar-actions,
.sample-box {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.sql-editor {
  min-height: 260px;
  margin-top: 14px;
  font-family: Consolas, Monaco, 'Courier New', monospace;
  line-height: 1.5;
  resize: vertical;
}

.sample-box {
  margin-top: 12px;
}

.error-card {
  color: var(--danger);
  border-color: #fecaca;
  background: #fef2f2;
}

.sql-result-table td {
  max-width: 360px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 1100px) {
  .admin-sql-grid {
    grid-template-columns: 1fr;
  }

  .schema-card {
    max-height: none;
  }
}
</style>
