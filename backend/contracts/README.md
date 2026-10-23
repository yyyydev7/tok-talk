# 공동 API 계약

openapi.yaml은 제공된 API 명세서 v0.3을 옮긴 구현 목표입니다.
x-implementation-status: planned인 경로는 아직 서버에 없습니다.
현재 FastAPI의 /openapi.json에는 실제 구현된 상태 확인 API만 나타납니다.
목표 명세가 존재한다는 사실이 기능 구현 완료를 뜻하지 않습니다.

## 규칙

- Java는 폼 기반 회원가입·로그인, FastAPI는 JSON 요청을 사용합니다.
- 브라우저 인증은 ACCESS_TOKEN HttpOnly 쿠키를 목표로 합니다.
- Vue는 인증된 호출에 credentials: include를 사용합니다.
- 물질이 하나로 확정된 후 해당 material_id/CAS만 검색합니다.
- 근거 부족·미인식·복수 후보는 200 + needs_review=true입니다.
- 미인증은 401, 잘못된 요청은 422, 의존성 장애는 503입니다.
- 출처는 검색 결과의 메타데이터에서 구성하고 LLM이 만들어내게 하지 않습니다.
- 재고는 별도 DB 조회이며 items: []를 수량 0으로 해석하지 않습니다.

- Java와 FastAPI는 HS256 JWT의 `sub`, `iss`, `aud`, `iat`, `exp`, `jti`를 동일하게 검증합니다.
- JWT는 15분 동안 유효하고 `ACCESS_TOKEN` HttpOnly, SameSite=Strict 쿠키로 전달됩니다.
- 공개 HTTPS 배포에서는 `COOKIE_SECURE=true`가 필수입니다.
- 로그인 복귀 주소, 토큰 조기 폐기, 공통 오류 본문과 질문 최대 길이는 추가 결정 항목입니다.
오류 응답의 상세 스키마는 합의 전이므로 이 명세에서 고정하지 않았습니다.

변경 시 이 명세와 examples, 서버 스키마, 프론트 호출을 함께 검토합니다.
examples의 값은 문서 예시이며 실제 수집·질의 결과나 실재고가 아닙니다.
