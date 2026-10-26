<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { answer, pageError, question, questionBusy, selectedMaterial, submitQuestion } from '../stores/tokTalk'
import type { Material } from '../stores/tokTalk'

const router = useRouter()
const activeMaterial = computed(() => answer.value?.material ?? selectedMaterial.value)

function formatDate(value?: string) {
  if (!value) return '확인일 정보 없음'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat('ko-KR').format(date)
}

async function askForCandidate(candidate: Material) {
  selectedMaterial.value = candidate
  await submitQuestion(candidate)
}

onMounted(() => {
  if (!answer.value) void router.replace({ name: 'question' })
})
</script>

<template>
  <main v-if="answer" class="workspace route-workspace">
    <div class="route-heading answer-route-heading">
      <div>
        <RouterLink class="back-link" :to="{ name: 'question' }">← 질문 화면</RouterLink>
        <h1>질문 결과</h1>
        <p class="welcome-copy route-question">“{{ question }}”</p>
      </div>
      <span v-if="activeMaterial" class="result-material">{{ activeMaterial.name }} <small>CAS {{ activeMaterial.cas_number || '정보 없음' }}</small></span>
    </div>

    <section v-if="answer.resolution.status === 'not_found'" class="resolution-card route-resolution">
      <div class="resolution-icon">?</div>
      <div class="resolution-content"><strong>질문에서 물질을 찾지 못했습니다</strong><p>질문에 물질명을 포함하거나 물질 검색 화면에서 직접 선택해 주세요.</p><RouterLink class="button button-soft inline-route-button" :to="{ name: 'materials' }">물질 검색·선택 <span>→</span></RouterLink></div>
    </section>

    <section v-else-if="answer.resolution.status === 'ambiguous'" class="resolution-card route-resolution">
      <div class="resolution-icon">?</div><div class="resolution-content"><strong>어떤 물질을 말씀하셨나요?</strong><p>질문에서 여러 물질이 확인되어 하나를 선택해야 합니다.</p><div class="candidate-list"><button v-for="candidate in answer.resolution.candidates" :key="candidate.material_id" type="button" class="candidate-button" :disabled="questionBusy" @click="askForCandidate(candidate)">{{ candidate.name }} <span>{{ questionBusy ? '검색 중…' : '이 물질로 다시 검색 →' }}</span></button></div></div>
    </section>

    <section v-else class="answer-route-grid">
      <article class="answer-card">
        <div class="answer-card-head"><span class="answer-icon">✳</span><div><h2>답변</h2></div><span v-if="answer.needs_review" class="review-tag">담당자 확인 필요</span><span v-else class="verified-tag"><span>✓</span> 근거 확인</span></div>
        <p class="answer-text">{{ answer.answer }}</p>
        <div v-if="answer.needs_review" class="review-note"><span>i</span> 제공된 자료에서 충분한 근거를 찾지 못했습니다. 실제 제품별 MSDS와 안전 담당자를 확인하세요.</div>
        <div v-if="answer.sources.length" class="source-list">
          <h3><span class="source-count">{{ answer.sources.length }}</span> 참고 근거</h3>
          <article v-for="(source, index) in answer.sources" :key="`${source.title}-${source.section}-${index}`" class="source-item">
            <span class="source-index">{{ String(index + 1).padStart(2, '0') }}</span>
            <div class="source-copy"><strong>{{ source.title || source.source_file || 'NIOSH Pocket Guide' }}</strong><span>{{ source.section || '관련 항목' }}<template v-if="source.pdf_page"> · PDF {{ source.pdf_page }}쪽</template></span><small>CAS {{ source.cas_number || activeMaterial?.cas_number || '확인 필요' }} · 확인일 {{ formatDate(source.checked_at) }}</small></div>
            <a v-if="source.url" class="source-link" :href="source.url" target="_blank" rel="noreferrer" :aria-label="`${source.title} 원문 열기`">↗</a>
          </article>
        </div>
        <p v-else class="source-empty">표시할 근거 자료가 없습니다.</p>
      </article>
      <aside class="answer-side-card">
        <span class="step-number">02</span><h2>다음으로</h2>
        <p>시연 재고는 안전정보 답변과 분리해 확인합니다.</p>
        <RouterLink v-if="activeMaterial" class="button button-soft full-button route-button" :to="{ name: 'inventory', params: { materialId: activeMaterial.material_id }, query: { name: activeMaterial.name, cas: activeMaterial.cas_number } }">시연 재고 확인 <span>→</span></RouterLink>
        <RouterLink class="button button-primary full-button route-button" :to="{ name: 'question' }">새 질문하기</RouterLink>
      </aside>
    </section>
    <p class="safety-disclaimer">NIOSH Pocket Guide는 일반 참고자료입니다. 실제 취급은 공급자가 제공한 제품별 MSDS와 안전 담당자의 확인을 따르세요.</p>
  </main>
  <main v-else class="workspace route-workspace">
    <div class="route-heading"><div><h1>답변을 불러오지 못했습니다</h1><p class="welcome-copy">질문을 다시 제출하거나 잠시 후 재시도해 주세요.</p></div></div>
    <div v-if="pageError" class="error-banner" role="alert"><span>!</span>{{ pageError }}</div>
    <div v-else class="route-loading"><span class="spinner" aria-hidden="true"></span><span>답변을 준비하고 있습니다</span></div>
    <RouterLink class="button button-primary inline-route-button" :to="{ name: 'question' }">질문 화면으로 이동</RouterLink>
  </main>
</template>
