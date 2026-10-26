import { ref, watch } from 'vue'

export type Material = {
  material_id: string
  name: string
  aliases?: string[]
  cas_number?: string
  source_title?: string
}

export type Source = {
  cas_number?: string
  title?: string
  section?: string
  url?: string
  source_file?: string
  pdf_page?: string
  checked_at?: string
}

export type RagResponse = {
  answer: string
  sources: Source[]
  needs_review: boolean
  answer_mode?: 'general' | 'rag'
  material: Material | null
  resolution: {
    status: 'resolved' | 'ambiguous' | 'not_found'
    candidates: Material[]
  }
}

export type InventoryItem = {
  item_id: string
  display_name: string
  quantity: number
  unit: string
  location: string
  updated_at: string
}

export type InventoryResponse = {
  material_id: string
  is_demo: boolean
  items: InventoryItem[]
}

type AuthResponse = { ok?: boolean; username?: string; error?: string }
type AuthState = 'checking' | 'signed-out' | 'signed-in' | 'unavailable'

const pageHostname = typeof window === 'undefined' ? 'localhost' : window.location.hostname
const localHosts = new Set(['localhost', '127.0.0.1'])

function serviceBase(configured: string | undefined, port: number): string {
  // Keep local API requests on the page's host so the HttpOnly auth cookie is
  // shared when a developer opens the app as either localhost or 127.0.0.1.
  if (configured === '') return ''
  const base = new URL(configured ?? `http://${pageHostname}:${port}`)
  if (localHosts.has(pageHostname) && localHosts.has(base.hostname)) {
    base.hostname = pageHostname
  }
  return base.toString().replace(/\/$/, '')
}

const authBase = serviceBase(import.meta.env.VITE_AUTH_BASE_URL, 8080)
const ragBase = serviceBase(import.meta.env.VITE_RAG_BASE_URL, 8001)

export const authState = ref<AuthState>('checking')
export const username = ref('')
export const authError = ref('')
export const question = ref('')
export const materialQuery = ref('')
export const materials = ref<Material[]>([])
export const materialsSearched = ref(false)
export const selectedMaterial = ref<Material | null>(null)
export const answer = ref<RagResponse | null>(null)
export const inventory = ref<InventoryResponse | null>(null)
export const inventoryError = ref('')
export const inventoryBusy = ref(false)
export const questionBusy = ref(false)
export const materialsBusy = ref(false)
export const pageError = ref('')

let authCheck: Promise<boolean> | null = null

function restoreWorkspace() {
  try {
    const saved = sessionStorage.getItem('toktalk.workspace.v1')
    if (!saved) return
    const value = JSON.parse(saved) as { question?: unknown; selectedMaterial?: unknown; answer?: unknown }
    if (typeof value.question === 'string') question.value = value.question
    if (value.selectedMaterial && typeof value.selectedMaterial === 'object') selectedMaterial.value = value.selectedMaterial as Material
    if (value.answer && typeof value.answer === 'object') answer.value = value.answer as RagResponse
  } catch {
    sessionStorage.removeItem('toktalk.workspace.v1')
  }
}

if (typeof window !== 'undefined') {
  restoreWorkspace()
  watch([question, selectedMaterial, answer], () => {
    try {
      sessionStorage.setItem('toktalk.workspace.v1', JSON.stringify({
        question: question.value,
        selectedMaterial: selectedMaterial.value,
        answer: answer.value,
      }))
    } catch {
      // Keep the current screen usable when browser storage is disabled or full.
    }
  }, { deep: true })
}

async function requestResponse(base: string, path: string, init: RequestInit = {}): Promise<Response> {
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
    clearResult()
    const message = wasSignedIn
      ? '로그인 시간이 끝났습니다. 다시 로그인해 주세요.'
      : path === '/api/login'
        ? '아이디 또는 비밀번호를 확인해 주세요.'
        : '로그인이 필요합니다. 로그인한 뒤 다시 이용해 주세요.'
    if (wasSignedIn) authError.value = message
    throw new Error(message)
  }
  if (!response.ok) {
    const message = response.status === 413
      ? '음성 녹음이 너무 깁니다. 짧게 나누어 다시 시도해 주세요.'
      : response.status === 415
        ? '지원하지 않는 음성 형식입니다. 다른 브라우저에서 다시 시도해 주세요.'
        : response.status === 422
      ? '입력 내용을 확인해 주세요.'
      : response.status === 503
        ? '서비스가 준비되지 않았거나 일시적으로 사용할 수 없습니다. 잠시 후 다시 시도해 주세요.'
        : response.status >= 500
          ? '서비스 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.'
          : `요청을 처리하지 못했습니다. (${response.status})`
    throw new Error(message)
  }
  return response
}

async function request<T>(base: string, path: string, init: RequestInit = {}): Promise<T> {
  const response = await requestResponse(base, path, init)
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export async function transcribeAudio(audio: Blob): Promise<string> {
  const extension = audio.type.includes('ogg') ? 'ogg'
    : audio.type.includes('mp4') ? 'm4a'
      : audio.type.includes('mpeg') ? 'mp3'
        : 'webm'
  const form = new FormData()
  form.append('file', audio, `question.${extension}`)
  const response = await requestResponse(ragBase, '/speech-to-text', {
    method: 'POST',
    body: form,
  })
  const result = await response.json() as { text?: string }
  const text = result.text?.trim()
  if (!text) throw new Error('음성을 텍스트로 변환하지 못했습니다. 다시 녹음해 주세요.')
  return text
}

export async function synthesizeSpeech(text: string): Promise<Blob> {
  const response = await requestResponse(ragBase, '/text-to-speech', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  })
  const audio = await response.blob()
  if (!audio.size) throw new Error('생성된 음성을 재생할 수 없습니다.')
  return audio
}

