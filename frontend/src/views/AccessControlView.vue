<template>
  <AppLayout>
    <section class="card hero-panel">
      <h1>Access Control & User Management</h1>
      <p class="muted">
        Admin creates SM, LM, DGM, EIT and other users here. Then map stations and reporting hierarchy on the same page.
        There is no public sign-up flow.
      </p>
    </section>

    <section class="card section-gap" v-if="error">
      <p class="error-text">{{ error }}</p>
    </section>
    <section class="card section-gap success-card" v-if="success">
      <p>{{ success }}</p>
    </section>

    <section class="grid grid-2 section-gap" v-if="!loading && !loadError">
      <div class="card panel-card">
        <div class="card-title">
          <div>
            <h2>{{ editingUserId ? 'Edit user' : 'Create user credentials' }}</h2>
            <p class="muted small-text">Only Admin/HK Cell can create login credentials. Password is set by admin and can be reset later.</p>
          </div>
          <button v-if="editingUserId" class="btn btn-muted" @click="resetUserForm">New user</button>
        </div>

        <div class="requirements-box">
          <strong>Minimum requirements</strong>
          <ul>
            <li>Full name: required, at least 2 characters.</li>
            <li>Username: required, at least 3 characters.</li>
            <li v-if="!editingUserId">Temporary password: required, at least 6 characters.</li>
            <li>Role: required.</li>
            <li>Employee no, mobile and email are optional.</li>
          </ul>
        </div>

        <div class="form-grid">
          <div>
            <label class="label" for="access-emp-number">Employee no</label>
            <input id="access-emp-number" class="input" v-model.trim="userForm.emp_number" placeholder="e.g. 12345" />
            <p class="field-hint">Optional. Use official employee number if available.</p>
          </div>
          <div>
            <label class="label" for="access-name">Full name <span class="required-star">*</span></label>
            <input
              id="access-name"
              class="input"
              :class="{ 'input-invalid': submittedUserForm && userFormErrors.name }"
              v-model.trim="userForm.name"
              placeholder="e.g. Rajesh Kumar"
              autocomplete="name"
            />
            <p class="field-hint">Required. Minimum 2 characters.</p>
            <p v-if="submittedUserForm && userFormErrors.name" class="field-error">{{ userFormErrors.name }}</p>
          </div>
          <div>
            <label class="label" for="access-username">Username <span class="required-star">*</span></label>
            <input
              id="access-username"
              class="input"
              :class="{ 'input-invalid': submittedUserForm && userFormErrors.username }"
              v-model.trim="userForm.username"
              placeholder="e.g. sm.rajesh"
              autocomplete="username"
            />
            <p class="field-hint">Required. Minimum 3 characters. Use a simple login name like <code>sm.lajpat</code>.</p>
            <p v-if="submittedUserForm && userFormErrors.username" class="field-error">{{ userFormErrors.username }}</p>
          </div>
          <div v-if="!editingUserId">
            <label class="label" for="access-password">Temporary password <span class="required-star">*</span></label>
            <input
              id="access-password"
              class="input"
              :class="{ 'input-invalid': submittedUserForm && userFormErrors.password }"
              v-model="userForm.password"
              type="text"
              placeholder="Minimum 6 characters"
              autocomplete="new-password"
            />
            <p class="field-hint">Required for new users. Minimum 6 characters. Share it securely and ask the user to change it later.</p>
            <p v-if="submittedUserForm && userFormErrors.password" class="field-error">{{ userFormErrors.password }}</p>
          </div>
          <div>
            <label class="label" for="access-role">Role <span class="required-star">*</span></label>
            <select
              id="access-role"
              class="input"
              :class="{ 'input-invalid': submittedUserForm && userFormErrors.role_code }"
              v-model="userForm.role_code"
            >
              <option value="">Select role</option>
              <option v-for="role in roles" :key="role" :value="role">{{ roleLabel(role) }}</option>
            </select>
            <p class="field-hint">Required. Role decides what the user can see and do.</p>
            <p v-if="submittedUserForm && userFormErrors.role_code" class="field-error">{{ userFormErrors.role_code }}</p>
          </div>
          <div>
            <label class="label" for="access-mobile">Mobile</label>
            <input id="access-mobile" class="input" v-model.trim="userForm.mobile" placeholder="optional" autocomplete="tel" />
            <p class="field-hint">Optional.</p>
          </div>
          <div>
            <label class="label" for="access-email">Email</label>
            <input id="access-email" class="input" v-model.trim="userForm.email" placeholder="optional" autocomplete="email" />
            <p class="field-hint">Optional. Used only if your workflow needs email communication later.</p>
          </div>
          <label class="toggle-row">
            <input type="checkbox" v-model="userForm.is_active" />
            <span>Active login</span>
          </label>
        </div>

        <button class="btn btn-primary full-button" :disabled="savingUser" @click="saveUser">
          {{ savingUser ? 'Saving...' : editingUserId ? 'Update user' : 'Create login user' }}
        </button>

        <div class="hint-box">
          <strong>Testing example:</strong>
          Create <code>sm.lajpat</code> with role <code>STATION_MANAGER</code>, then map that user to Lajpat Nagar station below.
        </div>
      </div>

      <div class="card panel-card">
        <div class="card-title">
          <div>
            <h2>Existing users</h2>
            <p class="muted small-text">Edit role/status or reset password. Passwords are never displayed after creation.</p>
          </div>
          <button class="btn btn-muted" @click="load">Refresh</button>
        </div>

        <input class="input" v-model.trim="userSearch" placeholder="Search name, username, emp no, role" />

        <div class="table-wrap user-table-wrap">
          <table class="table compact-table">
            <thead>
              <tr>
                <th>User</th>
                <th>Role</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="u in filteredUsers" :key="u.id">
                <td>
                  <strong>{{ u.name }}</strong><br />
                  <span class="muted small-text">{{ u.username }} · {{ u.emp_number || 'No emp no' }}</span>
                </td>
                <td><span class="badge blue">{{ roleLabel(u.role) }}</span></td>
                <td><span class="badge" :class="u.is_active ? 'green' : 'red'">{{ u.is_active ? 'Active' : 'Inactive' }}</span></td>
                <td class="action-cell">
                  <button class="btn btn-muted tiny-btn" @click="editUser(u)">Edit</button>
                  <button class="btn btn-muted tiny-btn" @click="resetPassword(u)">Reset password</button>
                  <button class="btn btn-muted tiny-btn" @click="toggleUserStatus(u)">{{ u.is_active ? 'Deactivate' : 'Activate' }}</button>
                </td>
              </tr>
              <tr v-if="!filteredUsers.length">
                <td colspan="4" class="muted">No users found.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <section class="grid grid-2 section-gap" v-if="!loading && !loadError">
      <div class="card panel-card">
        <div class="card-title">
          <div>
            <h2>User scope</h2>
            <p class="muted small-text">Assign stations/lines directly to SM, EIT or any operational user.</p>
          </div>
        </div>

        <label class="label">Select user</label>
        <select class="input" v-model.number="selectedAccessUserId">
          <option :value="0">Select active user</option>
          <option v-for="u in activeUsers" :key="u.id" :value="u.id">
            {{ u.name }} · {{ u.username }} · {{ roleLabel(u.role) }}
          </option>
        </select>

        <div v-if="selectedAccessUser" class="user-strip">
          <strong>{{ selectedAccessUser.name }}</strong>
          <span>{{ roleLabel(selectedAccessUser.role) }}</span>
        </div>

        <h3 class="mini-title">Station access</h3>
        <div class="mapping-list tall-list">
          <label class="check-row" v-for="s in stations" :key="s.id">
            <input type="checkbox" :value="s.id" v-model="selectedStationIds" />
            <span>{{ s.station_name }} <small>{{ s.station_code }}</small></span>
          </label>
        </div>

        <h3 class="mini-title">Line access</h3>
        <div class="mapping-list compact-list">
          <label class="check-row" v-for="l in lines" :key="l.id">
            <input type="checkbox" :value="l.id" v-model="selectedLineIds" />
            <span>{{ l.line_name }} <small>{{ l.line_code }}</small></span>
          </label>
        </div>

        <button class="btn btn-primary full-button" :disabled="!selectedAccessUserId || savingAccess" @click="saveAccess">
          {{ savingAccess ? 'Saving...' : 'Save station/line access' }}
        </button>
      </div>

      <div class="card panel-card">
        <div class="card-title">
          <div>
            <h2>Reporting hierarchy</h2>
            <p class="muted small-text">Use this for LM → SM and DGM → LM forwarding and visibility.</p>
          </div>
        </div>

        <label class="label">Supervisor</label>
        <select class="input" v-model.number="selectedSupervisorId">
          <option :value="0">Select supervisor</option>
          <option v-for="u in supervisorUsers" :key="u.id" :value="u.id">
            {{ u.name }} · {{ u.username }} · {{ roleLabel(u.role) }}
          </option>
        </select>

        <div v-if="selectedSupervisor" class="flow-hint">
          <strong>Recommended mapping:</strong>
          <span v-if="isLm(selectedSupervisor.role)">Select SMs/EIT members under this LM.</span>
          <span v-else-if="isDgm(selectedSupervisor.role)">Select LMs under this DGM.</span>
          <span v-else-if="selectedSupervisor.role === 'GM_OPS'">Select DGMs under this GM/Ops.</span>
          <span v-else>Select subordinate users.</span>
        </div>

        <h3 class="mini-title">Subordinate users</h3>
        <div class="mapping-list tall-list">
          <label class="check-row" v-for="u in subordinateCandidates" :key="u.id">
            <input type="checkbox" :value="u.id" v-model="selectedSubordinateIds" />
            <span>{{ u.name }} <small>{{ u.username }} · {{ roleLabel(u.role) }}</small></span>
          </label>
          <p v-if="selectedSupervisorId && !subordinateCandidates.length" class="muted small-text">
            No logical subordinate candidates found for this role.
          </p>
        </div>

        <button class="btn btn-primary full-button" :disabled="!selectedSupervisorId || savingHierarchy" @click="saveHierarchy">
          {{ savingHierarchy ? 'Saving...' : 'Save reporting hierarchy' }}
        </button>
      </div>
    </section>

    <section class="card section-gap" v-if="!loading && !loadError">
      <div class="card-title">
        <div>
          <h2>Current hierarchy</h2>
          <p class="muted small-text">Active reporting links currently used by backend scope checks.</p>
        </div>
        <button class="btn btn-muted" @click="load">Refresh</button>
      </div>
      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>Supervisor</th>
              <th>Role</th>
              <th>Subordinate</th>
              <th>Role</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="link in hierarchyRows" :key="link.id">
              <td>{{ link.supervisor?.name || '-' }}</td>
              <td><span class="badge blue">{{ roleLabel(link.supervisor?.role) }}</span></td>
              <td>{{ link.subordinate?.name || '-' }}</td>
              <td><span class="badge">{{ roleLabel(link.subordinate?.role) }}</span></td>
            </tr>
            <tr v-if="!hierarchyRows.length">
              <td colspan="4" class="muted">No hierarchy mapped yet.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="card section-gap info-card">
      <h2>How this controls visibility</h2>
      <div class="info-grid">
        <div><strong>SM</strong><span>Create the SM user, then map station access. SM can inspect only mapped stations.</span></div>
        <div><strong>LM</strong><span>Create LM user, then map SM/EIT users under that LM.</span></div>
        <div><strong>DGM</strong><span>Create DGM user, then map LM users under that DGM.</span></div>
        <div><strong>Admin/HK Cell</strong><span>Creates credentials, resets passwords, deactivates users and maintains mappings.</span></div>
      </div>
    </section>
  </AppLayout>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import AppLayout from '../components/AppLayout.vue'
