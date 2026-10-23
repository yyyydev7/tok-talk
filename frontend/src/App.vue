<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

type Material = {
  material_id: string
  name: string
  aliases?: string[]
  cas_number?: string
  source_title?: string
}

type Source = {
  cas_number?: string
  title?: string
  section?: string
  url?: string
  source_file?: string
  pdf_page?: string
  checked_at?: string
}

type RagResponse = {
  answer: string
  sources: Source[]
  needs_review: boolean
  material: Material | null
  resolution: {
    status: 'resolved' | 'ambiguous' | 'not_found'
    candidates: Material[]
  }
}

type InventoryItem = {
  item_id: string
  display_name: string
  quantity: number
  unit: string
  location: string
  updated_at: string
}

type InventoryResponse = {
  material_id: string
  is_demo: boolean
  items: InventoryItem[]
}

type AuthResponse = {
  ok?: boolean
  username?: string
  via?: 'jwt' | 'session'
  error?: string
  reason?: string
  redirect?: string
}

const authBase = (import.meta.env.VITE_AUTH_BASE_URL ?? 'http://localhost:8080').replace(/\/$/, '')
const ragBase = (import.meta.env.VITE_RAG_BASE_URL ?? 'http://localhost:8001').replace(/\/$/, '')

const authState = ref<'checking' | 'signed-out' | 'signed-in' | 'unavailable'>('checking')
const username = ref('')
const authMode = ref<'login' | 'signup'>('login')
const authUsername = ref('')
const authPassword = ref('')
const authBusy = ref(false)
const authError = ref('')

const flow = ref<'ask' | 'choose'>('ask')
const question = ref('')
const materialQuery = ref('')
const materials = ref<Material[]>([])
const materialsSearched = ref(false)
const selectedMaterial = ref<Material | null>(null)
const answer = ref<RagResponse | null>(null)
const inventory = ref<InventoryResponse | null>(null)
const inventoryError = ref('')
const busy = ref(false)
const materialsBusy = ref(false)
const pageError = ref('')

const activeMaterial = computed(() => answer.value?.material ?? selectedMaterial.value)
const canAsk = computed(() => question.value.trim().length > 0 && !busy.value)

