# Frontend Code Tutorial — Vue 3

This document explains the frontend code, screen flow, API calls and how to extend the UI.

Frontend location:

```text
frontend/
├── src/
│   ├── main.js
│   ├── App.vue
│   ├── router/
│   ├── stores/
│   ├── services/
│   ├── components/
│   ├── views/
│   └── assets/
├── public/
├── Dockerfile
├── nginx.conf
├── package.json
└── vite.config.js
```

---

## 1. Frontend technology stack

The frontend uses:

```text
Vue 3
Vite
Pinia
Vue Router
Axios
CSS responsive layout
PWA manifest
```

It is designed as a responsive web application that works on:

```text
mobile browser
tablet
desktop
```

---

## 2. Frontend request lifecycle

```text
User opens screen
    ↓
Vue route loads view component
    ↓
View calls API through src/services/api.js
    ↓
Axios adds JWT Authorization header
    ↓
FastAPI returns JSON
    ↓
Vue renders cards/forms/tables
```

---

## 3. `src/main.js`

This is the Vue frontend entry point.

It does three things:

```text
1. Creates Vue app.
2. Registers Pinia store.
3. Registers Vue Router.
4. Imports global CSS.
```

Code concept:

```javascript
createApp(App).use(createPinia()).use(router).mount('#app')
```

---

## 4. `src/App.vue`

This is the root component.

It only contains:

```vue
<RouterView />
```

That means every actual screen is controlled by the router.

---

## 5. `src/router/index.js`

This file defines frontend URLs and maps them to Vue screens.

Typical routes:

```text
/login
/
/inspections/start
/inspections/:id
/reviews
/kpi
/master
```

It also has route protection logic.

Expected flow:

```text
If route requires authentication and token does not exist:
    redirect to /login
else:
    allow route
```

When adding a new screen, add a route here.

Example:

```javascript
{
  path: '/reports',
  name: 'reports',
  component: () => import('../views/ReportsView.vue'),
  meta: { requiresAuth: true }
}
```

---

## 6. `src/services/api.js`

This file creates the Axios instance.

Responsibilities:

```text
Set base URL
Attach Authorization header
Handle API calls from all views
```

Important concept:

```javascript
api.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})
```

Do not create new Axios instances in every component. Import this common `api` object.

Example:

```javascript
import { api } from '../services/api'
const response = await api.get('/dashboard/summary')
```

---

## 7. `src/stores/auth.js`

This Pinia store handles login state.

Responsibilities:

```text
login user
save access token
save refresh token
fetch current user
logout user
```

Frontend login process:

```text
LoginView.vue calls auth.login()
    ↓
auth store calls POST /auth/login
    ↓
tokens are saved in localStorage
    ↓
/me is called to fetch user details
    ↓
user is redirected to dashboard
```

Important state:

```text
user
token
isAuthenticated
```

---

## 8. `src/assets/styles.css`

This file contains global styling.

It includes reusable classes such as:

```text
page/card/grid/button/input/badge/table
```

The UI is kept simple so it is easy to customize later.

For production UI improvement, add:

```text
better mobile camera layout
sticky submit footer
toast notifications
loading skeletons
confirmation modals
role-based side menu items
```

---

## 9. Components

### `components/AppLayout.vue`

This is the main layout used after login.

It usually contains:

```text
sidebar/topbar
navigation links
logout button
main content area
```

All authenticated screens should use:

```vue
<AppLayout>
  screen content
</AppLayout>
```

### `components/StatCard.vue`

Small reusable dashboard card.

Props:

```text
label
value
```

Used in dashboard screens.

### `components/AttributeCard.vue`

This is the most important inspection form component.

It renders one inspection attribute and its sub-areas.

It receives:

```text
attribute
grades
model
```

It emits:

```text
media-selected
```

Concept:

```text
Parent view owns data.
AttributeCard displays fields and emits selected media files.
Parent uploads media using API.
```

This is good Vue design because API logic stays in the view and the card remains reusable.

---

## 10. Views

### `views/LoginView.vue`

Screen purpose:

```text
User login
```

Flow:

```text
User enters username/password
    ↓
submit form
    ↓
auth store calls POST /auth/login
    ↓
redirect to dashboard
```

### `views/DashboardView.vue`

Screen purpose:

```text
Show summary cards and quick actions
```

API used:

```text
GET /dashboard/summary
```

Displayed cards:

```text
Contracts
Stations
Inspections
Pending Reviews
Generated Penalties
```

### `views/InspectionStartView.vue`

Screen purpose:

```text
Start new station inspection
```

Important form fields:

```text
contract
station
inspection type
GPS latitude
GPS longitude
gps accuracy
remarks
```

API flow:

```text
GET /master/bootstrap
POST /inspections/start
```

After successful start, user is redirected to:

```text
/inspections/{inspection_id}
```

### GPS capture

The screen uses browser geolocation.

Expected browser permission flow:

```text
Browser asks location permission
    ↓
user allows
    ↓
latitude/longitude/accuracy stored in form
```

Production note: on mobile, GPS is more accurate over HTTPS. For production, run the app with HTTPS.

---

### `views/InspectionFormView.vue`

Screen purpose:

```text
Fill checklist, upload media, save draft and submit inspection
```

API calls:

```text
GET  /inspections/{id}
GET  /inspections/checklist?contract_id=...&station_id=...
PUT  /inspections/{id}/draft
POST /inspections/{id}/submit
POST /inspections/{id}/media
```

