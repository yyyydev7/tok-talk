<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { authError, authState, authenticate, checkAuth } from '../stores/tokTalk'
import { tr, uiLanguage } from '../stores/uiSettings'

const props = defineProps<{ mode: 'login' | 'signup' }>()
const route = useRoute()
const router = useRouter()
const authUsername = ref('')
const password = ref('')
const showPassword = ref(false)
const busy = ref(false)
const title = computed(() => props.mode === 'login' ? tr('다시 오셨군요') : tr('계정 만들기'))
const introKey = ref(0)

watch(() => props.mode, () => { authError.value = '' })
watch(uiLanguage, () => { introKey.value += 1 })

async function submit() {
  busy.value = true
  const success = await authenticate(props.mode, authUsername.value, password.value)
  busy.value = false
  if (!success) return
  password.value = ''

  if (props.mode === 'signup') {
    await router.replace({ name: 'login', query: { signup: 'complete' } })
    return
  }

  const requested = route.query.redirect
  const redirect = typeof requested === 'string' && requested.startsWith('/') && !requested.startsWith('//')
    ? requested
    : '/'
  await router.replace(redirect)
}

async function retryAuth() {
  await checkAuth(true)
}
</script>

<template>
  <main class="auth-layout">
    <section :key="introKey" class="auth-intro" aria-live="polite">
      <p class="auth-service-name">{{ tr('연구실 화학물질 안전정보 도우미', 'Laboratory Chemical Safety Information Assistant') }}</p>
      <div class="auth-brand-line"><h1 class="auth-brand-name">톡,talk</h1></div>
    </section>
    <section class="auth-card">
      <template v-if="authState === 'unavailable' || authState === 'checking'">
        <h2>{{ authState === 'checking' ? tr('인증 상태 확인 중') : tr('인증 서비스를 연결할 수 없습니다') }}</h2>
        <p class="muted">{{ authState === 'checking' ? tr('잠시만 기다려 주세요.') : tr('Java 인증 서버 상태를 확인한 뒤 다시 시도해 주세요.') }}</p>
        <p v-if="authError" class="inline-error" role="status">{{ tr(authError) }}</p>
        <button class="button button-primary full-button" type="button" :disabled="authState === 'checking'" @click="retryAuth">{{ tr('다시 확인') }}</button>
      </template>
      <template v-else>
        <h2>{{ title }}</h2>
        <p class="muted">{{ props.mode === 'login' ? tr('계정에 로그인해 안전정보를 확인하세요.') : tr('실습용 계정을 등록합니다.') }}</p>
        <p v-if="route.query.signup === 'complete'" class="success-message" role="status">{{ tr('가입이 완료됐습니다. 로그인해 주세요.') }}</p>
        <form class="auth-form" @submit.prevent="submit">
          <label for="username">{{ tr('아이디') }}</label>
          <input id="username" v-model="authUsername" autocomplete="username" :placeholder="tr('아이디 입력')" required />
          <label for="password">{{ tr('비밀번호') }}</label>
          <div class="password-field">
            <input id="password" v-model="password" :autocomplete="props.mode === 'login' ? 'current-password' : 'new-password'" :type="showPassword ? 'text' : 'password'" minlength="8" maxlength="128" :placeholder="tr('비밀번호 입력')" required />
            <button
              class="password-visibility"
              type="button"
              :aria-label="showPassword ? tr('비밀번호 숨기기') : tr('비밀번호 표시')"
              :aria-pressed="showPassword"
              @click="showPassword = !showPassword"
            >
              <svg v-if="!showPassword" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M2.5 12s3.3-6 9.5-6 9.5 6 9.5 6-3.3 6-9.5 6-9.5-6-9.5-6Z" />
                <circle cx="12" cy="12" r="2.7" />
              </svg>
              <svg v-else viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="m3 3 18 18M10.6 6.2A10.8 10.8 0 0 1 12 6c6.2 0 9.5 6 9.5 6a16 16 0 0 1-3 3.7M6.2 6.8C3.8 8.4 2.5 12 2.5 12s3.3 6 9.5 6c1.4 0 2.6-.3 3.7-.8" />
                <path d="M9.9 9.9a3 3 0 0 0 4.2 4.2" />
              </svg>
            </button>
          </div>
          <p v-if="authError" class="inline-error" role="alert">{{ tr(authError) }}</p>
          <button class="button button-primary full-button" type="submit" :disabled="busy">
            {{ busy ? tr('요청 중…') : props.mode === 'login' ? tr('로그인') : tr('회원가입') }}
          </button>
        </form>
        <RouterLink class="switch-auth" :to="{ name: props.mode === 'login' ? 'signup' : 'login' }">
          {{ props.mode === 'login' ? tr('계정이 없으신가요? 회원가입') : tr('이미 계정이 있나요? 로그인') }}
        </RouterLink>
      </template>
    </section>
  </main>
</template>
