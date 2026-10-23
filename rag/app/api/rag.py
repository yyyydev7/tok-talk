"""Authenticated RAG endpoints consumed directly by the Vue client."""

import re
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.security.jwt import verify_access_token
from app.services.rag import MATERIALS, RagService

router = APIRouter(tags=["rag"], dependencies=[Depends(verify_access_token)])

ALIASES = {
    "acetone": ["Acetone"],
    "ethanol": ["Ethanol", "Ethyl alcohol"],
    "methanol": ["Methanol", "Methyl alcohol"],
    "toluene": ["Toluene"],
    "acetic_acid": ["Acetic acid"],
}


class Question(BaseModel):
    question: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=10, strict=True)

    @field_validator("question")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("질문을 입력해 주세요.")
        return value.strip()


class SelectedQuestion(Question):
    material_id: str


@lru_cache(maxsize=1)
def get_service() -> RagService:
    return RagService.from_environment()


def _loaded_materials(service: RagService) -> set[str]:
    """Expose only materials with NIOSH PDF chunks in the loaded index."""
    store = service.store
    loaded = set()
    for doc_id in store.index_to_docstore_id.values():
        doc = store.docstore.search(doc_id)
        if not hasattr(doc, "metadata") or doc.metadata.get("source") != "NIOSH PDF":
            continue
        for material_id, (_, cas) in MATERIALS.items():
            if doc.metadata.get("cas_no") == cas:
                loaded.add(material_id)
    return loaded


def _service() -> RagService:
    try:
        return get_service()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="RAG 인덱스를 사용할 수 없습니다.") from exc


def _candidate(material_id: str) -> dict[str, str]:
    return {"material_id": material_id, "name": MATERIALS[material_id][0]}


def _matches(text: str, loaded: set[str]) -> list[str]:
    lowered = text.casefold()
    found = []
    for material_id in MATERIALS:
        if material_id not in loaded:
            continue
        name, cas = MATERIALS[material_id]
        terms = (name, cas, *ALIASES[material_id])
        if any(
            term.casefold() in lowered if re.search(r"[가-힣]", term)
            else re.search(rf"(?<![a-z]){re.escape(term.casefold())}(?![a-z])", lowered)
            for term in terms
        ):
            found.append(material_id)
    return found


def _unresolved(status: str, matches: list[str]) -> dict:
    return {
        "answer": ("질문에서 여러 물질이 확인되었습니다. 물질을 선택해 다시 질문해 주세요."
                   if status == "ambiguous" else
                   "질문에서 물질을 찾지 못했습니다. 물질명을 포함해 다시 질문해 주세요."),
        "sources": [], "needs_review": True, "material": None,
        "resolution": {"status": status,
                       "candidates": [_candidate(material_id) for material_id in matches]},
    }


def _answer(service: RagService, material_id: str, question: str, top_k: int) -> dict:
    try:
        return service.answer(material_id, question, top_k)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        # Do not expose API keys, provider errors, or prompt contents to clients.
        raise HTTPException(status_code=503, detail="RAG 답변 서비스를 사용할 수 없습니다.") from exc


@router.get("/chemicals")
def chemicals(query: str = "", service: RagService = Depends(_service)) -> dict:
    loaded = _loaded_materials(service)
    items = []
    for material_id in MATERIALS:
        if material_id not in loaded:
            continue
        name, cas = MATERIALS[material_id]
        if query and not _matches(query, {material_id}):
            continue
        items.append({"material_id": material_id, "name": name,
                      "aliases": ALIASES[material_id], "cas_number": cas,
                      "source_title": "NIOSH Pocket Guide to Chemical Hazards"})
    return {"items": items}


@router.post("/rag-query")
def rag_query(body: SelectedQuestion, service: RagService = Depends(_service)) -> dict:
    if body.material_id not in _loaded_materials(service):
        raise HTTPException(status_code=422, detail="등록되지 않은 material_id입니다.")
    return _answer(service, body.material_id, body.question, body.top_k)


@router.post("/rag-query/auto")
def rag_query_auto(body: Question, service: RagService = Depends(_service)) -> dict:
    matches = _matches(body.question, _loaded_materials(service))
    if not matches:
        return _unresolved("not_found", matches)
    if len(matches) > 1:
        return _unresolved("ambiguous", matches)
    return _answer(service, matches[0], body.question, body.top_k)