async function request<T>(base: string, path: string, init: RequestInit = {}): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${base}${path}`, { ...init, credentials: 'include' })
  } catch {
    throw new Error('서비스에 연결할 수 없습니다. 서버 상태를 확인한 뒤 다시 시도해 주세요.')
  }
  if (response.status === 401) {
    const wasSignedIn = authState.value === 'signed-in'
    authState.value = 'signed-out'
    username.value = ''
    if (wasSignedIn) clearResult()
    const message = wasSignedIn
      ? '로그인 시간이 끝났습니다. 다시 로그인해 주세요.'
      : path === '/api/login'
        ? '아이디 또는 비밀번호를 확인해 주세요.'
        : '로그인이 필요합니다. 로그인한 뒤 다시 이용해 주세요.'
    if (wasSignedIn) authError.value = message
    throw new Error(message)
  }
  if (!response.ok) {
    const message = response.status === 422
      ? '입력 내용을 확인해 주세요.'
      : response.status === 503
        ? '서비스가 준비되지 않았거나 일시적으로 사용할 수 없습니다. 잠시 후 다시 시도해 주세요.'
        : response.status >= 500
          ? '서비스 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.'
          : `요청을 처리하지 못했습니다. (${response.status})`
    throw new Error(message)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

async function checkAuth() {
  authState.value = 'checking'
  try {
    const result = await request<AuthResponse>(authBase, '/api/auth/check')
    if (result.ok) {
      authState.value = 'signed-in'
      username.value = result.username ?? ''
      authError.value = ''
      return
    }
    authState.value = 'signed-out'
  } catch (error) {
    if (authState.value !== 'signed-out') {
      authState.value = 'unavailable'
      authError.value = error instanceof Error ? error.message : '인증 서버에 연결할 수 없습니다.'
    }
  }
}

async function submitAuth() {
  authError.value = ''
  if (!authUsername.value.trim() || !authPassword.value) {
    authError.value = '아이디와 비밀번호를 입력해 주세요.'
    return
  }
  const normalizedUsername = authUsername.value.trim()
  if (!/^[A-Za-z0-9._-]{3,64}$/.test(normalizedUsername)) {
    authError.value = '아이디는 영문, 숫자, 마침표, 밑줄, 하이픈을 사용해 3~64자로 입력해 주세요.'
    return
  }
  if (authPassword.value.length < 8 || authPassword.value.length > 128) {
    authError.value = '비밀번호는 8~128자로 입력해 주세요.'
    return
  }
  authBusy.value = true
  try {
    const body = new URLSearchParams({ username: normalizedUsername, password: authPassword.value })
    if (authMode.value === 'signup') {
      const response = await fetch(`${authBase}/api/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        credentials: 'include',
        // The auth server currently responds with 302 after creating an account.
        // Keep the redirect from sending this API request to the browser's /login page.
        redirect: 'manual',
        body,
      })
      if (!response.ok && response.status !== 302 && response.type !== 'opaqueredirect') {
        if (response.status === 409) throw new Error('이미 사용 중인 아이디입니다. 다른 아이디를 선택해 주세요.')
        if (response.status === 400) throw new Error('아이디 또는 비밀번호 형식을 확인해 주세요.')
        throw new Error(`회원가입에 실패했습니다. (${response.status})`)
      }
      authMode.value = 'login'
      authPassword.value = ''
      authError.value = '가입 요청을 보냈습니다. 계정으로 로그인해 주세요.'
      return
    }
    const result = await request<AuthResponse>(authBase, '/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body,
    })
    if (!result.ok) throw new Error(result.error ?? '로그인에 실패했습니다.')
    authState.value = 'signed-in'
    username.value = normalizedUsername
    authPassword.value = ''
    authError.value = ''
  } catch (error) {
    authError.value = error instanceof Error ? error.message : '인증 요청을 완료하지 못했습니다.'
  } finally {
    authBusy.value = false
  }
}

async function logout() {
  pageError.value = ''
  try {
    // The contract redirects to /login after expiring the HttpOnly cookie,
    // so its final response may be HTML instead of JSON.
    await fetch(`${authBase}/api/logout`, { method: 'POST', credentials: 'include' })
  } catch (error) {
    pageError.value = error instanceof Error ? error.message : '로그아웃 요청을 완료하지 못했습니다.'
  }
  authState.value = 'signed-out'
  username.value = ''
  authError.value = ''
  clearResult()
}

async function loadMaterials() {
  materialsBusy.value = true
  pageError.value = ''
  try {
    const query = materialQuery.value.trim()
    const params = query ? `?query=${encodeURIComponent(query)}` : ''
    const result = await request<{ items: Material[] }>(ragBase, `/chemicals${params}`)
    materials.value = result.items
    materialsSearched.value = true
  } catch (error) {
    pageError.value = error instanceof Error ? error.message : '물질 목록을 불러오지 못했습니다.'
  } finally {
    materialsBusy.value = false
  }
}

function clearResult() {
  answer.value = null
  inventory.value = null
  inventoryError.value = ''
  pageError.value = ''
}

function setFlow(next: 'ask' | 'choose') {
  flow.value = next
  clearResult()
  if (next === 'choose' && materials.value.length === 0) void loadMaterials()
}

async function loadInventory(material: Material | null) {
  inventory.value = null
  inventoryError.value = ''
  if (!material) return
  try {
    inventory.value = await request<InventoryResponse>(
      ragBase,
      `/inventory?material_id=${encodeURIComponent(material.material_id)}`,
    )
  } catch (error) {
    inventoryError.value = error instanceof Error ? error.message : '재고 조회를 사용할 수 없습니다.'
  }
}

