<script setup lang="ts">
import { ref } from 'vue'
import { tr } from '../stores/uiSettings'

const selectedPlan = ref<'demo' | 'lab' | 'institution'>('demo')
</script>

<template>
  <main class="workspace upgrade-workspace">
    <section class="upgrade-intro">
      <p class="upgrade-kicker">{{ tr('연구실과 함께 성장하는 플랜', 'Plans for laboratories') }}</p>
      <h1>{{ tr('연구실 규모에 맞는 플랜을 선택하세요') }}</h1>
    </section>

    <section class="plan-cards" :aria-label="tr('플랜 목록')">
      <article class="plan-card" :class="{ 'plan-card-selected': selectedPlan === 'demo' }">
        <span v-if="selectedPlan === 'demo'" class="plan-badge">{{ tr('현재 플랜') }}</span>
        <h2>Demo</h2>
        <p class="plan-description">{{ tr('먼저 써보고 서비스 흐름을 확인하세요.') }}</p>
        <div class="plan-price">{{ tr('무료') }}</div>
        <p class="plan-price-note">{{ tr('시연 및 기능 검토용') }}</p>
        <button class="plan-cta plan-cta-current" type="button" :aria-pressed="selectedPlan === 'demo'" @click="selectedPlan = 'demo'">{{ selectedPlan === 'demo' ? tr('현재 플랜') : tr('플랜 선택') }}</button>
        <div class="plan-features">
          <ul><li>{{ tr('등록된 물질 질문·답변') }}</li><li>{{ tr('답변 근거와 출처 확인') }}</li><li>{{ tr('시연용 재고 확인') }}</li></ul>
        </div>
      </article>

      <article class="plan-card plan-card-featured" :class="{ 'plan-card-selected': selectedPlan === 'lab' }">
        <span class="plan-badge">{{ selectedPlan === 'lab' ? tr('선택한 플랜') : tr('연구실 추천') }}</span>
        <h2>Lab</h2>
        <p class="plan-description">{{ tr('한 연구실의 안전정보와 재고를 함께 관리') }}</p>
        <div class="plan-price plan-price-contact">{{ tr('도입 상담') }}</div>
        <p class="plan-price-note">{{ tr('사용 인원과 운영 범위에 맞춰 안내') }}</p>
        <button class="plan-cta plan-cta-primary" type="button" :aria-pressed="selectedPlan === 'lab'" @click="selectedPlan = 'lab'">{{ selectedPlan === 'lab' ? tr('선택한 플랜') : tr('연구실 도입 상담') }}</button>
        <div class="plan-features">
          <ul><li>{{ tr('실제 연구실 재고·보관 위치 관리') }}</li><li>{{ tr('사용자별 권한과 연구실 공유') }}</li><li>{{ tr('재고 부족 알림과 변경 이력') }}</li></ul>
        </div>
      </article>

      <article class="plan-card" :class="{ 'plan-card-selected': selectedPlan === 'institution' }">
        <span v-if="selectedPlan === 'institution'" class="plan-badge">{{ tr('선택한 플랜') }}</span>
        <h2>Institution</h2>
        <p class="plan-description">{{ tr('여러 연구실과 기관 운영을 통합') }}</p>
        <div class="plan-price plan-price-contact">{{ tr('별도 협의') }}</div>
        <p class="plan-price-note">{{ tr('보안·연동·운영 요구사항에 따라 협의') }}</p>
        <button class="plan-cta plan-cta-dark" type="button" :aria-pressed="selectedPlan === 'institution'" @click="selectedPlan = 'institution'">{{ selectedPlan === 'institution' ? tr('선택한 플랜') : tr('기관 도입 문의') }}</button>
        <div class="plan-features">
          <ul><li>{{ tr('여러 연구실 통합 현황') }}</li><li>{{ tr('기관별 접근 권한·감사 기록') }}</li><li>{{ tr('내부 시스템·전용 자료 연동') }}</li></ul>
        </div>
      </article>
    </section>

  </main>
</template>
