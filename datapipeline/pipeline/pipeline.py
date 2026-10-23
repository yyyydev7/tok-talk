"""공식 물질정보 수집 및 실습 템플릿 기반 RAG 적재 도구."""
import argparse
import asyncio
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import aiohttp
from dotenv import load_dotenv
from .test_msds_api import fetch_xml, get_key

ROOT = Path(__file__).resolve().parent.parent
PDF_PATH = ROOT / "resources" / "NIOSH.pdf"
EMBEDDING_MODEL = "BAAI/bge-m3"
INDEX_CONFIG = {"embedding_model": EMBEDDING_MODEL, "metric": "cosine", "index_type": "IndexFlatIP"}
CHEMICALS = {
    "67-64-1": ("아세톤", 33, "Acetone"),
    "64-17-5": ("에탄올", 162, "Ethyl alcohol"),
    "67-56-1": ("메탄올", 230, "Methyl alcohol"),
    "108-88-3": ("톨루엔", 341, "Toluene"),
    "64-19-7": ("아세트산", 32, "Acetic acid"),
}
# 3, 9, 10은 동의어, 물성, 반응 금기 정보를 위해 보완한다.
SECTIONS = {2: "유해성·위험성", 3: "구성성분의 명칭 및 함유량", 4: "응급조치요령",
            5: "폭발·화재시 대처방법", 6: "누출사고시 대처방법", 7: "취급 및 저장방법",
            8: "노출방지 및 개인보호구", 9: "물리화학적 특성", 10: "안정성 및 반응성",
            11: "독성에 관한 정보", 13: "폐기시 주의사항", 16: "그 밖의 참고사항"}

def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def record(cas, source, section, content, url, **extra):
    return {"chemical_name": CHEMICALS[cas][0], "cas_no": cas, "source": source,
            "section": section, "content": content, "source_url": url,
            "retrieved_at": now(), **extra}


def availability(value):
    """공단이 명시한 자료없음만 결측으로 분류하고 원문은 보존한다."""
    return "not_available" if re.fullmatch(r"자료\s*없음[.。]*", value.strip()) else "available"


async def collect_kosha(session, key, cas):
    root = await fetch_xml(session, "getChemList001", {"serviceKey": key, "searchWrd": cas,
                           "searchCnd": 1, "numOfRows": 100, "pageNo": 1})
    candidates = []
    for node in root.iter():
        ident = (node.findtext("chemId") or "").strip()
        match_cas = (node.findtext("casNo") or "").strip()
        if ident and match_cas == cas:
            candidates.append((ident, (node.findtext("chemNameKor") or "").strip()))
    candidates = list(dict.fromkeys(candidates))
    if len(candidates) != 1:
        raise ValueError(f"{cas}: CAS 정확히 일치하는 물질 {len(candidates)}건; 선택 확인 필요")
    ident, name = candidates[0]
    records, statuses = [], {}
    for number, title in SECTIONS.items():
        endpoint = f"getChemDetail{number:02}1"
        try:
            detail = await fetch_xml(session, endpoint, {"serviceKey": key, "chemId": ident})
            items = []
            for node in detail.iter():
                label = (node.findtext("msdsItemNameKor") or "").strip()
                value = (node.findtext("itemDetail") or "").strip()
                if value:
                    items.append({"label": label, "value": value,
                                  "level": (node.findtext("lev") or "").strip(),
                                  "item_code": (node.findtext("msdsItemCode") or "").strip(),
                                  "parent_code": (node.findtext("upMsdsItemCode") or "").strip()})
            missing_count = sum(availability(item["value"]) == "not_available" for item in items)
            statuses[str(number)] = {"status": "ok" if items else "empty", "count": len(items),
                                     "not_available_count": missing_count}
            for item in items:
                records.append(record(cas, "KOSHA", title, item["value"],
                    "https://msds.kosha.or.kr/MSDSInfo/kcic/msdssearchMsds.do",
                    chem_id=ident, api_name=name, endpoint=endpoint,
                    availability=availability(item["value"]), **{k:v for k,v in item.items() if k != "value"}))
        except (RuntimeError, aiohttp.ClientError, asyncio.TimeoutError):
            statuses[str(number)] = {"status": "error", "count": 0}
    return records, statuses


