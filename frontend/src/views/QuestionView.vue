<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { useRouter } from 'vue-router'
import { pageError, question, questionBusy, submitQuestion, transcribeAudio } from '../stores/tokTalk'

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

async function ask(autoSpeak = false) {
  const result = await submitQuestion()
  if (!result) return false
  await router.push({
      name: 'answers',
      query: autoSpeak ? { speak: '1' } : undefined,
    })
  return true
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
        voiceStatus.value = '질문을 확인했습니다. 답변을 만드는 중…'
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
        <h1>무엇이 궁금하신가요?</h1>
        <p class="welcome-copy">질문을 입력하거나 마이크로 말하면 답변을 받아 음성으로 읽어드립니다.</p>
      </div>
      <div class="welcome-badge"><span class="badge-icon">✳</span><span>말하고 듣는<br /><strong>AI 음성 대화</strong></span></div>
    </section>

    <section class="query-card" aria-labelledby="query-title">
      <div class="query-heading">
        <div><span class="step-number">01</span><h2 id="query-title">질문 입력</h2></div>
        <span class="private-label"><span class="lock-icon">●</span> 인증된 사용자</span>
      </div>
      <form class="question-form" @submit.prevent="ask(true)">
        <label for="question">질문</label>
        <textarea id="question" v-model="question" rows="4" placeholder="궁금한 내용을 입력하거나 음성으로 질문하세요." @keydown.meta.enter.prevent="ask(true)" @keydown.ctrl.enter.prevent="ask(true)"></textarea>
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
            <span class="helper-text">음성 질문은 변환이 끝나면 자동으로 답변을 요청합니다.</span>
          </div>
          <button class="button button-primary ask-button" type="submit" :disabled="!canAsk">{{ questionBusy ? '근거를 찾는 중…' : '질문하기' }} <span>↗</span></button>
        </div>
      </form>
      <div v-if="pageError" class="error-banner" role="alert"><span>!</span>{{ pageError }}</div>
    </section>

    <section class="guidance-row">
      <div class="guidance-card"><span class="guidance-icon">⌕</span><div><strong>말하면 바로 질문</strong><p>녹음한 음성을 텍스트로 바꾸고 AI에 질문합니다.</p></div></div>
      <div class="guidance-card"><span class="guidance-icon inventory-guidance">▶</span><div><strong>답변을 음성으로</strong><p>생성된 답변을 화면에 표시하고 자연스럽게 읽어드립니다.</p></div></div>
    </section>
  </main>
</template>
