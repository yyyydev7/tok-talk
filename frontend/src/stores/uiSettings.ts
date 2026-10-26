import { ref, watch } from 'vue'

export type UiLanguage = 'ko' | 'en'
export type UiTheme = 'light' | 'dark'

function stored<T extends string>(key: string, allowed: readonly T[], fallback: T) {
  if (typeof window === 'undefined') return fallback
  try {
    const value = localStorage.getItem(key)
    return allowed.includes(value as T) ? value as T : fallback
  } catch {
    return fallback
  }
}

export const uiLanguage = ref<UiLanguage>(stored('toktalk.language', ['ko', 'en'], 'ko'))
export const uiTheme = ref<UiTheme>(stored('toktalk.theme', ['light', 'dark'], 'light'))

const englishText: Record<string, string> = {
  '홈': 'Home', '홈으로 이동': 'Go home', '사이트맵': 'Sitemap', '바로가기': 'Quick links', '주요 메뉴': 'Main navigation',
  '로그인': 'Sign in', '회원가입': 'Create account', '로그아웃': 'Sign out', '로그인 사용자': 'Signed-in user', '질문하기': 'Ask a question', '물질 검색': 'Search materials',
  '답변·출처': 'Answers & sources', '시연용 재고': 'Demo inventory', '서비스': 'Services', '참고 자료': 'References', '이용 안내': 'About & help',
  '출처·자료 기준': 'Sources & data policy', '서비스 소개': 'About the service', '데이터 출처': 'Data sources', '문의': 'Contact',
  '연구실 화학물질 안전정보 도우미': 'Laboratory Chemical Safety Information Assistant', '재고': 'inventory', '시연용': 'Demo', '갱신': 'Updated',
  '확인일': 'Checked', '쪽': ' p.', '원문 열기': 'Open original source', '근거 확인': 'Evidence checked',
  '질문 화면으로 이동': 'Go to questions', '질문 화면': 'Question page', '다크 모드': 'Dark mode', '라이트 모드': 'Light mode',
  '다크 모드로 전환': 'Switch to dark mode', '라이트 모드로 전환': 'Switch to light mode',
  '다시 오셨군요': 'Welcome back', '계정 만들기': 'Create your account',
  '인증 상태 확인 중': 'Checking authentication', '인증 서비스를 연결할 수 없습니다': 'Unable to connect to the authentication service',
  '잠시만 기다려 주세요.': 'Please wait a moment.', 'Java 인증 서버 상태를 확인한 뒤 다시 시도해 주세요.': 'Check the Java authentication server and try again.',
  '다시 확인': 'Try again', '계정에 로그인해 안전정보를 확인하세요.': 'Sign in to explore safety information.', '실습용 계정을 등록합니다.': 'Create an account for this exercise.',
  '가입이 완료됐습니다. 로그인해 주세요.': 'Sign-up complete. Please sign in.', '아이디': 'Username', '아이디 입력': 'Enter your username', '비밀번호': 'Password',
  '비밀번호 입력': 'Enter your password', '비밀번호 숨기기': 'Hide password', '비밀번호 표시': 'Show password', '요청 중…': 'Submitting…',
  '이미 계정이 있나요? 로그인': 'Already have an account? Sign in', '계정이 없으신가요? 회원가입': 'New here? Create an account',
  '어떤 시약을 확인할까요?': 'Which chemical would you like to check?', '질문에 물질명을 적거나, 물질을 먼저 검색해 선택하세요.': 'Mention a chemical in your question, or search and select one first.',
  '근거 중심': 'Evidence based', '안전정보 탐색': 'Safety information', '질문 입력': 'Ask a question', '인증된 사용자': 'Authenticated user',
  '선택 해제': 'Clear selection', '선택한 물질에 대해 질문': 'Ask about the selected chemical', '질문': 'Question',
  '예: 보호구 권고는 무엇인가요?': 'e.g. What protective equipment is recommended?', '예: 아세톤의 노출 경로와 주요 증상은 무엇인가요?': 'e.g. What are acetone’s exposure routes and main symptoms?',
  '물질 바꾸기': 'Change chemical', '물질 검색·선택': 'Search and select a chemical', '물질명이 여러 개면 답변 전에 선택을 요청합니다.': 'If multiple chemicals are detected, you will be asked to choose one.',
  '근거를 찾는 중…': 'Finding evidence…', '근거가 있는 답변': 'Evidence-backed answers', '답변과 함께 원문 출처·항목·확인일을 확인합니다.': 'Review original sources, sections, and checked dates with each answer.',
  '별도 재고 화면': 'Separate inventory view', '시연용 수량과 위치를 안전정보와 구분해 보여줍니다.': 'Demo quantities and locations are shown separately from safety information.',
  '← 질문으로 돌아가기': '← Back to questions', '이름이나 동의어로 자료가 등록된 물질을 찾아 질문에 지정합니다.': 'Find a listed chemical by name or synonym and select it for your question.',
  '물질명 또는 동의어': 'Chemical name or synonym', '예: 아세톤, ethanol': 'e.g. acetone, ethanol', '찾는 중…': 'Searching…', '물질 찾기': 'Search chemicals',
  '동의어:': 'Synonyms:', '자료:': 'Source:', '이 물질로 질문하기': 'Ask about this chemical', '일치하는 물질이 없습니다': 'No matching chemicals found',
  '물질명이나 영문 동의어를 바꿔 검색해 주세요.': 'Try another name or English synonym.', '물질명을 검색해 주세요': 'Search for a chemical', '검색된 후보 중 하나를 선택하면 질문 화면으로 돌아갑니다.': 'Select a result to return to your question.',
  '물질 목록을 불러오고 있습니다': 'Loading chemical list', '← 질문 화면': '← Back to question', '질문 결과': 'Answer', '정보 없음': 'Not available',
  '질문에서 물질을 찾지 못했습니다': 'No chemical found in the question', '질문에 물질명을 포함하거나 물질 검색 화면에서 직접 선택해 주세요.': 'Include a chemical name or select one from the chemical search page.',
  '어떤 물질을 말씀하셨나요?': 'Which chemical did you mean?', '질문에서 여러 물질이 확인되어 하나를 선택해야 합니다.': 'Several chemicals were found. Choose one to continue.',
  '검색 중…': 'Searching…', '이 물질로 다시 검색 →': 'Search again for this chemical →', '답변': 'Answer', '담당자 확인 필요': 'Review required', '✓ 근거 확인': '✓ Evidence checked',
  '제공된 자료에서 충분한 근거를 찾지 못했습니다. 실제 제품별 MSDS와 안전 담당자를 확인하세요.': 'The supplied sources did not provide enough evidence. Check the product-specific SDS and your safety officer.',
  '참고 근거': 'Sources', '관련 항목': 'Relevant section', '확인 필요': 'Needs verification', '확인일 정보 없음': 'Checked date unavailable', '표시할 근거 자료가 없습니다.': 'No source material to display.',
  '다음으로': 'Next', '시연 재고는 안전정보 답변과 분리해 확인합니다.': 'Demo inventory is separate from safety answers.', '시연 재고 확인': 'View demo inventory', '새 질문하기': 'Ask another question',
  'NIOSH Pocket Guide는 일반 참고자료입니다. 실제 취급은 공급자가 제공한 제품별 MSDS와 안전 담당자의 확인을 따르세요.': 'The NIOSH Pocket Guide is a general reference. Follow the supplier-provided product SDS and your safety officer for handling.',
  '답변을 불러오지 못했습니다': 'Could not load the answer', '질문을 다시 제출하거나 잠시 후 재시도해 주세요.': 'Submit your question again or retry shortly.', '답변을 준비하고 있습니다': 'Preparing your answer',
  '← 질문 결과로 돌아가기': '← Back to answer', '← 질문 화면으로 돌아가기': '← Back to questions', '시연용 데이터': 'Demo data',
  '안전정보 답변과 별도로 재고 저장소에서 조회한 가상 데이터입니다.': 'This is demo inventory data, separate from safety information.', '재고를 조회하고 있습니다': 'Loading inventory', '재고를 불러오지 못했어요': 'Could not load inventory',
  '다시 조회': 'Try again', '등록된 시연 재고가 없습니다': 'No demo inventory is registered', '빈 목록은 보유량 0을 의미하지 않습니다.': 'An empty list does not mean the stock quantity is zero.', '가상 데이터 · 실제 연구실 재고가 아닙니다': 'Demo data · Not actual laboratory inventory',
  '로그인이 필요합니다. 로그인한 뒤 다시 이용해 주세요.': 'Please sign in to continue.', '로그인 시간이 끝났습니다. 다시 로그인해 주세요.': 'Your session expired. Please sign in again.',
  '아이디 또는 비밀번호를 확인해 주세요.': 'Check your username and password.', '입력 내용을 확인해 주세요.': 'Check your input.',
  '이미 사용 중인 아이디입니다. 다른 아이디를 선택해 주세요.': 'That username is already taken. Choose another one.', '아이디 또는 비밀번호 형식을 확인해 주세요.': 'Check the username or password format.',
  '아이디와 비밀번호를 입력해 주세요.': 'Enter a username and password.', '비밀번호는 8~128자로 입력해 주세요.': 'Password must be 8–128 characters.',
  '서비스에 연결할 수 없습니다. 서버 상태를 확인한 뒤 다시 시도해 주세요.': 'Could not connect to the service. Check the server and try again.',
  '인증 서버에 연결할 수 없습니다.': 'Could not connect to the authentication server.', '로그인에 실패했습니다.': 'Sign-in failed.',
  '인증 요청을 완료하지 못했습니다.': 'Could not complete the authentication request.', '로그아웃 요청에 실패했습니다. 잠시 후 다시 시도해 주세요.': 'Could not sign out. Please try again shortly.',
  '물질 목록을 불러오지 못했습니다.': 'Could not load the chemical list.', '재고 조회를 사용할 수 없습니다.': 'Inventory lookup is unavailable.',
  '질문을 입력해 주세요.': 'Enter a question.', '질문을 처리하지 못했습니다.': 'Could not process the question.',
  '아이디는 영문, 숫자, 마침표, 밑줄, 하이픈을 사용해 3~64자로 입력해 주세요.': 'Use 3–64 characters: letters, numbers, periods, underscores, or hyphens.',
  '검색된 물질 목록': 'Search results', '톡,talk 홈': 'Tok,talk home', '서비스 바로가기': 'Service links',
  '물질 검색 · 시연용 재고': 'Materials · Demo inventory',
  '업그레이드': 'Upgrade', '무료 플랜': 'Free plan', '연구실과 함께 성장하는 플랜': 'Plans that grow with your lab',
  '연구실 규모에 맞는 플랜을 선택하세요': 'Choose a plan for your laboratory', '기관 운영에 맞는 플랜을 살펴보세요': 'Find a plan for your institution',
  '공식 안전자료 검색부터 여러 연구실의 운영까지, 필요한 범위에 맞춰 시작하세요.': 'Start with the scope you need, from official safety information to managing multiple laboratories.',
  '도입 규모 선택': 'Choose organization size', '연구실': 'Laboratory', '기관': 'Institution', '플랜 목록': 'Plans',
  '현재 플랜': 'Current plan', '먼저 써보고 서비스 흐름을 확인하세요.': 'Try the service and explore how it works.', '무료': 'Free', '시연 및 기능 검토용': 'For demos and feature evaluation',
  '포함 기능': 'Included features', '등록된 물질 질문·답변': 'Questions about listed substances', '답변 근거와 출처 확인': 'Answer evidence and sources', '시연용 재고 확인': 'Demo inventory view',
  '연구실 추천': 'Recommended for labs', '한 연구실의 안전정보와 재고를 함께 관리': 'Manage safety information and inventory for one laboratory', '도입 상담': 'Talk to us', '사용 인원과 운영 범위에 맞춰 안내': 'Options based on team size and needs',
  '연구실 도입 상담': 'Discuss a lab plan', '상담 신청 기능은 도입 시 연결됩니다.': 'Consultation requests are not connected in this demo.', 'Demo의 모든 기능과 함께': 'Everything in Demo, plus',
  '실제 연구실 재고·보관 위치 관리': 'Lab inventory and storage locations', '사용자별 권한과 연구실 공유': 'User permissions and lab sharing', '재고 부족 알림과 변경 이력': 'Low-stock alerts and change history',
  '여러 연구실과 기관 운영을 통합': 'Manage multiple laboratories across an institution', '별도 협의': 'Contact us', '보안·연동·운영 요구사항에 따라 협의': 'Options based on security, integrations, and operations', '기관 도입 문의': 'Discuss an institution plan',
  '요구사항 확인 후 도입 범위를 안내합니다.': 'We will scope the plan based on your requirements.', 'Lab의 모든 기능과 함께': 'Everything in Lab, plus', '여러 연구실 통합 현황': 'Overview across laboratories',
  '기관별 접근 권한·감사 기록': 'Institution-level access and audit logs', '내부 시스템·전용 자료 연동': 'Internal systems and private sources',
  '연구실 도입 상담은 데모 화면입니다. 실제 상담 신청은 아직 연결되지 않았습니다.': 'Lab plan inquiries are a demo; the request flow is not connected yet.',
  '기관 도입 문의는 데모 화면입니다. 실제 문의 기능은 아직 연결되지 않았습니다.': 'Institution inquiries are a demo; the contact flow is not connected yet.',
}

export function toggleLanguage() {
  uiLanguage.value = uiLanguage.value === 'ko' ? 'en' : 'ko'
}

export function toggleTheme() {
  uiTheme.value = uiTheme.value === 'light' ? 'dark' : 'light'
}

export function tr(korean: string, english = englishText[korean] ?? korean) {
  return uiLanguage.value === 'ko' ? korean : english
}

if (typeof document !== 'undefined') {
  const applyLanguage = (language: UiLanguage) => {
    document.documentElement.lang = language
    try { localStorage.setItem('toktalk.language', language) } catch { /* preference remains in memory */ }
  }
  const applyTheme = (theme: UiTheme) => {
    document.documentElement.dataset.theme = theme
    try { localStorage.setItem('toktalk.theme', theme) } catch { /* preference remains in memory */ }
  }
  watch(uiLanguage, applyLanguage, { immediate: true })
  watch(uiTheme, applyTheme, { immediate: true })
}