def collect_pdf(reader, cas, source_file="NIOSH.pdf"):
    from .niosh_pdf import extract_material, reference_pages
    _, page, name = CHEMICALS[cas]
    base = {"source_file": source_file, "document_title": "NIOSH Pocket Guide to Chemical Hazards",
            "document_edition": "September 2007", "language": "en"}
    references = {"First Aid": "28-30", "Personal Protection/Sanitation": "18-19",
                  "Respirator Recommendations": "20-25",
                  "Exposure Routes, Symptoms, Target Organs": "26-27"}
    records = [record(cas, "NIOSH PDF", section, content, "", pdf_page=page,
                      reference_pdf_pages=references.get(section, ""), **base)
               for section, content in extract_material(reader, cas, page, name)]
    for page_number, section, content in reference_pages(reader):
        records.append(record(cas, "NIOSH PDF", section, content, "", pdf_page=page_number,
                              record_type="reference", **base))
    return records


async def collect(args):
    from .niosh_pdf import open_pdf
    reader = open_pdf(args.pdf)
    path = Path(args.output)
    if path.exists():
        raise ValueError(f"기존 파일 보존을 위해 중단: {path}")
    cached = None
    if args.reuse_kosha:
        cached = json.loads(Path(args.reuse_kosha).read_text(encoding="utf-8"))
    key = None if cached is not None else get_key()
    all_data = {"schema_version": 2, "records": [], "status": {}}
    async with aiohttp.ClientSession() as session:
        for cas in args.cas:
            status = {}
            if cached is not None:
                kosha = [r for r in cached["records"] if r.get("source") == "KOSHA" and r.get("cas_no") == cas]
                if not kosha:
                    raise ValueError(f"기존 JSON에 {cas} 공단 자료가 없습니다.")
                status["kosha"] = cached.get("status", {}).get(cas, {}).get("kosha", {"status": "reused", "count": len(kosha)})
            else:
                try:
                    kosha, status["kosha"] = await collect_kosha(session, key, cas)
                except (ValueError, RuntimeError, aiohttp.ClientError, asyncio.TimeoutError) as exc:
                    raise ValueError(f"{cas} 공단 수집 실패: {exc}") from exc
            pdf_records = collect_pdf(reader, cas, Path(args.pdf).name)
            all_data["records"].extend(kosha + pdf_records)
            status["niosh_pdf"] = {"status": "ok", "count": len(pdf_records), "pdf_page": CHEMICALS[cas][1]}
            all_data["status"][cas] = status
            print(f"{CHEMICALS[cas][0]} ({cas}): {status}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    print(f"저장: {path} / 문서 {len(all_data['records'])}개")


def embeddings():
    from langchain_huggingface import HuggingFaceEmbeddings
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL,
                                encode_kwargs={"normalize_embeddings": True})


def load_index(path):
    from langchain_community.vectorstores import FAISS
    from langchain_community.vectorstores.utils import DistanceStrategy
    config_path = Path(path) / "config.json"
    if not config_path.exists() or json.loads(config_path.read_text(encoding="utf-8")) != INDEX_CONFIG:
        raise ValueError("인덱스 설정이 BGE-M3 코사인 설정과 다릅니다. 새 인덱스를 생성하세요.")
    # pickle을 포함하므로 본인이 생성한 신뢰할 수 있는 인덱스만 로드한다.
    return FAISS.load_local(path, embeddings(), allow_dangerous_deserialization=True,
                            distance_strategy=DistanceStrategy.MAX_INNER_PRODUCT)


def index(args):
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_community.vectorstores import FAISS
    from langchain_community.vectorstores.utils import DistanceStrategy
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    texts, metadata = [], []
    for item in data["records"]:
        if item.get("source") == "CDC/NIOSH":
            raise ValueError("기존 NIOSH 웹 자료가 포함되어 있습니다. PDF 자료로 다시 수집하세요.")
        if item.get("source") == "NIOSH PDF" and args.kosha_only:
            continue
        if not item.get("content", "").strip():
            continue
        texts.append(f"물질명: {item['chemical_name']}\nCAS: {item['cas_no']}\n출처: {item['source']}\n항목: {item['section']}\n세부항목: {item.get('label', '')}\n자료 상태: {item.get('availability', 'available')}\n내용: {item['content']}")
        metadata.append({k: v for k, v in item.items() if k != "content" and v is not None})
    if not texts:
        raise ValueError("적재할 문서가 없습니다.")
    path = Path(args.output)
    if path.exists():
        raise ValueError(f"기존 인덱스 보존을 위해 중단: {path}")
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    docs = splitter.create_documents(texts, metadatas=metadata)
    store = FAISS.from_documents(docs, embeddings(),
                                 distance_strategy=DistanceStrategy.MAX_INNER_PRODUCT)
    store.save_local(str(path))
    (path / "config.json").write_text(json.dumps(INDEX_CONFIG, ensure_ascii=False, indent=2), encoding="utf-8")
    sources = sorted({doc.metadata.get("source", "알 수 없음") for doc in docs})
    print(f"{len(docs)}개 청크 저장: {path} / 출처: {', '.join(sources)}")


