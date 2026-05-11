<!-- 
<template>
  <div class="login-page">
    <img src="../assets/MCH-bg.png" alt="DMRC" class="bg-image" />
    <div class="login-visual">
      <img src="../assets/dmrc-logo.svg" alt="DMRC" class="login-logo" />
      <h1>Real-Time Housekeeping Inspection Platform</h1>
      <p>Professional KPI-6 inspection workflow with geo-tagged evidence, role-wise review, dashboard analytics and PDF record keeping.</p>
    </div>
    <form class="card login-card" @submit.prevent="submit">
      <h2>Sign in</h2>
      <p class="muted">Use demo credentials or your assigned employee login.</p>
      <label><span class="label">Username</span><input class="input" v-model="username" autocomplete="username" /></label>
      <label><span class="label">Password</span><input class="input" type="password" v-model="password" autocomplete="current-password" /></label>
      <button class="btn btn-primary" :disabled="auth.loading">Login</button>
      <p v-if="error" class="badge red">{{ error }}</p>
      <div class="demo-box">
        <strong>Demo users</strong>
        <span>admin/admin123 · sm01/sm123 · eit01/eit123 · lm01/lm123 · dgm01/dgm123 · gm01/gm123</span>
      </div>
    </form>
  </div>
</template>
<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
const router = useRouter(); const auth = useAuthStore(); const username = ref('admin'); const password = ref('admin123'); const error = ref('')
async function submit(){ try { error.value=''; await auth.login(username.value, password.value); router.push('/') } catch(e){ error.value=e?.response?.data?.detail || 'Login failed' } }
</script>
<style scoped>
.login-page { min-height:100vh; display:grid; grid-template-columns: 1.1fr .9fr; background: radial-gradient(circle at 10% 10%, rgba(215,25,32,.16), transparent 30%), linear-gradient(135deg,#eaf1ff,#ffffff); }
.login-visual { padding:70px; display:flex; flex-direction:column; justify-content:center; }
.login-logo { width:180px; margin-bottom:28px; box-shadow:0 18px 40px rgba(15,23,42,.12); border-radius:18px; }
.login-visual h1 { max-width:720px; }
.login-visual p { max-width:620px; color:#526179; font-size:18px; line-height:1.65; }
.login-card { align-self:center; justify-self:center; width:min(440px, 92vw); display:grid; gap:16px; }
.demo-box { background:#f5f8fd; border:1px solid #dbe3f0; border-radius:16px; padding:12px; color:#475569; font-size:13px; line-height:1.5; }
.demo-box strong { display:block; color:#0f172a; }
@media(max-width: 880px){ .login-page { grid-template-columns:1fr; } .login-visual { padding:30px 20px 0; } .login-card { margin:24px auto; } }
</style> -->
<template>
  <div class="login-page">

    <!-- BACKGROUND -->
    <div class="bg-wrapper">
      <img
        src="../assets/MCH-bg.png"
        alt="Background"
        class="bg-image"
      />

      <div class="bg-overlay"></div>
    </div>

    <!-- CENTER CONTAINER -->
    <div class="main-container">

      <!-- LEFT INFO CARD -->
      <div class="info-card">

        <!-- <img
          src="../assets/dmrc-logo.svg"
          alt="DMRC"
          class="login-logo"
        /> -->

        <h1>
          Real-Time Housekeeping Inspection Platform
        </h1>

        <p>
          Professional KPI-6 inspection workflow with geo-tagged evidence,
          role-wise review, dashboard analytics and PDF record keeping.
        </p>

      </div>

      <!-- LOGIN CARD -->
      <form
        class="login-card"
        @submit.prevent="submit"
      >
        <h2>Sign in</h2>

        <p class="muted">
          Use demo credentials or your assigned employee login.
        </p>

        <label>
          <span class="label">Username</span>

          <input
            class="input"
            v-model="username"
            autocomplete="username"
            placeholder="Enter username"
          />
        </label>

        <label>
          <span class="label">Password</span>

          <input
            class="input"
            type="password"
            v-model="password"
            autocomplete="current-password"
            placeholder="Enter password"
          />
        </label>

        <button
          class="btn-primary"
          :disabled="auth.loading"
        >
          {{ auth.loading ? 'Signing in...' : 'Login' }}
        </button>

        <p
          v-if="error"
          class="error-box"
        >
          {{ error }}
        </p>

        <div class="demo-box">
          <strong>Demo users</strong>

          <span>
            admin/admin123 · sm01/sm123 · eit01/eit123 ·
            lm01/lm123 · dgm01/dgm123 · gm01/gm123
          </span>
        </div>

      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()

const username = ref('admin')
const password = ref('admin123')
const error = ref('')

async function submit() {
  try {
    error.value = ''

    await auth.login(
      username.value,
      password.value
    )

    router.push('/')

  } catch (e) {
    error.value =
      e?.response?.data?.detail || 'Login failed'
  }
}
</script>

<style scoped>

/* PAGE */
.login-page {
  position: relative;

  width: 100%;
  min-height: 100vh;

  display: flex;
  align-items: center;
  justify-content: center;

  padding: 28px;

  overflow: hidden;
}

/* BACKGROUND */
.bg-wrapper {
  position: absolute;
  inset: 0;
  z-index: 0;
}

.bg-image {
  width: 100%;
  height: 100%;

  object-fit: cover;

  /* blur only background */
  filter: blur(1px);

  transform: scale(1.05);
}

.bg-overlay {
  position: absolute;
  inset: 0;

  background:
    linear-gradient(
      135deg,
      rgba(0, 0, 0, 0.45),
      rgba(0, 0, 0, 0.28)
    );
}

/* MAIN CONTAINER */
.main-container {
  position: relative;
  z-index: 2;

  width: 60%;
  max-width: 860px;

  display: flex;
  align-items: stretch;

  border-radius: 24px;
  overflow: hidden;

  box-shadow:
    0 20px 60px rgba(0, 0, 0, 0);
}

/* LEFT INFO CARD */
.info-card {
  flex: 0.7;

  display: flex;
  flex-direction: column;
  justify-content: center;

  min-height: 540px;

  padding: 38px;

  background:
    rgba(120, 194, 225, 0.832);

  color: #111827;

  border-right:
    1px solid rgba(0, 0, 0, 0.06);
}

/* LOGO */
.login-logo {
  width: 90px;

  background: #f3f4f6;

  padding: 10px;

  border-radius: 16px;

  margin-bottom: 24px;
}

/* TITLE */
.info-card h1 {
  font-size: 2rem;
  line-height: 1.2;

  margin-bottom: 14px;

  font-weight: 700;

  color: #111827;
}

/* DESCRIPTION */
.info-card p {
  font-size: 0.96rem;
  line-height: 1.75;
  /* background-color: #aac6ee; */
  color: #1b2026;

  max-width: 360px;
}

/* LOGIN CARD */
.login-card {
  width: 400px;

  min-height: 540px;

  display: flex;
  flex-direction: column;
  justify-content: center;

  gap: 16px;

  padding: 38px;

  background:
    rgba(247, 251, 249, 0.525);

  color: #111827;
}

/* LOGIN TITLE */
.login-card h2 {
  font-size: 2rem;
  margin: 0;
}

/* SUBTEXT */
.muted {
  font-size: 14px;
  color: #6b7280;

  margin-bottom: 6px;
}

/* LABEL */
.label {
  display: block;

  margin-bottom: 8px;

  font-size: 14px;
  font-weight: 600;

  color: #374151;
}

/* INPUT */
.input {
  width: 100%;

  padding: 14px 15px;

  border-radius: 14px;

  border:
    1px solid #d1d5db;

  background: #f9fafb;

  color: #111827;

  font-size: 14px;

  outline: none;

  transition: 0.25s ease;
}

.input:focus {
  border-color: #2563eb;

  background: white;

  box-shadow:
    0 0 0 4px rgba(37, 99, 235, 0.12);
}

.input::placeholder {
  color: #9ca3af;
}

/* BUTTON */
.btn-primary {
  width: 100%;

  padding: 14px;

  border: none;
  border-radius: 14px;

  background: #111827;

  color: white;

  font-size: 15px;
  font-weight: 700;

  cursor: pointer;

  transition: 0.25s ease;

  margin-top: 4px;
}

.btn-primary:hover {
  background: #1f2937;

  transform: translateY(-1px);
}

.btn-primary:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

/* ERROR */
.error-box {
  background: #fee2e2;

  color: #b91c1c;

  padding: 12px;

  border-radius: 12px;

  font-size: 13px;
  font-weight: 500;
}

/* DEMO BOX */
.demo-box {
  margin-top: 6px;

  background: #f3f4f6;

  border:
    1px solid #e5e7eb;

  border-radius: 14px;

  padding: 14px;

  font-size: 12px;
  line-height: 1.7;

  color: #4b5563;
}

.demo-box strong {
  display: block;

  margin-bottom: 4px;

  color: #111827;
}

/* TABLET */
@media (max-width: 992px) {

  .main-container {
    flex-direction: column;

    max-width: 520px;
  }

  .info-card {
    min-height: auto;

    text-align: center;
    align-items: center;

    border-right: none;

    border-bottom:
      1px solid rgba(0, 0, 0, 0.06);
  }

  .info-card p {
    max-width: 100%;
  }

  .login-card {
    width: 100%;
    min-height: auto;
  }
}

/* MOBILE */
@media (max-width: 600px) {

  .login-page {
    padding: 16px;
  }

  .info-card,
  .login-card {
    padding: 26px 22px;
  }

  .info-card h1 {
    font-size: 1.6rem;
  }

  .info-card p {
    font-size: 0.9rem;
  }

  .login-logo {
    width: 76px;
  }

  .login-card h2 {
    font-size: 1.6rem;
  }

  .input {
    padding: 12px;
  }

  .btn-primary {
    padding: 13px;
  }
}

</style>