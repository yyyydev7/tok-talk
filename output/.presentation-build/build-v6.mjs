import fs from 'node:fs/promises';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { Presentation, PresentationFile } from '@oai/artifact-tool';

const root='/Users/daehun/Desktop/mini_team_project/tok-talk';
const build=path.join(root,'output/.presentation-build-v6');
const out=path.join(root,'output/pptx/toktalk_final_presentation_20261026_v6.pptx');
const afterPath='/var/folders/xr/p0t01tbj0b5gfw9m7g9zkdhw0000gn/T/codex-clipboard-989970fd-645d-4b31-8ab6-088b89c7fbab.png';
const teamPath=process.env.TOKTALK_TEAM_IMAGE;
if (!teamPath) throw new Error('TOKTALK_TEAM_IMAGE is required');
const skill='/Users/daehun/.codex/plugins/cache/openai-primary-runtime/presentations/26.1020.11127/skills/presentations';
const font='Nanum Gothic';
const C={ink:'#172b25',green:'#17684f',deep:'#10533e',mint:'#e8f2ec',muted:'#78817a',line:'#dfe8e0',page:'#f7f8f5',white:'#ffffff',amber:'#a66b13',soft:'#f2f5f1'};
const P=Presentation.create({slideSize:{width:1280,height:720}});
function tx(s,text,x,y,w,h,size=28,color=C.ink,bold=false,align='left'){
 const q=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{style:'solid',fill:'none',width:0}});
 q.text=text;q.text.style={fontSize:size,color,bold,typeface:font,alignment:align,verticalAlignment:'middle',wrap:'square',autoFit:'shrinkText',insets:0};return q;
}
function rule(s,x,y,w,color=C.line,h=2){s.shapes.add({geometry:'rect',position:{left:x,top:y,width:w,height:h},fill:color,line:{style:'solid',fill:'none',width:0}})}
function slide(section,title,num){
 const s=P.slides.add();s.background.fill=C.page;
 tx(s,'TOK,TALK  /  '+section.toUpperCase(),64,33,850,28,14,C.green,true);
 tx(s,title,64,81,1150,72,42,C.ink,true);
 rule(s,64,166,1152,C.line,2);
 tx(s,String(num).padStart(2,'0')+' / 13',1140,677,76,23,13,C.muted,true,'right');
 return s;
}
function notes(s,t){s.speakerNotes.text=t}
function img(s,p,x,y,w,h,alt,fit='contain',crop){const bytes=readFileSync(p);s.images.add({blob:bytes,contentType:p.endsWith('.jpg')?'image/jpeg':'image/png',alt,fit,position:{left:x,top:y,width:w,height:h},...(crop?{crop}:{})})}
function pair(s,label,value,y){tx(s,label,64,y,245,34,20,C.green,true);tx(s,value,320,y-1,880,62,25,C.ink);rule(s,64,y+65,1152,C.line,1)}