import { api } from '../services/api'

const loading = ref(true)
const loadError = ref('')
const error = ref('')
const success = ref('')
const users = ref([])
const roles = ref([])
const stations = ref([])
const lines = ref([])
const stationAccess = ref([])
const lineAccess = ref([])
const reportingLinks = ref([])

const userSearch = ref('')
const editingUserId = ref(0)
const savingUser = ref(false)
const submittedUserForm = ref(false)
const userForm = ref(defaultUserForm())

const selectedAccessUserId = ref(0)
const selectedStationIds = ref([])
const selectedLineIds = ref([])
const savingAccess = ref(false)

const selectedSupervisorId = ref(0)
const selectedSubordinateIds = ref([])
const savingHierarchy = ref(false)

const userById = computed(() => Object.fromEntries(users.value.map((u) => [u.id, u])))
const activeUsers = computed(() => users.value.filter((u) => u.is_active))
const selectedAccessUser = computed(() => userById.value[selectedAccessUserId.value])
const selectedSupervisor = computed(() => userById.value[selectedSupervisorId.value])

const filteredUsers = computed(() => {
  const q = userSearch.value.toLowerCase()
  if (!q) return users.value
  return users.value.filter((u) => [u.name, u.username, u.emp_number, u.email, u.mobile, u.role]
    .filter(Boolean)
    .some((value) => String(value).toLowerCase().includes(q)))
})