async function submitQuestion() {
  if (!canAsk.value) return
  busy.value = true
  clearResult()
  try {
    const result = flow.value === 'ask'
      ? await request<RagResponse>(ragBase, '/rag-query/auto', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question: question.value.trim(), top_k: 5 }),
        })
      : selectedMaterial.value
        ? await request<RagResponse>(ragBase, '/rag-query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              material_id: selectedMaterial.value.material_id,
              question: question.value.trim(),
              top_k: 5,
            }),
          })
        : null
    if (!result) {
      pageError.value = '먼저 물질을 선택해 주세요.'
      return
    }
    answer.value = result
    if (result.material) await loadInventory(result.material)
  } catch (error) {
    pageError.value = error instanceof Error ? error.message : '질문을 처리하지 못했습니다.'
  } finally {
    busy.value = false
  }
}

async function askForCandidate(candidate: Material) {
  selectedMaterial.value = candidate
  flow.value = 'choose'
  busy.value = true
  clearResult()
  try {
    answer.value = await request<RagResponse>(ragBase, '/rag-query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ material_id: candidate.material_id, question: question.value.trim(), top_k: 5 }),
    })
    await loadInventory(candidate)
  } catch (error) {
    pageError.value = error instanceof Error ? error.message : '선택한 물질의 질문을 처리하지 못했습니다.'
  } finally {
    busy.value = false
  }
}

function formatDate(value?: string) {
  if (!value) return '확인일 정보 없음'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat('ko-KR').format(date)
}

function formatDateTime(value: string) {
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat('ko-KR', { dateStyle: 'medium', timeStyle: 'short' }).format(date)
}

