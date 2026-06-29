<template>
  <main class="login-page">
    <div class="login-bg" aria-hidden="true"></div>

    <section class="login-shell" aria-label="Login panel">
      <div class="info-card">
        <img src="../assets/dmrc-logo.svg" alt="DMRC" class="login-logo" />
        <!-- <p class="eyebrow">KPI-6 Housekeeping</p> -->
        <h1>Comprehensive Housekeeping Inspection Platform</h1>
        <p class="info-copy">
          Advanced analytics, monitoring and automated KPI workflows.
        </p>
      </div>

      <form class="login-card" @submit.prevent="submit">
        <div>
          <h2>Sign in</h2>
          <!-- <p class="muted">Employee Login.</p> -->
        </div>

        <label>
          <span class="label">Username</span>
          <input class="input" v-model.trim="username" placeholder="Enter username" />
        </label>

        <label>
          <span class="label">Password</span>
          <input class="input" type="password" v-model="password" placeholder="Enter password" />
        </label>

        <button class="btn btn-primary login-btn" :disabled="auth.loading">
          {{ auth.loading ? 'Signing in...' : 'Login' }}
        </button>

        <p v-if="error" class="error-box">{{ error }}</p>

        <div class="demo-box">
          <strong>For assistance and queries contact : </strong>
          <!-- <span>admin/admin123 · sm01/sm123 · eit01/eit123 · lm01/lm123 · dgm01/dgm123 · gm01/gm123</span> -->
          <span>Sh. Ankit Arya/ IT Cell Ops - 8800460307 || Ext. - 113755</span>          
        </div>
      </form>
    </section>
  </main>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const username = ref('')
const password = ref('')

const error = ref('')

async function submit() {
  try {
    error.value = ''
    await auth.login(username.value, password.value)
    router.push('/')
  } catch (e) {
    // error.value = e?.response?.data?.detail || 'Login failed'
    error.value = 'Login failed'
  }
}
</script>

<style scoped>
.login-page {
  position: relative;
  min-height: 100vh;
  width: 100%;
  display: grid;
  place-items: center;
  padding: clamp(16px, 4vw, 40px);
  overflow-x: hidden;
  overflow-y: auto;
  background: #071b46;
}

.login-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  background:
    radial-gradient(circle at 15% 10%, rgba(215, 25, 32, .36), transparent 30%),
    radial-gradient(circle at 85% 10%, rgba(120, 194, 225, .32), transparent 32%),
    linear-gradient(135deg, rgba(6, 26, 68, .94), rgba(9, 43, 111, .78)),
    linear-gradient(135deg, #eaf1ff, #ffffff);
}

.login-bg::after {
  content: "";
  position: absolute;
  inset: 0;
  background:
    linear-gradient(120deg, rgba(255,255,255,.08), transparent 35%),
    repeating-linear-gradient(135deg, rgba(255,255,255,.06) 0 1px, transparent 1px 18px);
  opacity: .58;
}

.login-shell {
  position: relative;
  z-index: 1;
  width: min(920px, 100%);
  display: grid;
  grid-template-columns: minmax(0, .95fr) minmax(360px, .8fr);
  border-radius: 28px;
  overflow: hidden;
  box-shadow: 0 24px 70px rgba(2, 8, 23, .30);
  border: 1px solid rgba(255,255,255,.25);
  background: rgba(255,255,255,.72);
  backdrop-filter: blur(10px);
}

.info-card {
  min-width: 0;
  padding: clamp(28px, 5vw, 46px);
  display: flex;
  flex-direction: column;
  justify-content: center;
  color: #0f172a;
  background:
    radial-gradient(circle at 0 0, rgba(215,25,32,.16), transparent 34%),
    linear-gradient(145deg, rgba(212, 239, 249, .94), rgba(239, 247, 255, .88));
}

.login-logo {
  width: min(160px, 52vw);
  height: auto;
  display: block;
  margin-bottom: 24px;
  border-radius: 18px;
  box-shadow: 0 12px 28px rgba(15, 23, 42, .13);
  background: white;
}

.eyebrow {
  margin-bottom: 10px;
  color: #092b6f;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: .08em;
  font-size: 12px;
}

.info-card h1 {
  margin-bottom: 16px;
  font-size: clamp(28px, 4vw, 42px);
  line-height: 1.06;
  letter-spacing: -.045em;
}

.info-copy {
  max-width: 430px;
  color: #334155;
  line-height: 1.7;
  font-size: 16px;
  margin-bottom: 0;
}

.login-card {
  min-width: 0;
  padding: clamp(28px, 5vw, 44px);
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 16px;
  background: rgba(255,255,255,.86);
  color: #111827;
}

.login-card h2 {
  margin-bottom: 6px;
  font-size: clamp(26px, 3vw, 34px);
  letter-spacing: -.04em;
}

.login-btn { width: 100%; }

.error-box {
  margin: 0;
  background: #fee2e2;
  color: #991b1b;
  padding: 12px;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 700;
}

.demo-box {
  margin-top: 2px;
  background: #f3f6fb;
  border: 1px solid #dbe3f0;
  border-radius: 16px;
  padding: 13px;
  font-size: 12px;
  line-height: 1.65;
  color: #4b5563;
}

.demo-box strong {
  display: block;
  margin-bottom: 4px;
  color: #111827;
}

@media (max-width: 860px) {
  .login-page {
    align-items: start;
    padding: 16px;
  }

  .login-shell {
    grid-template-columns: 1fr;
    width: min(540px, 100%);
    border-radius: 24px;
  }

  .info-card {
    text-align: center;
    align-items: center;
    padding: 24px 22px 20px;
  }

  .login-logo {
    width: min(130px, 42vw);
    margin-bottom: 16px;
  }

  .info-copy {
    max-width: 100%;
  }

  .login-card {
    padding: 24px 22px 26px;
  }
}

@media (max-width: 480px) {
  .login-page { padding: 12px; }
  .login-shell { border-radius: 20px; }
  .info-card { padding: 20px 16px 16px; }
  .login-card { padding: 20px 16px 22px; }
  .info-card h1 { font-size: 24px; }
  .info-copy { font-size: 14px; line-height: 1.55; }
  .login-logo { width: 112px; }
  .demo-box { font-size: 11px; }
}

@media (max-height: 680px) and (min-width: 861px) {
  .login-page { place-items: start center; }
  .login-shell { min-height: auto; }
}
</style>