const supervisorUsers = computed(() => activeUsers.value.filter((u) => ['AM_MGR_LINE', 'AM_MGR_HK', 'DGM_LINE', 'DGM_HK', 'GM_OPS', 'SUPER_ADMIN', 'HK_CELL_ADMIN'].includes(u.role)))

const subordinateCandidates = computed(() => {
  const supervisor = selectedSupervisor.value
  if (!supervisor) return []
  return activeUsers.value.filter((u) => {
    if (u.id === supervisor.id) return false
    if (isLm(supervisor.role)) return ['STATION_MANAGER', 'EIT_MEMBER'].includes(u.role)
    if (isDgm(supervisor.role)) return ['AM_MGR_LINE', 'AM_MGR_HK'].includes(u.role)
    if (supervisor.role === 'GM_OPS') return ['DGM_LINE', 'DGM_HK'].includes(u.role)
    return true
  })
})

const hierarchyRows = computed(() => reportingLinks.value.map((link) => ({
  ...link,
  supervisor: userById.value[link.supervisor_user_id],
  subordinate: userById.value[link.subordinate_user_id]
})))

const userFormErrors = computed(() => validateUserForm())

const canSaveUser = computed(() => Object.keys(userFormErrors.value).length === 0)

function defaultUserForm() {
  return {
    emp_number: '',
    name: '',
    username: '',
    password: '',
    role_code: '',
    mobile: '',
    email: '',
    is_active: true
  }
}

