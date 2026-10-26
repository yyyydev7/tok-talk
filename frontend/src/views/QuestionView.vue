<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { answer, loadMaterials, materialQuery, materials, materialsBusy, materialsSearched, pageError, question, questionBusy, selectedMaterial, submitQuestion, transcribeAudio, username } from '../stores/tokTalk'
import type { Material, RagResponse } from '../stores/tokTalk'
import { tr, uiLanguage } from '../stores/uiSettings'

const router = useRouter()
type SearchRecord = { id: string; question: string; answer: RagResponse; createdAt: number }
const history = ref<SearchRecord[]>([])
const sidebarOpen = ref(false)
const materialPickerOpen = ref(false)
const activeRecordId = ref('')
const displayedAnswer = ref<RagResponse | null>(answer.value)
const displayedQuestion = ref(question.value)
const historyStorageKey = computed(() => `toktalk.search-history.v1.${username.value || 'user'}`)
const weekdayGreeting = computed(() => {
  const weekday = new Intl.DateTimeFormat(uiLanguage.value === 'ko' ? 'ko-KR' : 'en-US', { weekday: 'long', timeZone: 'Asia/Seoul' }).format(new Date())
  return uiLanguage.value === 'ko' ? `${username.value || '사용자'}님, 즐거운 ${weekday}이에요` : `Happy ${weekday}, ${username.value || 'there'}`
})
const recording = ref(false)
const transcribing = ref(false)
const voiceStatus = ref('')
const recordingSupported = typeof window !== 'undefined'
  && Boolean(navigator.mediaDevices?.getUserMedia)
  && typeof MediaRecorder !== 'undefined'
let recorder: MediaRecorder | null = null
let stream: MediaStream | null = null
let chunks: BlobPart[] = []
let disposed = false
const canAsk = computed(() => question.value.trim().length > 0 && !questionBusy.value && !transcribing.value)