onMounted(() => void checkAuth())
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <a class="brand" href="/" aria-label="톡talk 홈"><span class="brand-mark">t</span><span>톡,talk</span></a>
      <div class="topbar-right">
        <span class="service-label"><span class="live-dot"></span> 시약 안전정보 탐색</span>
        <template v-if="authState === 'signed-in'">
          <span class="user-chip"><span class="avatar">{{ username.slice(0, 1) || '연' }}</span>{{ username || '로그인 사용자' }}</span>
          <button class="text-button" type="button" @click="logout">로그아웃</button>
        </template>
      </div>
    </header>

    <main v-if="authState === 'checking'" class="center-state">
      <span class="spinner" aria-hidden="true"></span>
      <p>로그인 상태를 확인하고 있습니다</p>
    </main>

    <main v-else-if="authState === 'unavailable'" class="auth-layout">
      <section class="auth-intro">
        <p class="eyebrow">RESEARCH SAFETY, MADE CLEAR</p>
        <h1>시약을 확인하는 순간,<br /><em>근거가 곁에 있도록.</em></h1>
        <p class="intro-copy">NIOSH 참고 자료에서 필요한 정보를 찾고, 시연용 재고를 한 화면에서 확인합니다.</p>
        <div class="intro-note"><span class="note-icon">i</span><span>실제 취급 전에는 공급자가 제공한 제품별 MSDS와 담당자 확인을 따르세요.</span></div>
      </section>
      <section class="auth-card">
        <div class="card-kicker">SECURE ACCESS</div>
        <h2>인증 서비스를 연결할 수 없습니다</h2>
        <p class="muted">Java 인증 서버가 아직 준비되지 않았습니다. 서버가 실행되면 로그인할 수 있습니다.</p>
        <p v-if="authError" class="inline-error">{{ authError }}</p>
        <button class="button button-primary full-button" type="button" @click="checkAuth">다시 확인</button>
        <div class="auth-footnote">로그인 후 질문·출처·시연용 재고 화면을 이용할 수 있습니다.</div>
      </section>
    </main>

    <main v-else-if="authState === 'signed-out'" class="auth-layout">
      <section class="auth-intro">
        <p class="eyebrow">RESEARCH SAFETY, MADE CLEAR</p>
        <h1>시약을 확인하는 순간,<br /><em>근거가 곁에 있도록.</em></h1>
        <p class="intro-copy">NIOSH 참고 자료에서 필요한 정보를 찾고, 시연용 재고를 한 화면에서 확인합니다.</p>
        <div class="intro-note"><span class="note-icon">i</span><span>실제 취급 전에는 공급자가 제공한 제품별 MSDS와 담당자 확인을 따르세요.</span></div>
      </section>
      <section class="auth-card">
        <div class="card-kicker">SECURE ACCESS</div>
        <h2>{{ authMode === 'login' ? '다시 오셨군요' : '계정 만들기' }}</h2>
        <p class="muted">{{ authMode === 'login' ? '계정에 로그인해 안전정보를 확인하세요.' : '실습용 계정을 등록합니다.' }}</p>
        <form class="auth-form" @submit.prevent="submitAuth">
          <label for="username">아이디</label>
          <input id="username" v-model="authUsername" autocomplete="username" placeholder="아이디 입력" required />
          <label for="password">비밀번호</label>
          <input id="password" v-model="authPassword" :autocomplete="authMode === 'login' ? 'current-password' : 'new-password'" type="password" placeholder="비밀번호 입력" required />
          <p v-if="authError" class="inline-error" role="status">{{ authError }}</p>
          <button class="button button-primary full-button" type="submit" :disabled="authBusy">
            {{ authBusy ? '요청 중…' : authMode === 'login' ? '로그인' : '가입하고 로그인하기' }}
          </button>
        </form>
        <button class="switch-auth" type="button" @click="authMode = authMode === 'login' ? 'signup' : 'login'; authError = ''">
          {{ authMode === 'login' ? '계정이 없으신가요? 회원가입' : '이미 계정이 있나요? 로그인' }}
        </button>
      </section>
    </main>

    <main v-else class="workspace">
      <section class="welcome-row">
        <div>
          <p class="eyebrow">NIOSH REFERENCE · DEMO INVENTORY</p>
          <h1>어떤 시약을 확인할까요?</h1>
          <p class="welcome-copy">물질을 먼저 선택하거나, 질문에 물질명을 포함해 바로 물어보세요.</p>
        </div>
        <div class="welcome-badge"><span class="badge-icon">✳</span><span>근거 중심<br /><strong>안전정보 탐색</strong></span></div>
      </section>

      <section class="query-card" aria-labelledby="query-title">
        <div class="query-heading">
          <div><span class="step-number">01</span><h2 id="query-title">질문 시작하기</h2></div>
          <span class="private-label"><span class="lock-icon">●</span> 인증된 세션</span>
        </div>
        <div class="mode-tabs" role="tablist" aria-label="질문 방식">
          <button type="button" role="tab" :aria-selected="flow === 'ask'" :class="{ active: flow === 'ask' }" @click="setFlow('ask')"><span>✦</span> 질문으로 찾기</button>
          <button type="button" role="tab" :aria-selected="flow === 'choose'" :class="{ active: flow === 'choose' }" @click="setFlow('choose')"><span>⌕</span> 물질을 선택하기</button>
        </div>

        <div v-if="flow === 'choose'" class="material-picker">
          <label for="material-search">물질명 또는 동의어</label>
          <div class="picker-row">
            <input id="material-search" v-model="materialQuery" placeholder="예: 아세톤, ethanol" @keydown.enter.prevent="loadMaterials" />
            <button class="button button-soft" type="button" :disabled="materialsBusy" @click="loadMaterials">{{ materialsBusy ? '찾는 중…' : '물질 찾기' }}</button>
          </div>
          <div v-if="materials.length" class="material-list" aria-label="물질 후보">
            <button v-for="item in materials" :key="item.material_id" type="button" class="material-option" :class="{ selected: selectedMaterial?.material_id === item.material_id }" @click="selectedMaterial = item; clearResult()">
              <span class="chemical-symbol">{{ item.name.slice(0, 1) }}</span>
              <span class="material-details"><strong>{{ item.name }}</strong><small>CAS {{ item.cas_number ?? '정보 없음' }}</small></span>
              <span class="option-arrow">↗</span>
            </button>
          </div>
          <p v-else-if="!materialsBusy && !pageError" class="helper-text">
            {{ materialsSearched ? '일치하는 물질이 없습니다. 물질명이나 영문 동의어를 바꿔 검색해 주세요.' : '물질을 검색하면 사용 가능한 자료가 표시됩니다.' }}
          </p>
        </div>

        <form class="question-form" @submit.prevent="submitQuestion">
          <label for="question">{{ flow === 'ask' ? '질문' : '선택한 물질에 대해 질문' }}</label>
          <div v-if="flow === 'choose' && selectedMaterial" class="selected-pill"><span class="tiny-check">✓</span>{{ selectedMaterial.name }}<span>CAS {{ selectedMaterial.cas_number }}</span><button type="button" aria-label="선택 해제" @click="selectedMaterial = null">×</button></div>
          <textarea id="question" v-model="question" rows="3" :placeholder="flow === 'ask' ? '예: 아세톤의 노출 경로와 주요 증상은 무엇인가요?' : '예: 보호구 권고는 무엇인가요?'" @keydown.meta.enter.prevent="submitQuestion" @keydown.ctrl.enter.prevent="submitQuestion"></textarea>
          <div class="form-bottom"><span class="helper-text">{{ flow === 'ask' ? '한 가지 물질을 찾지 못하거나 여러 개가 나오면 선택을 요청합니다.' : '선택한 물질의 근거만 검색합니다.' }}</span><button class="button button-primary ask-button" type="submit" :disabled="!canAsk || (flow === 'choose' && !selectedMaterial)">{{ busy ? '근거를 찾는 중…' : '질문하기' }} <span>↗</span></button></div>
        </form>
        <div v-if="pageError" class="error-banner" role="alert"><span>!</span>{{ pageError }}</div>
      </section>

      <section v-if="answer" class="results" aria-live="polite">
        <div class="result-title-row"><div><span class="step-number">02</span><h2>확인 결과</h2></div><span v-if="activeMaterial" class="result-material">{{ activeMaterial.name }} <small>CAS {{ activeMaterial.cas_number }}</small></span></div>

        <div v-if="answer.resolution.status === 'not_found'" class="resolution-card">
          <div class="resolution-icon">?</div>
          <div class="resolution-content">
            <strong>질문에서 물질을 찾지 못했습니다</strong>
            <p>물질명을 포함해 다시 질문하거나, 물질을 검색해 선택해 주세요.</p>
            <button class="candidate-button" type="button" @click="setFlow('choose')">물질 검색해서 선택 <span>열기 →</span></button>
          </div>
        </div>
        <div v-else-if="answer.resolution.status === 'ambiguous'" class="resolution-card">
          <div class="resolution-icon">?</div><div class="resolution-content"><strong>어떤 물질을 말씀하셨나요?</strong><p>질문에서 여러 물질이 확인되어 답변 전에 하나를 선택해야 합니다.</p><div class="candidate-list"><button v-for="candidate in answer.resolution.candidates" :key="candidate.material_id" type="button" class="candidate-button" :disabled="busy" @click="askForCandidate(candidate)">{{ candidate.name }} <span>선택 →</span></button></div></div>
        </div>
        <div v-else class="result-grid">
          <article class="answer-card">
            <div class="answer-card-head"><span class="answer-icon">✳</span><div><span class="card-kicker">EVIDENCE-BASED RESPONSE</span><h3>질문에 대한 답변</h3></div><span v-if="answer.needs_review" class="review-tag">담당자 확인 필요</span><span v-else class="verified-tag"><span>✓</span> 근거 확인</span></div>
            <p class="answer-text">{{ answer.answer }}</p>
            <div v-if="answer.needs_review" class="review-note"><span>i</span> 제공된 자료에서 충분한 근거를 찾지 못했습니다. 실제 제품별 MSDS와 안전 담당자를 확인하세요.</div>
            <div v-if="answer.sources.length" class="source-list">
              <h4><span class="source-count">{{ answer.sources.length }}</span> 참고 근거</h4>
              <article v-for="(source, index) in answer.sources" :key="`${source.title}-${source.section}-${index}`" class="source-item">
                <span class="source-index">{{ String(index + 1).padStart(2, '0') }}</span>
                <div class="source-copy"><strong>{{ source.title || source.source_file || 'NIOSH Pocket Guide' }}</strong><span>{{ source.section || '관련 항목' }}<template v-if="source.pdf_page"> · PDF {{ source.pdf_page }}쪽</template></span><small>CAS {{ source.cas_number || activeMaterial?.cas_number || '확인 필요' }} · 확인일 {{ formatDate(source.checked_at) }}</small></div>
                <a v-if="source.url" class="source-link" :href="source.url" target="_blank" rel="noreferrer" :aria-label="`${source.title} 원문 열기`">↗</a>
              </article>
            </div>
            <p class="source-empty" v-else>표시할 근거 자료가 없습니다.</p>
          </article>

          <aside class="inventory-card">
            <div class="inventory-head"><div class="inventory-icon">▤</div><div><span class="card-kicker">LAB INVENTORY</span><h3>재고 조회</h3></div><span class="demo-tag">시연용</span></div>
            <p class="inventory-caption">질문 답변과 별도로 DB에서 조회한 가상 재고입니다.</p>
            <div v-if="inventoryError" class="inventory-state inventory-error"><span>!</span><div><strong>재고를 불러오지 못했어요</strong><p>{{ inventoryError }}</p></div></div>
            <div v-else-if="!inventory" class="inventory-state"><span class="spinner small"></span><p>재고를 확인하고 있습니다</p></div>
            <div v-else-if="inventory.items.length === 0" class="inventory-state empty-inventory"><span>—</span><div><strong>등록된 시연 재고가 없습니다</strong><p>빈 목록은 보유량 0을 의미하지 않습니다.</p></div></div>
            <div v-else class="stock-list"><article v-for="item in inventory.items" :key="item.item_id" class="stock-item"><div class="stock-top"><strong>{{ item.display_name }}</strong><span class="stock-demo">DEMO</span></div><div class="stock-quantity">{{ item.quantity }}<small>{{ item.unit }}</small></div><div class="stock-meta"><span>⌖ {{ item.location }}</span><span>갱신 {{ formatDateTime(item.updated_at) }}</span></div></article></div>
            <div class="inventory-disclaimer">가상 데이터 · 실제 연구실 재고가 아닙니다</div>
          </aside>
        </div>
        <p class="safety-disclaimer">NIOSH Pocket Guide는 일반 참고자료입니다. 실제 취급은 공급자가 제공한 제품별 MSDS와 안전 담당자의 확인을 따르세요.</p>
      </section>

      <section v-else class="guidance-row">
        <div class="guidance-card"><span class="guidance-icon">⌕</span><div><strong>근거가 있는 답변</strong><p>답변과 함께 원문 출처·항목·확인일을 표시합니다.</p></div></div>
        <div class="guidance-card"><span class="guidance-icon inventory-guidance">▤</span><div><strong>별도 재고 조회</strong><p>시연용 수량과 위치를 안전정보와 구분해 보여줍니다.</p></div></div>
      </section>
    </main>

    <footer class="footer"><span>톡,talk <span class="footer-separator">·</span> 근거를 확인하는 안전정보</span><span>NIOSH 일반 참고정보 <span class="footer-separator">·</span> 제품별 MSDS 대체 불가</span></footer>
  </div>
</template>