function validateUserForm() {
  const errors = {}
  const name = userForm.value.name?.trim() || ''
  const username = userForm.value.username?.trim() || ''
  const password = userForm.value.password || ''

  if (!name) errors.name = 'Full name is required.'
  else if (name.length < 2) errors.name = 'Full name must be at least 2 characters.'

  if (!username) errors.username = 'Username is required.'
  else if (username.length < 3) errors.username = 'Username must be at least 3 characters.'

  if (!editingUserId.value) {
    if (!password) errors.password = 'Temporary password is required for new users.'
    else if (password.length < 6) errors.password = 'Temporary password must be at least 6 characters.'
  }

  if (!userForm.value.role_code) errors.role_code = 'Role is required.'

  return errors
}

function roleLabel(role) {
  const labels = {
    SUPER_ADMIN: 'Super Admin',
    HK_CELL_ADMIN: 'HK Cell Admin',
    GM_OPS: 'GM/Ops',
    DGM_LINE: 'DGM Line',
    DGM_HK: 'DGM HK',
    AM_MGR_LINE: 'Line Manager',
    AM_MGR_HK: 'HK Manager',
    STATION_MANAGER: 'Station Manager',
    EIT_MEMBER: 'External Inspection Team',
    AUDITOR: 'Auditor'
  }
  return labels[role] || role || '-'
}

function isLm(role) {
  return ['AM_MGR_LINE', 'AM_MGR_HK'].includes(role)
}

function isDgm(role) {
  return ['DGM_LINE', 'DGM_HK'].includes(role)
}

function fieldLabel(field) {
  const labels = {
    username: 'Username',
    password: 'Password',
    name: 'Full name',
    emp_number: 'Employee no',
    email: 'Email',
    mobile: 'Mobile',
    role_code: 'Role',
    station_ids: 'Station access',
    line_ids: 'Line access',
    user_id: 'User',
    supervisor_user_id: 'Supervisor',
    subordinate_user_ids: 'Subordinate users',
    is_active: 'Active login'
  }
  return labels[field] || String(field || '').replaceAll('_', ' ')
}

function detailItemToMessage(item) {
  if (!item) return ''
  if (typeof item === 'string') return item

  if (typeof item === 'object') {
    const loc = Array.isArray(item.loc) ? item.loc : []
    const field = loc.filter((part) => !['body', 'query', 'path'].includes(String(part))).pop()
    const label = field ? fieldLabel(field) : ''
    const message = item.msg || item.message || item.detail || ''
    if (label && message) return `${label}: ${message}`
    if (message) return String(message)
  }

  try {
    return JSON.stringify(item)
  } catch {
    return String(item)
  }
}

function formatApiError(e, fallback) {
  const data = e?.response?.data
  const detail = data?.detail ?? data?.message ?? data?.error

  if (Array.isArray(detail)) {
    const messages = detail.map(detailItemToMessage).filter(Boolean)
    return messages.length ? messages.join(' ') : fallback
  }

  if (typeof detail === 'string') return detail

  if (detail && typeof detail === 'object') {
    const message = detailItemToMessage(detail)
    return message || fallback
  }

  return fallback
}

