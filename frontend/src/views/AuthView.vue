<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { authError, authState, authenticate, checkAuth } from '../stores/tokTalk'

const props = defineProps<{ mode: 'login' | 'signup' }>()
const route = useRoute()
const router = useRouter()
const authUsername = ref('')
const password = ref('')
const busy = ref(false)
const title = computed(() => props.mode === 'login' ? '다시 오셨군요' : '계정 만들기')

watch(() => props.mode, () => { authError.value = '' })

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
    <section class="auth-intro">
      <p class="eyebrow">RESEARCH SAFETY, MADE CLEAR</p>
      <h1>시약을 확인하는 순간,<br /><em>근거가 곁에 있도록.</em></h1>
      <p class="intro-copy">NIOSH 참고 자료에서 필요한 정보를 찾고, 시연용 재고를 한 화면에서 확인합니다.</p>
      <div class="intro-note"><span class="note-icon">i</span><span>실제 취급 전에는 공급자가 제공한 제품별 MSDS와 담당자 확인을 따르세요.</span></div>
    </section>

    <section class="auth-card">
      <div class="card-kicker">SECURE ACCESS</div>
      <template v-if="authState === 'unavailable' || authState === 'checking'">
        <h2>{{ authState === 'checking' ? '인증 상태 확인 중' : '인증 서비스를 연결할 수 없습니다' }}</h2>
        <p class="muted">{{ authState === 'checking' ? '잠시만 기다려 주세요.' : 'Java 인증 서버 상태를 확인한 뒤 다시 시도해 주세요.' }}</p>
        <p v-if="authError" class="inline-error" role="status">{{ authError }}</p>
        <button class="button button-primary full-button" type="button" :disabled="authState === 'checking'" @click="retryAuth">다시 확인</button>
      </template>
      <template v-else>
        <h2>{{ title }}</h2>
        <p class="muted">{{ props.mode === 'login' ? '계정에 로그인해 안전정보를 확인하세요.' : '실습용 계정을 등록합니다.' }}</p>
        <p v-if="route.query.signup === 'complete'" class="success-message" role="status">가입이 완료됐습니다. 로그인해 주세요.</p>
        <form class="auth-form" @submit.prevent="submit">
          <label for="username">아이디</label>
          <input id="username" v-model="authUsername" autocomplete="username" placeholder="아이디 입력" required />
          <label for="password">비밀번호</label>
          <input id="password" v-model="password" :autocomplete="props.mode === 'login' ? 'current-password' : 'new-password'" type="password" minlength="8" maxlength="128" placeholder="비밀번호 입력" required />
          <p v-if="authError" class="inline-error" role="alert">{{ authError }}</p>
          <button class="button button-primary full-button" type="submit" :disabled="busy">
            {{ busy ? '요청 중…' : props.mode === 'login' ? '로그인' : '회원가입' }}
          </button>
        </form>
        <RouterLink class="switch-auth" :to="{ name: props.mode === 'login' ? 'signup' : 'login' }">
          {{ props.mode === 'login' ? '계정이 없으신가요? 회원가입' : '이미 계정이 있나요? 로그인' }}
        </RouterLink>
      </template>
      <div class="auth-footnote">로그인 후 질문·출처·시연용 재고 화면을 이용할 수 있습니다.</div>
    </section>
  </main>
</template>
