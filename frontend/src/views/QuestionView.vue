<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { pageError, question, questionBusy, selectedMaterial, submitQuestion } from '../stores/tokTalk'

const router = useRouter()
const canAsk = computed(() => question.value.trim().length > 0 && !questionBusy.value)

async function ask() {
  const result = await submitQuestion()
  if (result) await router.push({ name: 'answers' })
}
</script>

<template>
  <main class="workspace">
    <section class="welcome-row">
      <div>
        <h1>어떤 시약을 확인할까요?</h1>
        <p class="welcome-copy">질문에 물질명을 적거나, 물질을 먼저 검색해 선택하세요.</p>
      </div>
      <div class="welcome-badge"><span class="badge-icon">✳</span><span>근거 중심<br /><strong>안전정보 탐색</strong></span></div>
    </section>

    <section class="query-card" aria-labelledby="query-title">
      <div class="query-heading">
        <div><span class="step-number">01</span><h2 id="query-title">질문 입력</h2></div>
        <span class="private-label"><span class="lock-icon">●</span> 인증된 사용자</span>
      </div>
      <div v-if="selectedMaterial" class="selected-pill"><span class="tiny-check">✓</span>{{ selectedMaterial.name }}<span>CAS {{ selectedMaterial.cas_number || '정보 없음' }}</span><button type="button" aria-label="선택 해제" @click="selectedMaterial = null">×</button></div>
      <form class="question-form" @submit.prevent="ask">
        <label for="question">{{ selectedMaterial ? '선택한 물질에 대해 질문' : '질문' }}</label>
        <textarea id="question" v-model="question" rows="4" :placeholder="selectedMaterial ? '예: 보호구 권고는 무엇인가요?' : '예: 아세톤의 노출 경로와 주요 증상은 무엇인가요?'" @keydown.meta.enter.prevent="ask" @keydown.ctrl.enter.prevent="ask"></textarea>
        <div class="form-bottom">
          <div class="question-actions">
            <RouterLink class="button button-soft material-route-button" :to="{ name: 'materials' }">{{ selectedMaterial ? '물질 바꾸기' : '물질 검색·선택' }} <span>⌕</span></RouterLink>
            <span class="helper-text">물질명이 여러 개면 답변 전에 선택을 요청합니다.</span>
          </div>
          <button class="button button-primary ask-button" type="submit" :disabled="!canAsk">{{ questionBusy ? '근거를 찾는 중…' : '질문하기' }} <span>↗</span></button>
        </div>
      </form>
      <div v-if="pageError" class="error-banner" role="alert"><span>!</span>{{ pageError }}</div>
    </section>

    <section class="guidance-row">
      <div class="guidance-card"><span class="guidance-icon">⌕</span><div><strong>근거가 있는 답변</strong><p>답변과 함께 원문 출처·항목·확인일을 확인합니다.</p></div></div>
      <div class="guidance-card"><span class="guidance-icon inventory-guidance">▤</span><div><strong>별도 재고 화면</strong><p>시연용 수량과 위치를 안전정보와 구분해 보여줍니다.</p></div></div>
    </section>
  </main>
</template>