// 1 — opening and requested 10-minute structure
{
 const s=P.slides.add();s.background.fill=C.page;
 img(s,path.join(root,'frontend/public/media/lab-pour-poster.jpg'),676,0,604,720,'Laboratory pour photograph from the tok-talk frontend','cover');
 tx(s,'TOK,TALK',62,61,520,30,17,C.green,true);
 tx(s,'실험 순간에 필요한\n화학물질 안전정보',62,176,580,190,62,C.ink,true);
 tx(s,'질문을 공식 자료의 근거와 연결하다',65,395,565,48,27,C.green);
 rule(s,64,488,536,C.green,3);
 tx(s,'문제 1분  ·  아키텍처 2분  ·  라이브 데모 3분',65,520,565,45,19,C.ink);
 tx(s,'결과 2분  ·  한계와 다음 단계 2분',65,559,565,45,19,C.ink);
 tx(s,'AI 서비스 개발 Mini-project  |  2026.10.26',65,658,535,28,15,C.muted);
 notes(s,'10분 구성은 사용자가 제시한 발표 양식(문제 1분, 아키텍처 2분, 라이브 데모 3분, 결과 2분, 한계·다음 2분)에 맞춤. 사진은 프로젝트 frontend/public/media/lab-pour-poster.jpg.');
}
// 2 — customer problem
{
 const s=slide('문제 · 1분','시약을 쓰고 다시 보관할 때',2);
 tx(s,'연구실에서는 물질명을 아는 것만으로 안전하게 반납하기 어렵습니다.',64,192,1100,55,28,C.ink);
 pair(s,'보관','냉장고별 온도와 인화성 물질의 분리 보관 조건을 다시 확인해야 합니다.',283);
 pair(s,'취급','고체·액체·용액 상태에 따라 보호구와 환기 조건이 달라집니다.',391);
 pair(s,'폐기','산·염기·유기용매 폐액을 혼합하지 않도록 분류해야 합니다.',499);
 tx(s,'필요한 정보는 길게 작성된 SDS의 여러 항목에 흩어져 있습니다.',64,618,1090,38,24,C.green,true);
 notes(s,'문제 정의는 사용자가 제공한 tok-talk 기획 설명을 요약. 실제 제품별 보관 위치와 연구실 운영 규칙은 공식 자료만으로 확정할 수 없다는 점을 다음 슬라이드에서 구분.');
}
// 3 — product scope
{
 const s=slide('문제 → 해결','문서 제목보다 상황을 먼저 묻습니다',3);
 tx(s,'“아세톤은 어떻게 보관하나요?”',64,213,1110,63,35,C.ink,true);
 rule(s,64,286,1152,C.line,1);
 tx(s,'“메탄올이 눈에 닿으면 어떻게 해야 하나요?”',64,315,1110,63,35,C.ink,true);
 rule(s,64,388,1152,C.line,1);
 tx(s,'“톨루엔 노출을 줄이려면?”',64,417,1110,63,35,C.ink,true);
 tx(s,'KOSHA MSDS와 NIOSH 자료에서 관련 항목을 찾아 한국어 답변과 출처를 제공합니다.',64,553,1100,80,27,C.green,true);
 notes(s,'주 대상은 소규모 연구·개발 실험실. 사용자 제공 기획 문서의 문제 정의와 공식 자료 기반 RAG 범위를 바탕으로 작성.');
}
// 4 — architecture
{
 const s=P.slides.add();s.background.fill=C.white;
 img(s,'/Users/daehun/Downloads/tok-talk-architecture.png',0,0,1280,720,'User supplied tok-talk system architecture diagram','contain');
 notes(s,'사용자가 제공한 아키텍처 다이어그램을 원본 비율 그대로 전체 화면에 배치했다. 원본 파일: /Users/daehun/Downloads/tok-talk-architecture.png.');
}
// 5 — RAG mechanics
{
 const s=slide('아키텍처 · 2분','복합 질문은 요청 항목별로 검색',5);
 tx(s,'질문: “아세톤의 노출 경로와 안전한 보관 방법은?”',64,200,1120,55,31,C.ink,true);
 rule(s,64,274,1152,C.line,1);
 tx(s,'노출 경로',64,310,220,38,26,C.green,true);
 tx(s,'NIOSH 노출 경로 + 약어표에서 흡입·섭취·피부/눈 접촉 확인',300,305,870,65,22,C.ink);
 rule(s,64,391,1152,C.line,1);
 tx(s,'보관 방법',64,431,220,38,26,C.green,true);
 tx(s,'KOSHA 취급 및 저장방법에서 환기·밀폐·점화원 조건 확인',300,427,870,65,22,C.ink);
 rule(s,64,514,1152,C.line,1);
 tx(s,'두 근거를 함께 제공 → 인용 번호 검사 → 답변·출처 표시',64,550,1110,55,27,C.ink,true);
 tx(s,'요청 항목의 근거가 없으면 담당자 확인 안내',64,616,1110,38,21,C.muted);
 notes(s,'근거: rag/app/services/rag.py의 INTENTS, _retrieve, answer. 구체적 안전정보는 실제 원문·제품별 MSDS 검증이 필요하다.');
}
// 6 — live demo
{
 const s=slide('라이브 데모 · 3분','질문 입력 화면',6);
 tx(s,'물질 선택·텍스트 입력·음성 질문을 한 화면에서 시작합니다.',64,191,1100,45,24,C.ink);
 img(s,'/Users/daehun/Downloads/질문창.png',110,247,1060,355,'User supplied screenshot of the question input screen','cover',{left:0.287,top:0.16,right:0.29,bottom:0.555});
 tx(s,'검색 버튼으로 물질을 고르고, 질문하거나 마이크로 음성을 입력합니다.',64,618,1130,38,21,C.green,true);
 notes(s,'사용자가 제공한 질문창.png를 입력창 중심으로 확대했다. 로그인 화면은 사용하지 않았다.');
}
// 7 — acetone answer demo
{
 const s=slide('라이브 데모 · 3분','아세톤: 두 항목에 한 번에 답변',7);
 tx(s,'질문: 아세톤의 노출 경로와 안전한 보관 방법은?',64,190,1110,43,23,C.ink,true);
 img(s,'/Users/daehun/Downloads/아세톤.png',64,251,1152,377,'User supplied enlarged screenshot of the acetone answer','cover',{left:0.308,top:0.249,right:0.312,bottom:0.504});
 tx(s,'흡입·섭취·피부/눈 접촉  /  환기·밀폐·점화원 회피',64,638,1130,31,19,C.green,true);
 notes(s,'사용자가 제공한 아세톤.png에서 답변 본문을 크게 확대했다. 원본 화면의 출처 목록은 결과 비교 슬라이드와 발표 시 실제 서비스 화면에서 확인할 수 있다.');
}
// 8 — typo correction demo
{
 const s=slide('라이브 데모 · 3분','오탈자에도 표준 물질명으로 답변',8);
 tx(s,'입력: “이세톤”  /  답변의 물질명: “아세톤”',64,190,1110,43,23,C.ink,true);
 img(s,'/Users/daehun/Downloads/이세톤.png',64,251,1152,377,'User supplied enlarged screenshot of the typo-corrected acetone answer','cover',{left:0.309,top:0.269,right:0.312,bottom:0.484});
 tx(s,'CAS 67-64-1의 안전 자료를 근거로 같은 항목을 답변',64,638,1130,31,19,C.green,true);
 notes(s,'사용자가 제공한 이세톤.png에서 답변 본문을 크게 확대했다. 이 자료는 오탈자 입력에서 아세톤 이름으로 답변한 화면 사례다.');
}
// 7 — before/after example with two actual captures
{
 const s=slide('결과 · 2분','복합 질문에서 빠지던 항목을 보완',9);
 tx(s,'화면 비교 3건  ·  요청한 두 항목 충족',64,194,900,35,21,C.muted);
 tx(s,'0/3  →  3/3',64,231,850,70,58,C.green,true);
 rule(s,64,307,1152,C.line,1);
 tx(s,'수정 전',64,316,540,31,20,C.muted,true);
 tx(s,'수정 후',665,316,540,31,20,C.green,true);
 img(s,'/var/folders/xr/p0t01tbj0b5gfw9m7g9zkdhw0000gn/T/codex-clipboard-e3128a78-67c4-443b-b08e-81dc7e0ecf7b.png',64,352,550,269,'User supplied before screenshot of the acetone exposure and storage answer','cover',{left:0,top:0.16,right:0.325,bottom:0.33});
 img(s,afterPath,665,352,550,269,'User supplied after screenshot of the acetone exposure and storage answer','cover',{left:0,top:0.16,right:0.325,bottom:0.31});
 tx(s,'흡입만 제시해 섭취·피부/눈 접촉이 빠짐',64,628,550,31,18,C.ink);
 tx(s,'흡입·섭취·피부/눈 접촉과 보관 조건을 제시',665,628,550,31,18,C.ink);
 notes(s,'왼쪽은 사용자 제공 수정 전 화면 캡처. 오른쪽은 사용자 제공 수정 후 화면 캡처. 0/3→3/3은 A01–A03 화면 사례의 두 요청 항목 포함 여부이며 정확도·근거성 전체 점수가 아니다.');
}
// 8 — chunking metrics
{
 const s=slide('결과 · 2분','검색 적중을 유지하며 색인 잡음을 제거',10);
 tx(s,'전체 청크',64,213,450,37,21,C.muted);
 tx(s,'715  →  553',64,248,775,82,59,C.green,true);
 tx(s,'162개 감소  ·  약 22.7%',64,340,700,40,23,C.ink);
 rule(s,64,415,1152,C.line,1);
 const rows=[['자료 없음 청크','107','0'],['본문 없는 머리글','66','0'],['CAS 없는 청크','152','0']];
 tx(s,'항목',64,434,585,30,19,C.muted,true);tx(s,'수정 전',814,434,160,30,19,C.muted,true,'center');tx(s,'수정 후',1020,434,160,30,19,C.muted,true,'center');
 rows.forEach((r,i)=>{let y=478+i*51;tx(s,r[0],64,y,630,35,22,C.ink);tx(s,r[1],815,y,160,35,22,C.ink,true,'center');tx(s,r[2],1020,y,160,35,22,C.green,true,'center');rule(s,64,y+44,1152,C.line,1)});
 notes(s,'근거: datapipeline/reports/chunking_before_after_20261026.md. 항목별 개수는 겹칠 수 있으므로 합산하지 않는다. 동일 BGE-M3, 동일 9개 질문에서 기대 항목 top-5 적중은 9/9→9/9. 색인 용량과 질의 지연은 미측정.');
}
// 9 — evaluation and loop
{
 const s=slide('평가·개선 루프','원인 단계를 바꾸고 같은 질문으로 재평가',11);
 const rows=[
  ['검색 누락','복합 질문 의도 분해·섹션별 검색','화면 3건 두 항목 포함 0/3→3/3'],
  ['빈 근거 혼입','자료 없음·머리글 청크 제외','107→0 / 66→0'],
  ['청킹 부작용 우려','같은 임베딩·CAS·top-5로 비교','기대 항목 9/9→9/9 유지']
 ];
 tx(s,'관찰',64,219,260,32,19,C.green,true);tx(s,'수정',338,219,460,32,19,C.green,true);tx(s,'재평가',840,219,355,32,19,C.green,true);
 rule(s,64,263,1152,C.green,2);
 rows.forEach((r,i)=>{let y=286+i*118;tx(s,r[0],64,y,250,67,24,C.ink,true);tx(s,r[1],338,y,466,72,21,C.ink);tx(s,r[2],840,y,355,76,21,C.ink);rule(s,64,y+98,1152,C.line,1)});
 tx(s,'검색 적중, 두 항목 포함, 답변 정확성은 서로 다른 지표입니다.',64,636,1100,38,21,C.muted);
 notes(s,'근거: output/evaluation/toktalk_eval_set_20261026.md. 3건은 수동 화면 비교, 9건은 자동 검색 항목 평가. 한 변경의 단독 효과로 합산하지 않는다.');
}
// 10 — limitations and next steps
{
 const s=slide('한계·다음 · 2분','다음 검증에서 확인할 것',12);
 pair(s,'현재 확인','선정 물질 5종의 공식 자료를 검색하고 출처와 함께 답변합니다.',222);
 pair(s,'미측정','문장별 정확성·근거성·환각률, 지연시간·비용은 아직 점수화하지 않았습니다.',338);
 pair(s,'다음 평가','복합 질문 5건을 원문과 대조하고, 자료에 없는 현장 질문 2건의 보류 응답을 시험합니다.',454);
 tx(s,'실제 취급·보관 결정은 제품별 MSDS와 연구실 안전 담당자의 확인이 필요합니다.',64,606,1120,58,24,C.green,true);
 notes(s,'근거: output/evaluation/toktalk_eval_set_20261026.md. N01–N02는 미실행. KOSHA/NIOSH 공식 자료는 특정 제품과 연구실 자체 배치를 확정하지 않는다.');
}
// 11 — team introduction with portraits cropped from the user supplied collage
{
 const s=slide('팀 소개','5명이 나눠 구현한 톡,talk',13);
 const members=[
  {name:'김대훈',role:'RAG · LLM 서빙',work:'복합 질문별 근거 검색\nFastAPI·LLM 답변 생성',crop:{left:0.058,top:0.113,right:0.756,bottom:0.613}},
  {name:'강도희',role:'Front',work:'Vue 질문·결과 화면\n인증·음성 API 연동',crop:{left:0.5,top:0.113,right:0.307,bottom:0.613}},
  {name:'정수민',role:'Backend',work:'Java 로그인·계정 API\nJWT 쿠키·MariaDB',crop:{left:0.054,top:0.662,right:0.754,bottom:0.062}},
  {name:'이연주',role:'데이터 파이프라인',work:'KOSHA·NIOSH 수집·청킹\nBGE-M3·FAISS 색인',crop:{left:0.498,top:0.4,right:0.302,bottom:0.338}},
  {name:'손연우',role:'배포',work:'Docker Compose·Nginx\n헬스체크·기동 검사',crop:{left:0.503,top:0.666,right:0.307,bottom:0.062}},
 ];
 members.forEach((m,i)=>{
  const x=64+i*233;
  img(s,teamPath,x+22,207,170,191,`${m.name} portrait cropped from user supplied team image`,'cover',m.crop);
  tx(s,m.name,x,419,214,38,29,C.ink,true,'center');
  tx(s,m.role,x,461,214,35,20,C.green,true,'center');
  rule(s,x+30,509,154,C.line,1);
  tx(s,m.work,x,530,214,85,18,C.ink,false,'center');
 });
 notes(s,'팀원 이름과 담당 분야는 사용자가 제공했다. 세부 작업은 rag/app, frontend/src, backend/src/main/java/com/toktalk/auth, datapipeline/pipeline, infra 및 Compose 설정을 확인해 요약했다. 사진은 사용자가 제공한 팀 소개 이미지에서 각 초상 영역을 잘라 사용했다.');
}

await fs.mkdir(build,{recursive:true});
for(let i=0;i<P.slides.items.length;i++){
 const png=await P.export({slide:P.slides.items[i],format:'png',scale:1});
 await fs.writeFile(path.join(build,`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await png.arrayBuffer()));
}
const candidate=path.join(build,'candidate.pptx');
await (await PresentationFile.exportPptx(P)).save(candidate);
const {finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
const result=await finalizePresentation({
 workspaceDir:root,candidatePath:candidate,finalPath:out,
 pythonExecutable:'/Users/daehun/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3',
 integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),
 layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit'],
 fontPolicy:{basis:'design',families:[font]},
 explicitTotalSlideCount:13,
 requiredNativeTableOwnerSlides:[],requiredNativeChartOwnerSlides:[],
 verifyArtifactToolImport:true,
 receiptPath:path.join(build,'validation.json'),
});
console.log(JSON.stringify({out,slides:P.slides.items.length,result},null,2));