def is_incompatibility_question(question):
    """반응 금기 질문의 자주 쓰이는 표현을 보수적으로 감지한다."""
    text = re.sub(r"\s+", "", question.lower())
    direct = ("반응금기", "혼합금지", "혼합하면안", "섞으면안", "섞어도되",
              "섞어쓰", "피해야할물질", "같이보관", "함께보관", "같이두", "함께두",
              "옆에놓", "인접보관", "incompatib")
    return any(term in text for term in direct) or ("옆에" in text and "놓" in text) or (
        any(term in text for term in ("혼합", "섞", "반응", "같이", "함께"))
        and any(term in text for term in ("위험", "금지", "주의", "안되", "안돼", "물질"))
    )


def search_evidence(store, cas_no, question, top_k=5, pdf_path=PDF_PATH, intent=None):
    """CAS별 검색 결과와 해당 청크에 실제로 등장한 공식 코드 설명을 반환한다.

    store는 load_index()로 미리 로드해서 여러 요청에 재사용할 수 있다.
    코드 설명은 각 결과에 포함되며 top_k 개수에 포함되지 않는다.
    intent='incompatibility'로 반응 금기 검색을 명시할 수 있다.
    """
    if cas_no not in CHEMICALS:
        raise ValueError("지원하지 않는 CAS 번호입니다.")
    if not question.strip() or not isinstance(top_k, int) or isinstance(top_k, bool) or top_k < 1:
        raise ValueError("질문과 1 이상의 top_k가 필요합니다.")
    if intent not in (None, "incompatibility"):
        raise ValueError("지원하지 않는 검색 의도입니다.")
    vector = store.embeddings.embed_query(question)
    def search_filtered(predicate, count):
        return store.similarity_search_with_score_by_vector(
            vector, k=count, fetch_k=max(10000, top_k),
            filter=lambda meta: meta.get("cas_no") == cas_no
            and meta.get("record_type") != "reference" and predicate(meta))

    hits = search_filtered(lambda meta: True, top_k)
    targeted = []
    if intent == "incompatibility" or (intent is None and is_incompatibility_question(question)):
        def is_target(meta):
            return meta.get("availability", "available") == "available" and (
                (meta.get("source") == "NIOSH PDF" and meta.get("section") == "Incompatibilities and Reactivities")
                or (meta.get("source") == "KOSHA" and meta.get("section") == "안정성 및 반응성"
                    and re.sub(r"\s+", "", meta.get("label", "")) == "피해야할물질"))
        targeted = search_filtered(is_target, top_k)
        # 명시적 항목을 우선하고, 나머지 자리는 기존 유사도 검색으로 채운다.
        combined, seen = [], set()
        for doc, score in targeted + hits:
            key = (doc.page_content, json.dumps(doc.metadata, sort_keys=True, ensure_ascii=False))
            if key not in seen:
                seen.add(key)
                combined.append((doc, score))
            if len(combined) == top_k:
                break
        hits = combined
    catalog = None
    results = []
    for doc, score in hits:
        metadata = dict(doc.metadata)
        explanations, unknown = [], []
        if metadata.get("source") == "NIOSH PDF" and metadata.get("reference_pdf_pages"):
            if catalog is None:
                from .niosh_codes import glossary
                catalog = glossary(pdf_path)
            from .niosh_codes import related_codes
            explanations, unknown = related_codes(metadata.get("section", ""), doc.page_content, catalog)
        is_targeted = any(doc.page_content == target.page_content and doc.metadata == target.metadata
                          for target, _ in targeted)
        results.append({"content": doc.page_content, "score": float(score), "metadata": metadata,
                        "selection_reason": "incompatibility_section" if is_targeted else "similarity",
                        "code_explanations": explanations, "unmatched_codes": unknown})
    return results


def search(args):
    hits = search_evidence(load_index(args.index), args.cas, args.question, args.top_k, args.pdf, args.intent)
    for hit in hits:
        meta = hit["metadata"]
        location = meta.get("source_url") or f"{meta.get('source_file', '')} PDF {meta.get('pdf_page', '?')}쪽"
        print(f"\n코사인 유사도: {hit['score']:.4f} | {meta.get('source')} | {location}")
        if hit["selection_reason"] == "incompatibility_section":
            print("선택 이유: 반응 금기 관련 항목")
        print(hit["content"])
        for code in hit["code_explanations"]:
            print(f"  코드 설명 [{code['code']}] (PDF {code['pdf_page']}쪽): {code['description']}")
        for code in hit["unmatched_codes"]:
            print(f"  미확인: {code}")
    if not hits:
        print("해당 물질의 검색 결과가 없습니다.")


