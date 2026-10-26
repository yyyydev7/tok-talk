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
      <RouterLink class="brand" :to="{ name: 'question' }" aria-label="톡,talk 홈"><span class="brand-logo-window"><img class="brand-logo" src="/media/tok-talk-brand-mark.png?v=3" alt="" /></span><span>톡,talk</span></RouterLink>
      <nav v-if="authState === 'signed-in'" class="app-navigation" aria-label="주요 메뉴">
        <RouterLink :to="{ name: 'question' }" exact-active-class="active">질문</RouterLink>
        <RouterLink :to="{ name: 'materials' }" exact-active-class="active">물질 검색</RouterLink>
        <RouterLink v-if="route.name === 'answers' || route.name === 'inventory'" :to="{ name: 'answers' }" exact-active-class="active">답변·출처</RouterLink>
      </nav>
      <div class="topbar-right">
        <template v-if="authState === 'signed-in'">
          <span class="user-chip"><span class="avatar">{{ username.slice(0, 1) || '연' }}</span>{{ username || '로그인 사용자' }}</span>
          <button class="text-button" type="button" @click="signOut">로그아웃</button>
        </template>
      </div>
    </header>

    <RouterView />

    <footer class="site-footer">
      <div class="footer-main">
        <div class="footer-brand-block">
          <RouterLink class="footer-brand" :to="{ name: 'question' }" aria-label="톡,talk 홈">
            <img src="/media/tok-talk-brand-mark.png?v=3" alt="" />
            <span>톡,talk</span>
          </RouterLink>
          <p>근거를 확인하는 안전정보</p>
        </div>

        <nav class="footer-column" aria-label="서비스 바로가기">
          <h2>서비스</h2>
          <RouterLink :to="{ name: 'question' }">질문하기</RouterLink>
          <RouterLink :to="{ name: 'materials' }">물질 검색</RouterLink>
          <RouterLink :to="{ name: 'materials' }">시연용 재고</RouterLink>
        </nav>

        <nav id="footer-sources" class="footer-column" aria-label="참고 자료">
          <h2>참고 자료</h2>
          <a href="https://msds.kosha.or.kr/MSDSInfo/kcic/msdssearchMsds.do" target="_blank" rel="noopener noreferrer">KOSHA MSDS <span aria-hidden="true">↗</span></a>
          <a href="https://www.cdc.gov/niosh/npg/" target="_blank" rel="noopener noreferrer">NIOSH Pocket Guide <span aria-hidden="true">↗</span></a>
          <a href="#footer-sources">출처·자료 기준</a>
        </nav>

        <div class="footer-column footer-guidance">
          <h2>이용 안내</h2>
          <RouterLink :to="{ name: 'question' }">서비스 소개</RouterLink>
          <a href="#footer-sources">데이터 출처</a>
          <a href="https://github.com/yyyydev7/tok-talk/issues" target="_blank" rel="noopener noreferrer">문의 <span aria-hidden="true">↗</span></a>
        </div>
      </div>
      <div class="footer-bottom"><span>© 2026 톡,talk Mini Project</span></div>
    </footer>
  </div>
</template>
