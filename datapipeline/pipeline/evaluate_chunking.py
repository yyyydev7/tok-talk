"""Compare two trusted local FAISS builds with fixed evidence questions.

Run: python -m pipeline.evaluate_chunking --before PATH --after PATH --output report.md
"""

import argparse
import json
from collections import Counter
from pathlib import Path

from .pipeline import INDEX_CONFIG, embeddings


QUESTIONS = (
    ("아세톤 노출 경로", "67-64-1", "아세톤의 흡입 섭취 피부 눈 노출 경로", "Exposure Routes, Symptoms, Target Organs"),
    ("아세톤 약어 Con", "67-64-1", "Con은 피부 및 눈 접촉인가", "Exposure and symptoms abbreviations"),
    ("아세톤 보관", "67-64-1", "아세톤의 안전한 보관 방법", "취급 및 저장방법"),
    ("메탄올 보호구", "67-56-1", "메탄올 취급 시 필요한 개인보호구", "노출방지 및 개인보호구"),
    ("메탄올 응급조치", "67-56-1", "메탄올 피부 눈 접촉 응급조치", "응급조치요령"),
    ("톨루엔 건강 영향", "108-88-3", "톨루엔의 주요 건강 영향 증상", "독성에 관한 정보"),
    ("톨루엔 노출 감소", "108-88-3", "톨루엔 노출을 줄이는 공정 격리 국소배기", "노출방지 및 개인보호구"),
    ("에탄올 소화제", "64-17-5", "에탄올 화재 발생 시 적절한 소화제", "폭발·화재시 대처방법"),
    ("아세트산 피부 증상", "64-19-7", "아세트산 피부 접촉 화상 증상", "유해성·위험성"),
)


def inspect(path: Path, embedder) -> dict:
    from langchain_community.vectorstores import FAISS
    from langchain_community.vectorstores.utils import DistanceStrategy

    if json.loads((path / "config.json").read_text()) != INDEX_CONFIG:
        raise ValueError(f"인덱스 설정이 다릅니다: {path}")
    store = FAISS.load_local(str(path), embedder, allow_dangerous_deserialization=True,
                            distance_strategy=DistanceStrategy.MAX_INNER_PRODUCT)
    docs = [store.docstore.search(doc_id) for doc_id in store.index_to_docstore_id.values()]
    counts = Counter(doc.metadata.get("source") for doc in docs)
    audit = {
        "chunks": len(docs),
        "by_source": dict(counts),
        "not_available": sum(doc.metadata.get("availability") == "not_available" for doc in docs),
        "header_only": sum(("물질명:" in doc.page_content and "내용:" not in doc.page_content)
                           or ("내용:" in doc.page_content and
                               not doc.page_content.split("내용:", 1)[1].strip()) for doc in docs),
        "no_cas_in_text": sum("CAS:" not in doc.page_content for doc in docs),
        "reference_chunks": sum(doc.metadata.get("record_type") == "reference" for doc in docs),
    }
    results = []
    for title, cas, question, expected in QUESTIONS:
        is_glossary = title == "아세톤 약어 Con"
        def relevant(meta):
            return (meta.get("cas_no") == cas and
                    (meta.get("section") == expected if is_glossary else
                     meta.get("record_type") != "reference") and
                    meta.get("availability", "available") == "available")
        hits = store.similarity_search_with_score(question, k=5, fetch_k=10000,
                                                  filter=relevant)
        sections = [doc.metadata.get("section", "") for doc, _score in hits]
        results.append({"title": title, "expected_section": expected,
                        "first_rank": next((i for i, section in enumerate(sections, 1)
                                            if section == expected), None),
                        "sections": sections})
    return {"path": str(path.resolve()), "audit": audit, "questions": results}


def report(before: dict, after: dict) -> str:
    lines = ["# 청킹 변경 전후 검색 평가", "",
             "같은 BGE-M3 임베딩, 동일 질문·CAS 필터·top-5 기준입니다. 일반 질문은 공통 참고표를 제외하고, 약어 질문만 해당 표를 검색합니다. 출처 항목 적중은 답변의 사실 정확도를 보증하지 않습니다.", "",
             f"- 기존 인덱스: `{before['path']}`",
             f"- 새 인덱스: `{after['path']}`", "",
             "## 청크 품질", "",
             "| 지표 | 변경 전 | 변경 후 |", "| --- | ---: | ---: |"]
    for key, label in (("chunks", "전체 청크"), ("not_available", "자료없음 청크"),
                       ("header_only", "본문 없는 머리글 청크"),
                       ("no_cas_in_text", "본문에 CAS가 없는 청크"),
                       ("reference_chunks", "NIOSH 공통 참고표 청크")):
        lines.append(f"| {label} | {before['audit'][key]} | {after['audit'][key]} |")
    lines += ["", "## 같은 질문의 검색 결과", "",
              "`순위`는 기대 항목이 처음 검색된 위치입니다. `-`는 상위 5개에 없음을 뜻합니다.", "",
              "| 질문 | 기대 항목 | 전 순위 | 후 순위 |", "| --- | --- | ---: | ---: |"]
    for old, new in zip(before["questions"], after["questions"]):
        lines.append(f"| {old['title']} | {old['expected_section']} | "
                     f"{old['first_rank'] or '-'} | {new['first_rank'] or '-'} |")
    old_hits = sum(item["first_rank"] is not None for item in before["questions"])
    new_hits = sum(item["first_rank"] is not None for item in after["questions"])
    lines += ["", f"기대 항목 top-5 적중: **{old_hits}/{len(QUESTIONS)} → {new_hits}/{len(QUESTIONS)}**", "",
              "## 상세 검색 항목", ""]
    for old, new in zip(before["questions"], after["questions"]):
        lines += [f"### {old['title']}", "",
                  f"- 변경 전: {', '.join(old['sections'])}",
                  f"- 변경 후: {', '.join(new['sections'])}", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    embedder = embeddings()
    before = inspect(args.before, embedder)
    after = inspect(args.after, embedder)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report(before, after), encoding="utf-8")
    args.output.with_suffix(".json").write_text(
        json.dumps({"before": before, "after": after}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"보고서 저장: {args.output}")


if __name__ == "__main__":
    main()