def answer(args):
    """검색된 원문을 근거로 한국어 답변을 생성한다."""
    from langchain_openai import ChatOpenAI
    load_dotenv(ROOT / ".env")
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY가 필요합니다.")
    store = load_index(args.index)
    hits = search_evidence(store, args.cas, args.question, args.top_k, args.pdf, args.intent)
    if not hits:
        print("해당 물질의 검색 근거가 없어 답변을 생성하지 않습니다.")
        return
    evidence = "\n\n".join(
        f"[근거 {i}] 출처: {hit['metadata'].get('source', '')} | "
        f"항목: {hit['metadata'].get('section', '')} | URL: {hit['metadata'].get('source_url', '')} | "
        f"PDF: {hit['metadata'].get('source_file', '')} {hit['metadata'].get('pdf_page', '')}쪽\n"
        f"{hit['content']}\n공식 코드 설명: "
        + json.dumps(hit['code_explanations'], ensure_ascii=False)
        + "\n미확인 코드: " + json.dumps(hit['unmatched_codes'], ensure_ascii=False)
        for i, hit in enumerate(hits, 1)
    )
    prompt = (
        "당신은 화학물질 안전자료 검색 도우미입니다. 아래 제공된 근거만 사용해 한국어로 답하세요. "
        "영문 자료는 원래 의미를 바꾸지 않도록 번역하거나 요약하세요. "
        "물질명과 CAS 번호, 농도, 단위, 노출기준 종류와 적용 조건을 보존하고, "
        "자료 상태가 not_available이거나 내용이 자료없음이면 위험이 없다는 뜻이 아니라 "
        "해당 출처에 자료가 없다는 뜻입니다. 근거가 부족하면 없다고 말하세요. "
        "서로 다른 출처의 차이를 임의로 합치지 말고, 약어 설명이 근거에 없으면 추측하지 마세요. "
        "답변의 각 주장 옆에 [근거 번호]를 표시하고 링크나 사실을 만들지 마세요. "
        "실제 작업에서는 해당 제품의 공급자 SDS와 현장 안전관리 기준을 확인하도록 안내하세요.\n\n"
        f"질문: {args.question}\n선택된 CAS: {args.cas}\n\n{evidence}"
    )
    result = ChatOpenAI(model=args.model, temperature=0).invoke(prompt)
    print(result.content)
    print("\n검색 근거:")
    for i, hit in enumerate(hits, 1):
        meta = hit['metadata']
        location = meta.get('source_url') or f"{meta.get('source_file', '')} PDF {meta.get('pdf_page', '?')}쪽"
        print(f"[{i}] {meta.get('source', '')} | {meta.get('section', '')} | {location}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("collect")
    p.add_argument("--cas", nargs="+", choices=CHEMICALS, default=list(CHEMICALS))
    p.add_argument("--output", required=True, help="새 JSON 파일 경로")
    p.add_argument("--pdf", default=str(PDF_PATH), help="NIOSH 원본 PDF 경로")
    p.add_argument("--reuse-kosha", help="기존 JSON에서 KOSHA 자료만 재사용")
    p = sub.add_parser("index")
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True, help="새 FAISS 디렉터리")
    p.add_argument("--kosha-only", action="store_true", help="공단 자료만 적재")
    p = sub.add_parser("search")
    p.add_argument("--index", required=True)
    p.add_argument("--cas", required=True, choices=CHEMICALS)
    p.add_argument("--question", required=True)
    p.add_argument("--top-k", type=int, default=5)
    p.add_argument("--intent", choices=["incompatibility"], help="검색 의도를 명시적으로 지정")
    p.add_argument("--pdf", default=str(PDF_PATH))
    p = sub.add_parser("answer")
    p.add_argument("--index", required=True)
    p.add_argument("--cas", required=True, choices=CHEMICALS)
    p.add_argument("--question", required=True)
    p.add_argument("--model", default="gpt-4o-mini", help="사용할 OpenAI 모델")
    p.add_argument("--top-k", type=int, default=5)
    p.add_argument("--intent", choices=["incompatibility"], help="검색 의도를 명시적으로 지정")
    p.add_argument("--pdf", default=str(PDF_PATH))
    args = parser.parse_args()
    try:
        if args.command == "collect":
            asyncio.run(collect(args))
        elif args.command == "index":
            index(args)
        elif args.command == "search":
            search(args)
        else:
            answer(args)
    except (ValueError, RuntimeError, FileExistsError, ModuleNotFoundError) as exc:
        print(f"작업 중단: {exc}")
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
