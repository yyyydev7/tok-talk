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

    def test_index_config_must_match(self):
        with TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                validate_index(Path(directory))


if __name__ == "__main__":
    unittest.main()
