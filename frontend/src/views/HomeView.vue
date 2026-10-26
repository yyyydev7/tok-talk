<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { tr, uiLanguage } from '../stores/uiSettings'

const message = computed(() => tr(
  '톡,talk은 연구자가 물질명 또는 상황 중심의 질문을 입력하면, 공식 안전자료에서 관련 근거를 검색하고 이해하기 쉬운 답변과 출처를 제공합니다.',
  'Tok,talk helps researchers ask about a chemical or situation, searches official safety resources for relevant evidence, and provides clear answers with sources.',
))
const graphemes = computed(() => Array.from(message.value))
const visibleText = ref('')
let timer: number | undefined

function startTyping() {
  if (timer !== undefined) window.clearInterval(timer)
  visibleText.value = ''
  let index = 0
  const typingDuration = 2400
  const characterDelay = typingDuration / graphemes.value.length
  timer = window.setInterval(() => {
    index += 1
    visibleText.value = graphemes.value.slice(0, index).join('')
    if (index >= graphemes.value.length && timer !== undefined) {
      window.clearInterval(timer)
      timer = undefined
    }
  }, characterDelay)
}

onMounted(startTyping)
watch(uiLanguage, startTyping)
onUnmounted(() => { if (timer !== undefined) window.clearInterval(timer) })
</script>

<template>
  <main class="home-landing">
    <section class="home-content">
      <div class="home-brand-lockup">
        <h1 class="home-brand-name">톡,talk</h1>
      </div>
      <p class="home-service-name">{{ tr('연구실 화학물질 안전정보 도우미', 'Laboratory Chemical Safety Information Assistant') }}</p>
      <p class="home-typewriter" aria-live="polite">{{ visibleText }}<span class="typing-caret" aria-hidden="true"></span></p>
    </section>
  </main>
</template>