async function ask(autoSpeak = false) {
  const submittedQuestion = question.value.trim()
  const result = await submitQuestion()
  if (!result) return false
  const record: SearchRecord = { id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`, question: submittedQuestion, answer: result, createdAt: Date.now() }
  history.value = [record, ...history.value.filter((item) => item.question !== submittedQuestion)].slice(0, 30)
  activeRecordId.value = record.id
  displayedQuestion.value = submittedQuestion
  displayedAnswer.value = result
  try { sessionStorage.setItem(historyStorageKey.value, JSON.stringify(history.value)) } catch { /* Browser storage is optional. */ }
  if (!autoSpeak) question.value = ''
  if (autoSpeak) await router.push({ name: 'answers', query: { speak: '1' } })
  return true
}

function openRecord(record: SearchRecord) {
  activeRecordId.value = record.id
  question.value = record.question
  displayedQuestion.value = record.question
  displayedAnswer.value = record.answer
  answer.value = record.answer
  selectedMaterial.value = record.answer.material
  sidebarOpen.value = false
  pageError.value = ''
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function newQuestion() {
  activeRecordId.value = ''
  question.value = ''
  displayedQuestion.value = ''
  displayedAnswer.value = null
  answer.value = null
  selectedMaterial.value = null
  pageError.value = ''
  sidebarOpen.value = false
  materialPickerOpen.value = false
}

async function toggleMaterialPicker() {
  materialPickerOpen.value = !materialPickerOpen.value
  if (materialPickerOpen.value && !materialsSearched.value && materials.value.length === 0) await loadMaterials()
}

function chooseMaterial(material: Material) {
  selectedMaterial.value = material
  materialPickerOpen.value = false
}

function formatDate(value: number) {
  return new Intl.DateTimeFormat(uiLanguage.value === 'ko' ? 'ko-KR' : 'en-US', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(value)
}

onMounted(() => {
  try {
    const saved = sessionStorage.getItem(historyStorageKey.value)
    if (saved) history.value = JSON.parse(saved) as SearchRecord[]
  } catch { sessionStorage.removeItem(historyStorageKey.value) }
  if (answer.value) displayedAnswer.value = answer.value
  if (question.value) displayedQuestion.value = question.value
})

function stopTracks() {
  stream?.getTracks().forEach((track) => track.stop())
  stream = null
}

function preferredMimeType() {
  for (const type of ['audio/webm;codecs=opus', 'audio/mp4', 'audio/webm']) {
    if (MediaRecorder.isTypeSupported(type)) return type
  }
  return ''
}

async function toggleRecording() {
  pageError.value = ''
  if (recording.value) {
    recorder?.stop()
    recording.value = false
    voiceStatus.value = tr('음성을 텍스트로 바꾸는 중…')
    return
  }
  if (!recordingSupported) {
    pageError.value = '이 브라우저는 음성 녹음을 지원하지 않습니다.'
    return
  }
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    const mimeType = preferredMimeType()
    recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream)
    chunks = []
    recorder.addEventListener('dataavailable', (event) => {
      if (event.data.size) chunks.push(event.data)
    })
    recorder.addEventListener('stop', async () => {
      const audio = new Blob(chunks, { type: recorder?.mimeType || 'audio/webm' })
      stopTracks()
      if (disposed || !audio.size) return
      transcribing.value = true
      try {
        question.value = await transcribeAudio(audio)
        voiceStatus.value = tr('질문을 확인했습니다. 답변을 만드는 중…')
        if (!await ask(true)) voiceStatus.value = ''
      } catch (error) {
        pageError.value = error instanceof Error ? error.message : '음성을 변환하지 못했습니다.'
        voiceStatus.value = ''
      } finally {
        transcribing.value = false
      }
    }, { once: true })
    recorder.start()
    recording.value = true
    voiceStatus.value = tr('녹음 중입니다. 완료되면 버튼을 다시 누르세요.')
  } catch {
    stopTracks()
    pageError.value = '마이크 권한을 확인한 뒤 다시 시도해 주세요.'
  }
}

onBeforeUnmount(() => {
  disposed = true
  if (recorder?.state === 'recording') recorder.stop()
  stopTracks()
})
</script>

<template>
  <main class="workspace conversation-workspace">
    <aside class="history-sidebar" :class="{ 'history-sidebar-open': sidebarOpen }" :aria-hidden="!sidebarOpen">
      <div class="history-sidebar-head"><strong>{{ tr('이전 질문', 'Recent questions') }}</strong><button type="button" :aria-label="tr('기록 닫기', 'Close history')" @click="sidebarOpen = false">×</button></div>
      <button class="history-new-button" type="button" @click="newQuestion"><span>＋</span>{{ tr('새 질문', 'New question') }}</button>
      <div v-if="history.length" class="history-list">
        <button v-for="record in history" :key="record.id" class="history-item" :class="{ active: activeRecordId === record.id }" type="button" @click="openRecord(record)">
          <span>{{ record.question }}</span><small>{{ formatDate(record.createdAt) }}</small>
        </button>
      </div>
      <p v-else class="history-empty">{{ tr('검색 기록이 여기에 표시됩니다.', 'Your searches will appear here.') }}</p>
    </aside>
    <button v-if="sidebarOpen" class="history-backdrop" type="button" :aria-label="tr('기록 닫기', 'Close history')" @click="sidebarOpen = false"></button>
    <section class="question-welcome" aria-label="톡talk">
      <div class="plan-wrap"><div class="plan-pill"><span>{{ tr('무료 플랜', 'Free plan') }}</span><span class="plan-divider">·</span><RouterLink :to="{ name: 'upgrade' }">{{ tr('업그레이드', 'Upgrade') }}</RouterLink></div></div>
      <div class="greeting-line"><img src="/media/tok-talk-brand-mark.png?v=3" alt="" /><h1>{{ weekdayGreeting }}</h1></div>
    </section>
    <section v-if="displayedAnswer" class="conversation-thread" aria-live="polite">
      <article class="conversation-question"><span class="conversation-avatar">{{ tr('나', 'You') }}</span><p>{{ displayedQuestion }}</p></article>
      <section v-if="displayedAnswer.resolution.status !== 'resolved'" class="resolution-card conversation-result">
        <div class="resolution-icon">?</div><div class="resolution-content"><strong>{{ displayedAnswer.resolution.status === 'ambiguous' ? tr('어떤 물질을 말씀하셨나요?') : tr('질문에서 물질을 찾지 못했습니다') }}</strong><p>{{ displayedAnswer.resolution.status === 'ambiguous' ? tr('질문에서 여러 물질이 확인되어 하나를 선택해야 합니다.') : tr('질문에 물질명을 포함하거나 물질 검색 화면에서 직접 선택해 주세요.') }}</p><div v-if="displayedAnswer.resolution.candidates.length" class="candidate-list"><button v-for="candidate in displayedAnswer.resolution.candidates" :key="candidate.material_id" type="button" class="candidate-button" @click="selectedMaterial = candidate; question = `${candidate.name}: ${displayedQuestion}`">{{ candidate.name }} <span>{{ tr('질문에 적용') }}</span></button></div><RouterLink v-else class="button button-soft inline-route-button" :to="{ name: 'materials' }">{{ tr('물질 검색·선택') }}</RouterLink></div>
      </section>
      <article v-else class="answer-card conversation-answer">
        <div class="answer-card-head"><span class="answer-icon">✳</span><h2>{{ tr('답변') }}</h2><span v-if="displayedAnswer.answer_mode === 'general'" class="review-tag">{{ tr('AI 일반 답변') }}</span><span v-else-if="displayedAnswer.needs_review" class="review-tag">{{ tr('담당자 확인 필요') }}</span><span v-else class="verified-tag">✓ {{ tr('근거 확인') }}</span></div>
        <p class="answer-text">{{ displayedAnswer.answer }}</p>
        <div v-if="displayedAnswer.answer_mode === 'general'" class="review-note"><span>i</span>{{ tr('일반 AI 답변이며 검색 근거를 조회하지 않았습니다. 안전 관련 내용은 공식 자료와 담당자 확인이 필요합니다.') }}</div>
        <div v-if="displayedAnswer.needs_review" class="review-note"><span>i</span>{{ tr('제공된 자료에서 충분한 근거를 찾지 못했습니다. 실제 제품별 MSDS와 안전 담당자를 확인하세요.') }}</div>
        <div v-if="displayedAnswer.sources.length" class="source-list"><h3><span class="source-count">{{ displayedAnswer.sources.length }}</span>{{ tr('참고 근거') }}</h3><article v-for="(source, index) in displayedAnswer.sources" :key="`${source.title}-${source.section}-${index}`" class="source-item"><span class="source-index">{{ String(index + 1).padStart(2, '0') }}</span><div class="source-copy"><strong>{{ source.title || source.source_file || 'NIOSH Pocket Guide' }}</strong><span>{{ source.section || tr('관련 항목') }}<template v-if="source.pdf_page"> · PDF {{ source.pdf_page }}{{ tr('쪽') }}</template></span><small>CAS {{ source.cas_number || displayedAnswer.material?.cas_number || tr('확인 필요') }}</small></div><a v-if="source.url" class="source-link" :href="source.url" target="_blank" rel="noreferrer" :aria-label="`${source.title} ${tr('원문 열기')}`">↗</a></article></div>
        <p v-else-if="displayedAnswer.answer_mode !== 'general'" class="source-empty">{{ tr('표시할 근거 자료가 없습니다.') }}</p>
      </article>
    </section>

    <section class="query-card conversation-composer" :aria-label="tr('질문 입력', 'Ask a question')">
      <div v-if="selectedMaterial" class="selected-pill"><span class="tiny-check">✓</span>{{ selectedMaterial.name }}<span>CAS {{ selectedMaterial.cas_number || tr('정보 없음') }}</span><button type="button" :aria-label="tr('선택 해제')" @click="selectedMaterial = null">×</button></div>
      <form class="question-form" @submit.prevent="ask()">
        <div class="question-input-wrap">
          <div v-if="!question" class="question-input-hint" aria-hidden="true"><span class="hint-search-icon">⌕</span>{{ tr('버튼을 눌러 물질을 선택하여 질문을 입력하거나,', 'to select a substance and type a question, or') }} <svg viewBox="0 0 24 24" fill="none"><rect x="9" y="2.5" width="6" height="12" rx="3" /><path d="M5.5 11.5a6.5 6.5 0 0 0 13 0M12 18v3.5m-4 0h8" /></svg>{{ tr('를 눌러 음성으로 질문해보세요.', 'to ask by voice.') }}</div>
          <textarea id="question" v-model="question" rows="3" :aria-label="selectedMaterial ? tr('선택한 물질에 대해 질문') : tr('질문')" :placeholder="selectedMaterial ? tr('예: 보호구 권고는 무엇인가요?') : ''" @keydown.meta.enter.prevent="ask()" @keydown.ctrl.enter.prevent="ask()"></textarea>
        </div>
        <div class="form-bottom"><div class="question-actions"><button class="history-toggle history-icon-button" type="button" :aria-expanded="sidebarOpen" :aria-label="tr('검색 기록', 'Search history')" :title="tr('검색 기록', 'Search history')" @click="sidebarOpen = !sidebarOpen"><span aria-hidden="true">☰</span></button><button class="button button-soft material-route-button material-icon-button" :class="{ 'picker-active': materialPickerOpen }" type="button" :aria-expanded="materialPickerOpen" :aria-label="materialPickerOpen ? tr('물질 검색 닫기') : selectedMaterial ? tr('물질 바꾸기') : tr('물질 검색·선택')" :title="materialPickerOpen ? tr('물질 검색 닫기') : selectedMaterial ? tr('물질 바꾸기') : tr('물질 검색·선택')" @click="toggleMaterialPicker"><span aria-hidden="true">⌕</span></button></div><div class="ask-actions"><button v-if="recordingSupported" class="voice-button" :class="{ recording }" type="button" :disabled="transcribing || questionBusy" :aria-pressed="recording" :aria-label="recording ? tr('녹음 완료') : tr('음성으로 질문')" @click="toggleRecording"><svg v-if="!recording" viewBox="0 0 24 24" fill="none" aria-hidden="true"><rect x="9" y="2.5" width="6" height="12" rx="3" /><path d="M5.5 11.5a6.5 6.5 0 0 0 13 0M12 18v3.5m-4 0h8" /></svg><svg v-else viewBox="0 0 24 24" fill="none" aria-hidden="true"><rect x="7" y="7" width="10" height="10" rx="2" /></svg></button><button class="button button-primary ask-button" type="submit" :disabled="!canAsk">{{ questionBusy ? tr('근거를 찾는 중…') : tr('질문하기') }}</button><span v-if="voiceStatus" class="voice-status" aria-live="polite">{{ voiceStatus }}</span></div></div>
        <section v-if="materialPickerOpen" class="inline-material-picker" :aria-label="tr('물질 검색·선택')">
          <form class="material-search-form" @submit.prevent="loadMaterials">
            <div class="picker-row"><input v-model="materialQuery" :aria-label="tr('물질명 또는 동의어')" :placeholder="tr('예: 아세톤, ethanol')" /><button class="button button-primary search-button" type="submit" :disabled="materialsBusy">{{ materialsBusy ? tr('찾는 중…') : tr('검색') }}</button></div>
          </form>
          <div v-if="pageError" class="error-banner" role="alert"><span>!</span>{{ tr(pageError) }}</div>
          <div v-if="materials.length" class="inline-material-list"><button v-for="material in materials" :key="material.material_id" type="button" class="inline-material-option" @click="chooseMaterial(material)"><span class="chemical-symbol">{{ material.name.slice(0, 1) }}</span><span class="material-details"><strong>{{ material.name }}</strong><small>CAS {{ material.cas_number || tr('정보 없음') }}</small></span><span class="option-arrow">{{ tr('선택') }} →</span></button></div>
          <p v-else-if="materialsSearched && !materialsBusy && !pageError" class="inline-material-empty">{{ tr('일치하는 물질이 없습니다. 이름이나 동의어를 바꿔 검색해 주세요.') }}</p>
          <p v-else-if="materialsBusy" class="inline-material-empty">{{ tr('물질 목록을 불러오고 있습니다…') }}</p>
        </section>
      </form>
      <div v-if="pageError && !materialPickerOpen" class="error-banner" role="alert"><span>!</span>{{ tr(pageError) }}</div>
    </section>

  </main>
</template>