export async function checkAuth(force = false): Promise<boolean> {
  if (!force && authState.value === 'signed-in') return true
  if (!force && authState.value === 'signed-out') return false
  if (!force && authState.value === 'unavailable') return false
  if (authCheck) return authCheck

  authState.value = 'checking'
  authCheck = (async () => {
    try {
      const result = await request<AuthResponse>(authBase, '/api/auth/check')
      authState.value = result.ok ? 'signed-in' : 'signed-out'
      username.value = result.username ?? ''
      authError.value = ''
      return Boolean(result.ok)
    } catch (error) {
      if (authState.value !== 'signed-out') {
        authState.value = 'unavailable'
        authError.value = error instanceof Error ? error.message : '인증 서버에 연결할 수 없습니다.'
      }
      return false
    } finally {
      authCheck = null
    }
  })()
  return authCheck
}

export async function authenticate(mode: 'login' | 'signup', rawUsername: string, password: string): Promise<boolean> {
  authError.value = ''
  const normalizedUsername = rawUsername.trim()
  if (!normalizedUsername || !password) {
    authError.value = '아이디와 비밀번호를 입력해 주세요.'
    return false
  }
  if (!/^[A-Za-z0-9._-]{3,64}$/.test(normalizedUsername)) {
    authError.value = '아이디는 영문, 숫자, 마침표, 밑줄, 하이픈을 사용해 3~64자로 입력해 주세요.'
    return false
  }
  if (password.length < 8 || password.length > 128) {
    authError.value = '비밀번호는 8~128자로 입력해 주세요.'
    return false
  }

  try {
    const body = new URLSearchParams({ username: normalizedUsername, password })
    if (mode === 'signup') {
      const response = await fetch(`${authBase}/api/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        credentials: 'include',
        redirect: 'manual',
        body,
      })
      if (!response.ok && response.status !== 302 && response.type !== 'opaqueredirect') {
        if (response.status === 409) throw new Error('이미 사용 중인 아이디입니다. 다른 아이디를 선택해 주세요.')
        if (response.status === 400) throw new Error('아이디 또는 비밀번호 형식을 확인해 주세요.')
        throw new Error(`회원가입에 실패했습니다. (${response.status})`)
      }
      return true
    }

    const result = await request<AuthResponse>(authBase, '/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body,
    })
    if (!result.ok) throw new Error(result.error ?? '로그인에 실패했습니다.')
    authState.value = 'signed-in'
    username.value = result.username ?? normalizedUsername
    authError.value = ''
    return true
  } catch (error) {
    authError.value = error instanceof Error ? error.message : '인증 요청을 완료하지 못했습니다.'
    return false
  }
}

export async function logout() {
  try {
    await fetch(`${authBase}/api/logout`, { method: 'POST', credentials: 'include' })
  } catch {
    authError.value = '로그아웃 요청에 실패했습니다. 잠시 후 다시 시도해 주세요.'
  } finally {
    authState.value = 'signed-out'
    username.value = ''
    authError.value = ''
    question.value = ''
    selectedMaterial.value = null
    clearResult()
  }
}

export function clearResult() {
  answer.value = null
  inventory.value = null
  inventoryError.value = ''
  pageError.value = ''
}

export async function loadMaterials(): Promise<Material[]> {
  materialsBusy.value = true
  pageError.value = ''
  try {
    const query = materialQuery.value.trim()
    const params = query ? `?query=${encodeURIComponent(query)}` : ''
    const result = await request<{ items: Material[] }>(ragBase, `/chemicals${params}`)
    materials.value = result.items
    materialsSearched.value = true
    return result.items
  } catch (error) {
    pageError.value = error instanceof Error ? error.message : '물질 목록을 불러오지 못했습니다.'
    return []
  } finally {
    materialsBusy.value = false
  }
}

export async function loadInventory(materialId: string): Promise<InventoryResponse | null> {
  inventory.value = null
  inventoryError.value = ''
  inventoryBusy.value = true
  try {
    inventory.value = await request<InventoryResponse>(ragBase, `/inventory?material_id=${encodeURIComponent(materialId)}`)
    return inventory.value
  } catch (error) {
    inventoryError.value = error instanceof Error ? error.message : '재고 조회를 사용할 수 없습니다.'
    return null
  } finally {
    inventoryBusy.value = false
  }
}

export async function submitQuestion(_material?: Material | null): Promise<RagResponse | null> {
  const text = question.value.trim()
  if (!text) {
    pageError.value = '질문을 입력해 주세요.'
    return null
  }
  questionBusy.value = true
  clearResult()
  pageError.value = ''
  try {
    const result = await request<RagResponse>(ragBase, '/chat-query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: text }),
    })
    answer.value = result
    if (result.material) selectedMaterial.value = result.material
    return result
  } catch (error) {
    pageError.value = error instanceof Error ? error.message : '질문을 처리하지 못했습니다.'
    return null
  } finally {
    questionBusy.value = false
  }
}