Data structure:

```javascript
models = {
  [attributeId]: {
    score: {
      attribute_id,
      grade_code,
      remarks
    },
    observations: {
      [subAreaId]: {
        attribute_id,
        sub_area_id,
        is_applicable,
        na_reason,
        observation_text
      }
    }
  }
}
```

When saving draft or submitting, the view converts `models` into backend payload:

```javascript
{
  attribute_scores: [...],
  observations: [...]
}
```

### Media upload

When user selects photo/video:

```text
AttributeCard emits media-selected
    ↓
InspectionFormView creates FormData
    ↓
POST /inspections/{id}/media
```

FormData fields:

```text
attribute_id
sub_area_id
media_type
file
```

Production improvement:

```text
show upload progress bar
show uploaded photo preview
compress photos before upload
capture photo directly from camera
block submit until uploads complete
```

---

### `views/ReviewQueueView.vue`

Screen purpose:

```text
Show inspections pending review
```

API used:

```text
GET /reviews/pending
```

Production extension:

```text
Add action buttons for Line Manager, DGM and GM.
Open inspection detail modal.
Show photo/video evidence.
Add review comments.
Submit review action.
```

---

### `views/KpiDashboardView.vue`

Screen purpose:

```text
Show KPI score and penalties
```

Possible APIs:

```text
GET /kpi/station-scores
GET /kpi/contract-scores
GET /kpi/penalties
POST /kpi/calculate/monthly
```

Production extension:

```text
Add contract filter
Add billing cycle filter
Add line filter
Add export to Excel/PDF
Add charts
```

---

### `views/MasterDataView.vue`

Screen purpose:

```text
Show master data summary
```

Uses:

```text
GET /master/bootstrap
```

Production extension:

```text
Create/edit stations
Create/edit contracts
Map stations to contracts
Assign user access
Create billing cycles
Upload monthly bill values
```

---

## 11. How frontend and backend paths match

Axios base URL normally points to:

```text
/api/v1
```

So frontend call:

```javascript
api.get('/dashboard/summary')
```

becomes backend URL:

```text
/api/v1/dashboard/summary
```

Nginx routes `/api/` requests to FastAPI.

---

## 12. How to add a new screen

Example: add Reports screen.

### Step 1: Create view

Create:

```text
src/views/ReportsView.vue
```

Basic template:

```vue
<template>
  <AppLayout>
    <h1>Reports</h1>
    <div class="card">Reports will appear here.</div>
  </AppLayout>
</template>

<script setup>
import AppLayout from '../components/AppLayout.vue'
</script>
```

### Step 2: Add route

Edit:

```text
src/router/index.js
```

Add:

```javascript
{
  path: '/reports',
  name: 'reports',
  component: () => import('../views/ReportsView.vue'),
  meta: { requiresAuth: true }
}
```

### Step 3: Add menu link

Edit:

```text
src/components/AppLayout.vue
```

Add:

```vue
<RouterLink to="/reports">Reports</RouterLink>
```

---

## 13. How to add a new API call in frontend

Use existing Axios instance:

```javascript
import { api } from '../services/api'

const { data } = await api.get('/kpi/penalties')
```

For POST:

```javascript
await api.post('/reviews/10/line-manager', {
  action: 'RECOMMEND_PENALTY',
  comments: 'Penalty recommended due to repeated low grading.',
  recommended_penalty_amount: 5000
})
```

For file upload:

```javascript
const fd = new FormData()
fd.append('file', file)
fd.append('attribute_id', attributeId)
fd.append('sub_area_id', subAreaId)
fd.append('media_type', 'PHOTO')

await api.post(`/inspections/${inspectionId}/media`, fd, {
  headers: { 'Content-Type': 'multipart/form-data' }
})
```

---

## 14. Role-based UI rendering

The backend already enforces permissions. The frontend should also hide/show UI for better UX.

Example:

```javascript
const canReview = computed(() => ['AM_MGR_LINE','DGM_LINE','SUPER_ADMIN'].includes(auth.user?.role))
```

Then:

```vue
<button v-if="canReview">Review</button>
```

Important: frontend hiding is only for convenience. Backend must always validate permissions.

---

## 15. Frontend debugging checklist

### Blank page

Check:

```bash
docker compose logs frontend
docker compose logs nginx
```

Also check browser console.

### Login API failing

Open browser Network tab and check:

```text
/api/v1/auth/login response
```

Common causes:

```text
backend not running
seed data not loaded
wrong username/password
CORS problem
nginx route issue
```

### API says 401

Check:

```text
access token exists in localStorage
token has not expired
SECRET_KEY did not change
user is active
```

### GPS not working

Check:

```text
browser location permission
HTTPS in production
mobile GPS setting
```

### File upload failing

Check:

```text
file size
file type
backend media endpoint logs
MinIO container logs
```

---

## 16. Recommended UI improvements before production

Add these before full field rollout:

```text
1. Uploaded media preview and delete before submission.
2. Upload progress percentage.
3. Offline draft support using IndexedDB.
4. Better validation messages before submit.
5. Confirmation modal on final submit.
6. Role-based side menu.
7. Review detail page with evidence viewer.
8. Monthly KPI chart page.
9. PDF/Excel report download page.
10. Session expiry warning.
```
