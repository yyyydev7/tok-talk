import unittest
from unittest.mock import patch
from xml.etree import ElementTree

from . import pipeline


class PipelineTest(unittest.IsolatedAsyncioTestCase):
    def test_chunking_preserves_record_context_and_skips_unavailable(self):
        records = [
            {"chemical_name": "아세톤", "cas_no": "67-64-1", "source": "KOSHA",
             "section": "취급 및 저장방법", "label": "안전한 저장방법",
             "availability": "available", "content": "환기가 잘 되는 곳에 보관하시오."},
            {"chemical_name": "아세톤", "cas_no": "67-64-1", "source": "KOSHA",
             "section": "독성에 관한 정보", "label": "기타", "availability": "not_available",
             "content": "자료없음"},
            {"chemical_name": "아세톤", "cas_no": "67-64-1", "source": "NIOSH PDF",
             "section": "Exposure and symptoms abbreviations", "pdf_page": 26,
             "content": "code description " * 120 + "con Skin and/or eye contact"},
        ]
        chunks = pipeline.chunk_records({"records": records})
        self.assertTrue(any(doc.metadata["label"] == "안전한 저장방법" for doc in chunks))
        self.assertFalse(any(doc.metadata.get("availability") == "not_available" for doc in chunks))
        for doc in chunks:
            self.assertIn("CAS: 67-64-1", doc.page_content)
            self.assertIn("내용: ", doc.page_content)
            self.assertGreater(len(doc.page_content.split("내용: ", 1)[1]), 0)
            self.assertLessEqual(len(doc.page_content), 1000)
        self.assertTrue(any("con Skin and/or eye contact" in doc.page_content for doc in chunks))

    def test_supported_niosh_abbreviations_keep_code_with_definition(self):
        from .niosh_codes import glossary
        from .niosh_pdf import open_pdf

        records = pipeline.collect_pdf(open_pdf(pipeline.PDF_PATH), "67-64-1")
        docs = pipeline.chunk_records({"records": records})
        pages = [doc.page_content.casefold() for doc in docs
                 if doc.metadata["section"] == "Exposure and symptoms abbreviations"]
        abbreviations = glossary(pipeline.PDF_PATH)[1]
        self.assertGreater(len(abbreviations), 20)
        for code, (meaning, _page) in abbreviations.items():
            with self.subTest(code=code):
                self.assertTrue(any(f"{code} {meaning}".casefold() in text for text in pages))

    def test_pdf_extracts_five_materials_without_neighboring_tables(self):
        from .niosh_pdf import extract_material, open_pdf, reference_pages
        reader = open_pdf(pipeline.PDF_PATH)
        for cas, (_, page, name) in pipeline.CHEMICALS.items():
            sections = dict(extract_material(reader, cas, page, name))
            self.assertIn(cas, sections["Identification"])
            self.assertIn("First Aid", sections)
            self.assertIn("Incompatibilities and Reactivities", sections)
        acetone = dict(extract_material(reader, "67-64-1", 33, "Acetone"))
        self.assertIn("590 mg/m3", acetone["Exposure Limits"])
        self.assertNotIn("Acetic anhydride", str(acetone))
        methanol = dict(extract_material(reader, "67-56-1", 230, "Methyl alcohol"))
        self.assertNotIn("Methylamine", str(methanol))
        self.assertEqual({n for n, _, _ in reference_pages(reader)}, set(range(18, 31)))
        with self.assertRaises(ValueError):
            extract_material(reader, "67-56-1", 33, "Acetone")

    def test_search_returns_only_matching_aid_codes_with_original_page(self):
        from langchain_core.documents import Document
        class FakeStore:
            class Embeddings:
                def embed_query(self, question):
                    return [0.0]
            embeddings = Embeddings()
            def similarity_search_with_score_by_vector(self, vector, k, fetch_k, filter):
                docs = [
                    Document(page_content="Eye: Irr immed Skin: Soap wash immed Breath: Resp support Swallow: Medical attention immed",
                             metadata={"cas_no": "67-64-1", "source": "NIOSH PDF", "section": "First Aid", "pdf_page": 33, "reference_pdf_pages": "28-30"}),
                    Document(page_content="other", metadata={"cas_no": "67-56-1", "source": "KOSHA"}),
                    Document(page_content="reference", metadata={"cas_no": "67-64-1", "record_type": "reference"}),
                ]
                return [(d, 0.8) for d in docs if filter(d.metadata)][:k]
        hits = pipeline.search_evidence(FakeStore(), "67-64-1", "응급조치", top_k=1)
        self.assertEqual(len(hits), 1)
        explanations = {e['code']: e for e in hits[0]['code_explanations']}
        self.assertEqual(set(explanations), {"Eye: Irr immed", "Skin: Soap wash immed", "Breath: Resp support", "Swallow: Medical attention immed"})
        self.assertEqual(explanations['Eye: Irr immed']['pdf_page'], 28)
        self.assertIn('medical attention immediately', explanations['Eye: Irr immed']['description'])
        self.assertEqual(hits[0]['unmatched_codes'], [])

    def test_unknown_codes_are_not_guessed(self):
        from .niosh_codes import glossary, related_codes
        found, unknown = related_codes('First Aid', 'Eye: UNKNOWN CODE', glossary(pipeline.PDF_PATH))
        self.assertEqual(found, [])
        self.assertEqual(unknown, ['Eye: UNKNOWN CODE'])

    async def test_kosha_missing_values_are_preserved_and_counted(self):
        async def fake_fetch(session, endpoint, params):
            if endpoint == "getChemList001":
                return ElementTree.fromstring("<root><item><chemId>1</chemId><chemNameKor>아세톤</chemNameKor><casNo>67-64-1</casNo></item></root>")
            return ElementTree.fromstring("<root><item><msdsItemNameKor>피해야 할 물질</msdsItemNameKor><itemDetail>자료없음</itemDetail></item><item><msdsItemNameKor>조건</msdsItemNameKor><itemDetail>원문 설명</itemDetail></item></root>")

        with patch.object(pipeline, "fetch_xml", fake_fetch):
            records, status = await pipeline.collect_kosha(None, "test", "67-64-1")
        self.assertEqual(status["10"]["not_available_count"], 1)
        missing = next(r for r in records if r["section"] == "안정성 및 반응성" and r["label"] == "피해야 할 물질")
        self.assertEqual((missing["content"], missing["availability"]), ("자료없음", "not_available"))
        self.assertEqual(pipeline.availability("자료없음으로 추정"), "available")


if __name__ == "__main__":
    unittest.main()
