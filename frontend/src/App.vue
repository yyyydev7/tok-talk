<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { authState, logout, username } from './stores/tokTalk'
import { toggleLanguage, toggleTheme, tr, uiLanguage, uiTheme } from './stores/uiSettings'

const route = useRoute()
const router = useRouter()
const hasAuthBackground = computed(() => route.name === 'home' || route.name === 'login' || route.name === 'signup')
const siteMapOpen = ref(false)
const homeRoute = { name: 'home' }

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
      <div class="header-main">
        <RouterLink class="brand" :to="homeRoute" :aria-label="tr('홈', 'Home')"><span class="brand-logo-window"><img class="brand-logo" src="/media/tok-talk-brand-mark.png?v=3" alt="" /></span><span class="brand-name">톡,talk</span></RouterLink>
        <div class="header-utility">
          <RouterLink class="home-icon-link" :to="homeRoute" :aria-label="tr('홈으로 이동', 'Go home')" :title="tr('홈', 'Home')"><img src="/media/home-icon.png" alt="" /></RouterLink>
          <RouterLink class="header-utility-button" :to="{ name: 'question' }" :aria-label="tr('질문', 'Ask')" @click="siteMapOpen = false">{{ tr('질문', 'Ask') }}</RouterLink>
          <div class="sitemap-wrap">
            <button class="header-utility-button" type="button" :aria-expanded="siteMapOpen" @click="siteMapOpen = !siteMapOpen">{{ tr('사이트맵', 'Sitemap') }}</button>
          </div>
          <button class="header-utility-button language-toggle" type="button" :aria-label="uiLanguage === 'ko' ? 'Switch to English' : '한국어로 전환'" @click="toggleLanguage">{{ uiLanguage === 'ko' ? 'EN' : 'KO' }}</button>
          <button class="theme-toggle" type="button" :aria-label="uiTheme === 'light' ? tr('다크 모드로 전환', 'Switch to dark mode') : tr('라이트 모드로 전환', 'Switch to light mode')" :title="uiTheme === 'light' ? tr('다크 모드', 'Dark mode') : tr('라이트 모드', 'Light mode')" @click="toggleTheme">
            <svg v-if="uiTheme === 'light'" class="theme-sun" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4" /><path d="M12 2v2m0 16v2M4.93 4.93l1.42 1.42m11.3 11.3 1.42 1.42M2 12h2m16 0h2M4.93 19.07l1.42-1.42m11.3-11.3 1.42-1.42" /></svg>
            <svg v-else class="theme-moon" viewBox="0 0 24 24" aria-hidden="true"><path d="M20.4 15.1A8.7 8.7 0 0 1 8.9 3.6 8.8 8.8 0 1 0 20.4 15.1Z" /></svg>
          </button>
        <template v-if="authState === 'signed-in'">
          <span class="user-chip"><span class="avatar">{{ username.slice(0, 1) || '연' }}</span>{{ username || tr('로그인 사용자', 'Signed-in user') }}</span>
          <button class="text-button" type="button" @click="signOut">{{ tr('로그아웃', 'Sign out') }}</button>
        </template>
        <template v-else>
          <RouterLink class="header-auth-link" :to="{ name: 'login' }">{{ tr('로그인', 'Sign in') }}</RouterLink>
          <RouterLink class="header-signup-link" :to="{ name: 'signup' }">{{ tr('회원가입', 'Create account') }}</RouterLink>
        </template>
      </div>
      </div>
      <nav v-if="siteMapOpen" class="sitemap-menu" :aria-label="tr('사이트맵', 'Sitemap')" @keydown.esc="siteMapOpen = false">
        <div class="sitemap-group">
          <a href="https://msds.kosha.or.kr/MSDSInfo/kcic/msdssearchAll.do" target="_blank" rel="noopener noreferrer">KOSHA MSDS <span aria-hidden="true">↗</span></a>
          <a href="https://www.cdc.gov/niosh/npg/" target="_blank" rel="noopener noreferrer">NIOSH Pocket Guide <span aria-hidden="true">↗</span></a>
        </div>
      </nav>
    </header>

    <RouterView />

    <footer class="site-footer">
      <div class="footer-main">
        <div class="footer-brand-block">
          <RouterLink class="footer-brand" :to="homeRoute" :aria-label="tr('톡,talk 홈', 'Tok,talk home')">
            <img src="/media/tok-talk-brand-mark.png?v=3" alt="" />
            <span class="footer-brand-name">톡,talk</span>
          </RouterLink>
          <p>{{ tr('연구실 화학물질 안전정보 도우미', 'Laboratory Chemical Safety Information Assistant') }}</p>
          <small class="footer-copyright">© 2026 SKALA AI 서비스 개발 Mini-project</small>
        </div>

        <nav class="footer-column" :aria-label="tr('서비스 바로가기', 'Service links')">
          <h2>{{ tr('서비스', 'Services') }}</h2>
          <RouterLink :to="{ name: 'question' }">{{ tr('질문하기', 'Ask a question') }}</RouterLink>
          <RouterLink :to="{ name: 'materials' }">{{ tr('물질 검색', 'Search materials') }}</RouterLink>
        </nav>

        <nav id="footer-sources" class="footer-column" :aria-label="tr('참고 자료', 'References')">
          <h2>{{ tr('참고 자료', 'References') }}</h2>
          <a href="https://msds.kosha.or.kr/MSDSInfo/kcic/msdssearchMsds.do" target="_blank" rel="noopener noreferrer">KOSHA MSDS <span aria-hidden="true">↗</span></a>
          <a href="https://www.cdc.gov/niosh/npg/" target="_blank" rel="noopener noreferrer">NIOSH Pocket Guide <span aria-hidden="true">↗</span></a>
          <a href="#footer-sources">{{ tr('출처·자료 기준', 'Sources & data policy') }}</a>
        </nav>

        <div class="footer-column footer-guidance">
          <h2>{{ tr('이용 안내', 'About & help') }}</h2>
          <RouterLink :to="homeRoute">{{ tr('서비스 소개', 'About the service') }}</RouterLink>
          <a href="#footer-sources">{{ tr('데이터 출처', 'Data sources') }}</a>
          <a href="https://github.com/yyyydev7/tok-talk/issues" target="_blank" rel="noopener noreferrer">{{ tr('문의', 'Contact') }} <span aria-hidden="true">↗</span></a>
        </div>
      </div>
    </footer>
  </div>
</template>
