import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from app.services.rag import RagService, validate_index


class FakeStore:
    def __init__(self, hits):
        self.hits = hits
        self.filters = []

    def similarity_search_with_score(self, question, *, k, fetch_k, filter):
        self.filters.append(filter)
        return self.hits[:k]


class FakeLlm:
    def __init__(self, answer):
        self.answer = answer

    def invoke(self, messages):
        return SimpleNamespace(content=self.answer)


def hit(cas="67-64-1", source="NIOSH PDF"):
    return (SimpleNamespace(page_content="노출 경로: 흡입", metadata={
        "cas_no": cas, "source": source, "chemical_name": "아세톤",
        "section": "Exposure Routes, Symptoms, Target Organs", "source_url": "",
        "source_file": "NIOSH.pdf", "pdf_page": 33,
        "retrieved_at": "2026-10-23T00:54:44+00:00",
    }), 0.8)


def glossary_hit():
    doc, score = hit()
    doc.page_content = "con Skin and/or eye contact"
    doc.metadata["section"] = "Exposure and symptoms abbreviations"
    doc.metadata["pdf_page"] = 26
    return doc, score


def section_hit(section, label, *, cas="67-64-1", content=None):
    doc, score = hit(cas=cas, source="KOSHA")
    doc.metadata.update(section=section, label=label, availability="available")
    doc.page_content = content or f"{section}: {label}"
    return doc, score


class FilteringStore(FakeStore):
    def similarity_search_with_score(self, question, *, k, fetch_k, filter):
        self.filters.append(filter)
        if callable(filter):
            return [(doc, score) for doc, score in self.hits if filter(doc.metadata)][:k]
        return [(doc, score) for doc, score in self.hits
                if all(doc.metadata.get(key) == value for key, value in filter.items())][:k]


class RagServiceTest(unittest.TestCase):
    def test_cas_is_restricted_and_supported_sources_are_cited(self):
        store = FakeStore([hit(), hit("67-56-1"), hit(source="KOSHA")])
        result = RagService(store, FakeLlm("흡입 노출 가능 [근거 1]")).answer("acetone", "노출 경로는?")
        self.assertEqual(store.filters[0], {"cas_no": "67-64-1"})
        self.assertFalse(result["needs_review"])
        self.assertEqual(len(result["sources"]), 1)
        self.assertEqual(result["sources"][0]["checked_at"], "2026-10-23")
        self.assertEqual(result["sources"][0]["pdf_page"], "33")

    def test_kosha_source_is_returned_without_pdf_location(self):
        doc, score = hit(source="KOSHA")
        doc.metadata.update(source_file="", pdf_page="", source_url="https://example.org/msds")
        result = RagService(FakeStore([(doc, score)]), FakeLlm("흡입 노출 가능 [근거 1]")).answer(
            "acetone", "노출 경로는?"
        )
        self.assertFalse(result["needs_review"])
        self.assertEqual(result["sources"][0]["title"], "KOSHA MSDS — 아세톤")
        self.assertEqual(result["sources"][0]["url"], "https://example.org/msds")
        self.assertEqual(result["sources"][0]["pdf_page"], "")

    def test_citations_are_hidden_after_sources_are_validated(self):
        answer = "답변: 흡입 노출 가능 [근거 1][근거 2].\n근거:\n- 흡입 [근거 1]."
        result = RagService(FakeStore([hit(), hit()]), FakeLlm(answer)).answer(
            "acetone", "노출 경로는?", top_k=2
        )
        self.assertEqual(result["answer"], "답변: 흡입 노출 가능.\n근거:\n- 흡입.")
        self.assertEqual(len(result["sources"]), 2)

    def test_missing_or_invalid_citation_needs_review(self):
        for answer in ("근거 없음", "임의 답변 [근거 9]"):
            with self.subTest(answer=answer):
                result = RagService(FakeStore([hit()]), FakeLlm(answer)).answer("acetone", "질문")
                self.assertTrue(result["needs_review"])
                self.assertEqual(result["sources"], [])

    def test_no_evidence_does_not_call_llm(self):
        result = RagService(FakeStore([]), FakeLlm("should not appear")).answer("acetone", "질문")
        self.assertTrue(result["needs_review"])

    def test_exposure_code_requires_eye_and_glossary_citation(self):
        exposure, score = hit()
        exposure.page_content = "ER: Inh, Ing, Con"
        exposure.metadata["section"] = "Exposure Routes, Symptoms, Target Organs"
        store = FakeStore([(exposure, score), glossary_hit()])
        result = RagService(store, FakeLlm("피부 접촉입니다. [근거 1]")).answer(
            "acetone", "노출 경로는?", top_k=2
        )
        self.assertTrue(result["needs_review"])

    def test_correct_exposure_expansion_keeps_glossary_source_without_model_citation(self):
        exposure, score = hit()
        exposure.page_content = "ER: Inh, Ing, Con"
        store = FakeStore([(exposure, score), glossary_hit()])
        answer = "답변: 흡입, 섭취, 피부 및 눈 접촉입니다. [근거 1]"
        result = RagService(store, FakeLlm(answer)).answer("acetone", "노출 경로는?", top_k=2)
        self.assertFalse(result["needs_review"])
        self.assertEqual([item["section"] for item in result["sources"]],
                         ["Exposure Routes, Symptoms, Target Organs",
                          "Exposure and symptoms abbreviations"])

    def test_compound_question_retrieves_both_requested_sections(self):
        routes = hit()
        routes[0].page_content = "ER: Inh, Ing, Con"
        storage = section_hit("취급 및 저장방법", "안전한 저장방법", content="환기와 밀폐")
        noise = section_hit("누출사고시 대처방법", "보호장비", content="누출 조치")
        store = FilteringStore([noise, routes, storage, glossary_hit()])
        evidence = RagService(store).search("acetone", "아세톤의 노출 경로와 보관 방법은?", top_k=5)
        sections = {item.source["section"] for item in evidence}
        self.assertIn("Exposure Routes, Symptoms, Target Organs", sections)
        self.assertIn("취급 및 저장방법", sections)
        self.assertIn("Exposure and symptoms abbreviations", sections)
        self.assertNotIn("누출사고시 대처방법", sections)

    def test_first_aid_does_not_take_spill_response(self):
        ppe = section_hit("노출방지 및 개인보호구", "손 보호")
        first_aid = section_hit("응급조치요령", "피부에 접촉했을 때")
        spill = section_hit("누출사고시 대처방법", "보호장비")
        evidence = RagService(FilteringStore([spill, ppe, first_aid])).search(
            "acetone", "개인보호구와 응급조치 방법은?", top_k=5)
        self.assertEqual({item.source["section"] for item in evidence},
                         {"노출방지 및 개인보호구", "응급조치요령"})

    def test_missing_compound_topic_blocks_llm(self):
        store = FilteringStore([section_hit("취급 및 저장방법", "안전한 저장방법")])
        result = RagService(store, FakeLlm("임의 답변 [근거 1]")).answer(
            "acetone", "노출 경로와 보관 방법은?")
        self.assertTrue(result["needs_review"])
        self.assertIn("노출 경로", result["answer"])
        self.assertEqual(result["sources"], [])

    def test_index_config_must_match(self):
        with TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                validate_index(Path(directory))


if __name__ == "__main__":
    unittest.main()