async function load() {
  loading.value = true
  loadError.value = ''
  error.value = ''
  try {
    const [{ data: bootstrap }, { data: allUsers }] = await Promise.all([
      api.get('/access-control/bootstrap'),
      api.get('/users', { params: { include_inactive: true } })
    ])
    roles.value = bootstrap.roles || []
    users.value = allUsers || bootstrap.users || []
    stations.value = bootstrap.stations || []
    lines.value = bootstrap.lines || []
    stationAccess.value = bootstrap.station_access || []
    lineAccess.value = bootstrap.line_access || []
    reportingLinks.value = bootstrap.reporting_links || []
  } catch (e) {
    const message = formatApiError(e, 'Unable to load access-control data. Only Admin/HK Cell can manage users and mappings.')
    error.value = message
    loadError.value = message
  } finally {
    loading.value = false
  }
}

function clearMessages() {
  error.value = ''
  success.value = ''
}

function resetUserForm() {
  editingUserId.value = 0
  submittedUserForm.value = false
  userForm.value = defaultUserForm()
}

function editUser(user) {
  clearMessages()
  submittedUserForm.value = false
  editingUserId.value = user.id
  userForm.value = {
    emp_number: user.emp_number || '',
    name: user.name || '',
    username: user.username || '',
    password: '',
    role_code: user.role || '',
    mobile: user.mobile || '',
    email: user.email || '',
    is_active: Boolean(user.is_active)
  }
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function cleanPayload(payload) {
  const cleaned = { ...payload }
  for (const key of ['emp_number', 'email', 'mobile']) {
    if (cleaned[key] === '') cleaned[key] = null
  }
  return cleaned
}

async function saveUser() {
  submittedUserForm.value = true
  clearMessages()

  if (!canSaveUser.value) {
    error.value = 'Please fix the highlighted fields before saving.'
    return
  }

  savingUser.value = true
  try {
    if (editingUserId.value) {
      const payload = cleanPayload({ ...userForm.value })
      delete payload.password
      await api.put(`/users/${editingUserId.value}`, payload)
      success.value = 'User updated successfully.'
    } else {
      await api.post('/users', cleanPayload({ ...userForm.value }))
      success.value = `User created. Share username "${userForm.value.username}" and the temporary password entered by admin.`
      resetUserForm()
    }
    await load()
  } catch (e) {
    error.value = formatApiError(e, 'Unable to save user')
  } finally {
    savingUser.value = false
  }
}

async function resetPassword(user) {
  clearMessages()
  const password = window.prompt(`Enter new temporary password for ${user.name}\n\nMinimum requirement: at least 6 characters.`)
  if (!password) return
  if (password.length < 6) {
    error.value = 'Password must be at least 6 characters.'
    return
  }
  try {
    await api.put(`/users/${user.id}/password`, { password })
    success.value = `Password reset for ${user.name}. Share the new temporary password securely.`
  } catch (e) {
    error.value = formatApiError(e, 'Unable to reset password')
  }
}

async function toggleUserStatus(user) {
  clearMessages()
  const nextStatus = !user.is_active
  const label = nextStatus ? 'activate' : 'deactivate'
  if (!window.confirm(`Are you sure you want to ${label} ${user.name}?`)) return
  try {
    await api.put(`/users/${user.id}/status`, { is_active: nextStatus })
    success.value = `${user.name} ${nextStatus ? 'activated' : 'deactivated'} successfully.`
    await load()
  } catch (e) {
    error.value = formatApiError(e, 'Unable to update user status')
  }
}

watch(selectedAccessUserId, (id) => {
  selectedStationIds.value = stationAccess.value.filter((row) => row.user_id === id).map((row) => row.station_id)
  selectedLineIds.value = lineAccess.value.filter((row) => row.user_id === id).map((row) => row.line_id)
})

watch(selectedSupervisorId, (id) => {
  selectedSubordinateIds.value = reportingLinks.value.filter((row) => row.supervisor_user_id === id).map((row) => row.subordinate_user_id)
})

async function saveAccess() {
  savingAccess.value = true
  clearMessages()
  try {
    await api.put('/access-control/station-access', {
      user_id: selectedAccessUserId.value,
      station_ids: selectedStationIds.value.map(Number)
    })
    await api.put('/access-control/line-access', {
      user_id: selectedAccessUserId.value,
      line_ids: selectedLineIds.value.map(Number)
    })
    success.value = 'Station/line access saved.'
    await load()
  } catch (e) {
    error.value = formatApiError(e, 'Unable to save station/line access')
  } finally {
    savingAccess.value = false
  }
}

async function saveHierarchy() {
  savingHierarchy.value = true
  clearMessages()
  try {
    await api.put('/access-control/reporting-links', {
      supervisor_user_id: selectedSupervisorId.value,
      subordinate_user_ids: selectedSubordinateIds.value.map(Number),
      relation_type: 'REPORTING'
    })
    success.value = 'Reporting hierarchy saved.'
    await load()
  } catch (e) {
    error.value = formatApiError(e, 'Unable to save reporting hierarchy')
  } finally {
    savingHierarchy.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.section-gap { margin-top: 18px; }
.hero-panel h1 { margin-bottom: 8px; }
.panel-card { display: flex; flex-direction: column; gap: 12px; }
.small-text { font-size: 13px; }
.error-text { color: #b91c1c; font-weight: 800; }
.success-card { border-color: #bbf7d0; background: #f0fdf4; color: #166534; font-weight: 800; }
.form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.required-star { color: #b91c1c; }
.field-hint { margin: 5px 0 0; color: #64748b; font-size: 12px; line-height: 1.4; }
.field-hint code { background: #e0f2fe; border-radius: 6px; padding: 1px 5px; color: #0f3f8f; }
.field-error { margin: 5px 0 0; color: #b91c1c; font-size: 12px; font-weight: 800; line-height: 1.4; }
.input-invalid { border-color: #ef4444 !important; box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.12); }
.requirements-box {
  border: 1px solid #bfdbfe;
  background: #eff6ff;
  border-radius: 16px;
  padding: 12px 14px;
  color: #1e3a8a;
  font-size: 13px;
  line-height: 1.5;
}
.requirements-box strong { display: block; margin-bottom: 4px; }
.requirements-box ul { margin: 0; padding-left: 18px; }
.toggle-row { display: flex; align-items: center; gap: 10px; font-weight: 800; color: #0f172a; padding-top: 28px; }
.user-strip,
.flow-hint,
.hint-box {
  display: flex;
  gap: 8px;
  align-items: center;
  justify-content: space-between;
  border: 1px solid #dbeafe;
  background: #f8fbff;
  border-radius: 14px;
  padding: 10px 12px;
  color: #1e3a8a;
}
.flow-hint,
.hint-box { align-items: flex-start; flex-direction: column; }
.hint-box { font-size: 13px; line-height: 1.5; }
.hint-box code { background: #e0f2fe; border-radius: 6px; padding: 1px 5px; }
.mini-title { margin: 8px 0 0; font-size: 15px; }
.mapping-list {
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 8px;
  background: #fbfdff;
  overflow: auto;
}
.tall-list { max-height: 330px; }
.compact-list { max-height: 165px; }
.check-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 9px 8px;
  border-radius: 12px;
  cursor: pointer;
}
.check-row:hover { background: #eef6ff; }
.check-row input { margin-top: 2px; }
.check-row span { display: flex; flex-direction: column; gap: 2px; font-weight: 700; color: #0f172a; }
.check-row small { color: #64748b; font-weight: 600; }
.full-button { width: 100%; justify-content: center; }
.user-table-wrap { max-height: 520px; overflow: auto; }
.compact-table th,
.compact-table td { font-size: 13px; vertical-align: top; }
.action-cell { display: flex; flex-wrap: wrap; gap: 6px; }
.tiny-btn { padding: 7px 9px; font-size: 12px; }
.badge.green { background: #dcfce7; color: #166534; }
.badge.red { background: #fee2e2; color: #991b1b; }
.info-card { background: linear-gradient(135deg, #f8fbff, #ffffff); }
.info-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
.info-grid div { border: 1px solid #e2e8f0; border-radius: 16px; padding: 12px; background: white; }
.info-grid strong { display: block; margin-bottom: 6px; color: #0f3f8f; }
.info-grid span { color: #475569; font-size: 13px; line-height: 1.5; }
@media (max-width: 900px) {
  .info-grid,
  .form-grid { grid-template-columns: 1fr; }
  .toggle-row { padding-top: 0; }
  .action-cell { flex-direction: column; }
}
</style>
