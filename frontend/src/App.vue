<script setup lang="ts">
import { computed, watch } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { authState, logout, username } from './stores/tokTalk'

const route = useRoute()
const router = useRouter()
const hasAuthBackground = computed(() => route.name === 'login' || route.name === 'signup')

watch(authState, (state) => {
  if (state === 'signed-out' && route.meta.requiresAuth) {
    void router.replace({ name: 'login', query: { reason: 'expired', redirect: route.fullPath } })
  }
})

async function signOut() {
  try {
    await logout()
  } finally {
    await router.replace({ name: 'login' })
  }
}
</script>

<template>
  <div class="app-shell" :class="{ 'has-auth-background': hasAuthBackground }">
    <div v-if="hasAuthBackground" class="auth-backdrop" aria-hidden="true">
      <video class="auth-backdrop-video" autoplay muted loop playsinline preload="metadata" poster="/media/lab-pour-poster.jpg">
        <source src="/media/lab-pour-background.mp4" type="video/mp4" />
      </video>
      <div class="auth-backdrop-scrim"></div>
    </div>

    <header class="topbar">
      <RouterLink class="brand" :to="{ name: 'question' }" aria-label="톡talk 홈"><span class="brand-mark">t</span><span>톡,talk</span></RouterLink>
      <nav v-if="authState === 'signed-in'" class="app-navigation" aria-label="주요 메뉴">
        <RouterLink :to="{ name: 'question' }" exact-active-class="active">질문</RouterLink>
        <RouterLink :to="{ name: 'materials' }" exact-active-class="active">물질 검색</RouterLink>
        <RouterLink v-if="route.name === 'answers' || route.name === 'inventory'" :to="{ name: 'answers' }" exact-active-class="active">답변·출처</RouterLink>
      </nav>
      <div class="topbar-right">
        <span class="service-label"><span class="live-dot"></span> 시약 안전정보 탐색</span>
        <template v-if="authState === 'signed-in'">
          <span class="user-chip"><span class="avatar">{{ username.slice(0, 1) || '연' }}</span>{{ username || '로그인 사용자' }}</span>
          <button class="text-button" type="button" @click="signOut">로그아웃</button>
        </template>
      </div>
    </header>

    <RouterView />

    <footer class="footer"><span>톡,talk <span class="footer-separator">·</span> 근거를 확인하는 안전정보</span><span>NIOSH 일반 참고정보 <span class="footer-separator">·</span> 제품별 MSDS 대체 불가</span></footer>
  </div>
</template>
