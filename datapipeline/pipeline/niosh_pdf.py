"""2007년 NIOSH 포켓 가이드의 5개 물질 표와 코드표 추출."""
import re
from pathlib import Path

from pypdf import PdfReader


HEADINGS = (
    "Synonyms/Trade Names", "Exposure Limits", "Physical Description", "Measurement Methods",
    "Chemical & Physical Properties", "Personal Protection/Sanitation", "Respirator Recommendations",
    "Incompatibilities and Reactivities", "Exposure Routes, Symptoms, Target Organs", "First Aid",
)
HEADER_PATTERN = re.compile(r"(?m)^([^\n]{1,100}?)\s+Formula:\s*[^\n]*")


def compact(text):
    return re.sub(r"\s+", " ", text).strip()


def extract_material(reader, cas, page_number, name):
    """해당 표의 시작·끝과 CAS를 확인해 다른 물질의 텍스트를 섞지 않는다."""
    if len(reader.pages) != 454:
        raise ValueError("예상한 454쪽 NIOSH PDF가 아닙니다.")
    text = reader.pages[page_number - 1].extract_text() or ""
    pattern = re.compile(r"(?m)^" + re.escape(name) + r"\s+Formula:")
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise ValueError(f"PDF {page_number}쪽에서 {name} 표를 유일하게 찾지 못했습니다.")
    start = matches[0].start()
    next_header = HEADER_PATTERN.search(text, matches[0].end())
    block = text[start:next_header.start() if next_header else len(text)]
    if not re.search(r"CAS#:\s*" + re.escape(cas) + r"(?!\d)", block):
        raise ValueError(f"PDF {page_number}쪽에서 {cas} 확인 실패")
    # 마지막 페이지 번호만 제거하고 나머지 수치와 조건은 그대로 보존한다.
    block = re.sub(r"\n\s*\d+\s*$", "", block)
    head = r"|".join(re.escape(h).replace(r"\ ", r"\s+") for h in HEADINGS)
    markers = list(re.finditer(r"(?m)^\s*(" + head + r")(?:\s*\(see\s+Tables?\s+[^)]*\))?\s*:", block))
    sections = [("Identification", compact(block[:markers[0].start()]))] if markers else []
    for i, match in enumerate(markers):
        end = markers[i + 1].start() if i + 1 < len(markers) else len(block)
        sections.append((compact(match.group(1)), compact(block[match.end():end])))
    sections = [(heading, value) for heading, value in sections if value]
    if not {"Exposure Limits", "First Aid", "Incompatibilities and Reactivities"}.issubset({x[0] for x in sections}):
        raise ValueError(f"PDF {page_number}쪽의 주요 항목 추출 실패")
    return sections


def reference_pages(reader):
    """표가 참조하는 원문 설명을 페이지별로 보존한다.

    별도 문서로 검색 가능하며, 코드가 자동으로 해석되었다는 의미는 아니다.
    """
    titles = {18: "Personal Protection codes", 19: "Personal Protection codes",
              **{n: "Respirator codes" for n in range(20, 26)},
              26: "Exposure and symptoms abbreviations", 27: "Exposure and symptoms abbreviations",
              28: "First Aid codes", 29: "First Aid codes", 30: "First Aid codes"}
    result = []
    for number, title in titles.items():
        text = compact(reader.pages[number - 1].extract_text() or "")
        if not text:
            raise ValueError(f"PDF 설명표 {number}쪽의 텍스트 추출 실패")
        result.append((number, title, text))
    return result


def open_pdf(path):
    path = Path(path)
    if not path.is_file():
        raise ValueError(f"NIOSH PDF 파일이 없습니다: {path}")
    reader = PdfReader(str(path))
    if len(reader.pages) != 454 or "NIOSH POCKET GUIDE" not in (reader.pages[0].extract_text() or "").upper():
        raise ValueError("예상한 454쪽 NIOSH PDF가 아닙니다.")
    return reader
