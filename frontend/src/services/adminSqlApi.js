import { api } from './api'

export async function getAdminSqlTables() {
  const { data } = await api.get('/admin-sql/tables')
  return data
}

export async function getAdminSqlColumns(tableSchema, tableName) {
  const { data } = await api.get('/admin-sql/columns', {
    params: { table_schema: tableSchema, table_name: tableName }
  })
  return data
}

export async function executeAdminSql(sql, limit = 100) {
  const { data } = await api.post('/admin-sql/execute', { sql, limit })
  return data
}
