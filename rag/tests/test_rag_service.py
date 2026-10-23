import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from app.services.rag import RagService, validate_index


class FakeStore:
    def __init__(self, hits):
        self.hits = hits
        self.filter = None

    def similarity_search_with_score(self, question, *, k, fetch_k, filter):
        self.filter = filter
        return self.hits[:k]


class FakeLlm:
    def __init__(self, answer):
        self.answer = answer

    def invoke(self, messages):
        return SimpleNamespace(content=self.answer)


def hit(cas="67-64-1", source="CDC/NIOSH"):
    return (SimpleNamespace(page_content="노출 경로: 흡입", metadata={
        "cas_no": cas, "source": source, "chemical_name": "아세톤",
        "section": "Exposure Routes", "source_url": "https://www.cdc.gov/niosh/npg/npgd0004.html",
        "retrieved_at": "2026-10-23T00:54:44+00:00",
    }), 0.8)


class RagServiceTest(unittest.TestCase):
    def test_cas_and_source_are_restricted_and_cited(self):
        store = FakeStore([hit(), hit("67-56-1"), hit(source="KOSHA")])
        result = RagService(store, FakeLlm("흡입 노출 가능 [근거 1]")).answer("acetone", "노출 경로는?")
        self.assertEqual(store.filter, {"cas_no": "67-64-1", "source": "CDC/NIOSH"})
        self.assertFalse(result["needs_review"])
        self.assertEqual(len(result["sources"]), 1)
        self.assertEqual(result["sources"][0]["checked_at"], "2026-10-23")

    def test_missing_or_invalid_citation_needs_review(self):
        for answer in ("근거 없음", "임의 답변 [근거 9]"):
            with self.subTest(answer=answer):
                result = RagService(FakeStore([hit()]), FakeLlm(answer)).answer("acetone", "질문")
                self.assertTrue(result["needs_review"])
                self.assertEqual(result["sources"], [])

    def test_no_evidence_does_not_call_llm(self):
        result = RagService(FakeStore([]), FakeLlm("should not appear")).answer("acetone", "질문")
        self.assertTrue(result["needs_review"])

    def test_index_config_must_match(self):
        with TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                validate_index(Path(directory))


if __name__ == "__main__":
    unittest.main()
