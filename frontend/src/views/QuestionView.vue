<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { useRouter } from 'vue-router'
import { pageError, question, questionBusy, selectedMaterial, submitQuestion, transcribeAudio } from '../stores/tokTalk'

const router = useRouter()
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

async function ask() {
  const result = await submitQuestion()
  if (result) await router.push({ name: 'answers' })
}

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
    voiceStatus.value = '음성을 텍스트로 바꾸는 중…'
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
        voiceStatus.value = '음성을 질문으로 입력했습니다.'
      } catch (error) {
        pageError.value = error instanceof Error ? error.message : '음성을 변환하지 못했습니다.'
        voiceStatus.value = ''
      } finally {
        transcribing.value = false
      }
    }, { once: true })
    recorder.start()
    recording.value = true
    voiceStatus.value = '녹음 중입니다. 완료되면 버튼을 다시 누르세요.'
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
        <div class="voice-input-row">
          <button
            class="voice-button"
            :class="{ recording }"
            type="button"
            :disabled="transcribing || questionBusy"
            :aria-pressed="recording"
            @click="toggleRecording"
          >
            <span aria-hidden="true">{{ recording ? '■' : '●' }}</span>
            {{ recording ? '녹음 완료' : transcribing ? '변환 중…' : '음성으로 질문' }}
          </button>
          <span v-if="voiceStatus" class="voice-status" aria-live="polite">{{ voiceStatus }}</span>
        </div>
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
