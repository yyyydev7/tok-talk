"""NIOSH 2007 PDF 코드표와 물질 원문을 정확히 매칭한다."""
import re

from .niosh_pdf import compact, open_pdf

# PDF 26~27쪽에서 직접 확인한 다섯 물질의 약어만 사용한다.
SUPPORTED_ABBREVIATIONS = set("abs anxi bron cns con conf conj depres derm dist dizz drow euph ftg gi head ing inh insom irrit lac lass musc narco nau pares phar repro resp sens sys terato vis vomit".split())


def row(text, code, end_codes):
    """PDF 표의 특정 코드 행을 다음 행 앞까지 추출한다."""
    start = re.search(r"(?m)^\s*" + r"\s+".join(map(re.escape, code.split())) + r"\s+", text)
    if not start:
        raise ValueError(f"설명표에서 {code} 행을 찾지 못했습니다")
    end_pattern = r"(?m)^\s*(?:" + "|".join(r"\s+".join(map(re.escape, x.split())) for x in end_codes) + r")\s+"
    end = re.search(end_pattern, text[start.end():]) if end_codes else None
    return compact(text[start.end():start.end() + end.start()] if end else text[start.end():])


def glossary(pdf_path):
    reader = open_pdf(pdf_path)
    pages = {n: reader.pages[n - 1].extract_text() or "" for n in range(18, 31)}
    first_aid = {}
    rows = [
        ("Eye", "Irr immed", 28, ["Irr prompt"]),
        ("Skin", "Soap wash immed", 29, ["Soap wash prompt"]),
        ("Skin", "Soap wash prompt", 29, ["Water flush"]),
        ("Skin", "Water flush immed", 29, ["Water flush prompt"]),
        ("Skin", "Water flush prompt", 29, ["Water wash"]),
        ("Breath", "Resp support", 30, ["Fresh air"]),
        ("Breath", "Fresh air", 30, ["Fresh air; 100% O2"]),
        ("Swallow", "Medical attention immed", 30, []),
    ]
    for field, code, page, stops in rows:
        first_aid[(field, code.casefold())] = (row(pages[page], code, stops), page)

    abbreviations = {}
    for page in (26, 27):
        for line in pages[page].splitlines():
            for cell in re.split(r" {2,}", line.strip()):
                match = re.match(r"^(\[carc\]|muc memb|peri neur|[A-Za-z]+)\s+(.+)$", cell.strip(), re.IGNORECASE)
                if match and match.group(1).casefold() in SUPPORTED_ABBREVIATIONS:
                    abbreviations[match.group(1).casefold()] = (compact(match.group(2)), page)

    respirators = {}
    for page in range(21, 25):
        text = pages[page]
        # 코드 행은 줄 시작에 코드와 APF가 있으며, ScbaE는 APF가 비어 있다.
        pattern = re.compile(r"(?m)^\s*((?:\d{2,3}[A-Za-z]+|[A-Z][A-Za-z0-9:,]+))\s+(?:(\d[\d,]*)\s+)?(Any\b)")
        matches = list(pattern.finditer(text))
        for i, m in enumerate(matches):
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            respirators[m.group(1)] = (compact(text[m.start(3):end]), page)
    symbols = {}
    text = pages[20]
    for symbol in ('§', '*', '£', '¥'):
        match = re.search(r"(?m)^\s*" + re.escape(symbol) + r"\s+([^\n]*(?:\n(?!\s*[§*£¥¿†]|\s*APF)[^\n]+)?)", text)
        if match:
            symbols[symbol] = (compact(match.group(1)), 20)
    protection = {}
    protection_rows = [
        ("Skin", "Prevent skin contact", 18, "Skin: Prevent skin contact", ["Frostbite"]),
        ("Eyes", "Prevent eye contact", 18, "Eyes: Prevent eye contact", ["Frostbite"]),
        ("Wash skin", "When contam", 18, "skin: When contam", ["Daily"]),
        ("Remove", "When wet or contam", 18, "Remove: When wet or contam", ["When wet (flamm)"]),
        ("Remove", "When wet (flamm)", 18, "When wet (flamm)", ["N.R."]),
        ("Change", "N.R.", 19, "N.R.", ["Provide: Eyewash"]),
        ("Provide", "Eyewash", 19, "Provide: Eyewash", ["Quick drench"]),
        ("Provide", "Quick drench", 19, "Quick drench", ["Frostbite wash"]),
    ]
    for field, code, page, label, stops in protection_rows:
        protection[(field, code.casefold())] = (row(pages[page], label, stops), page)
    return first_aid, abbreviations, respirators, symbols, protection


def related_codes(section, content, catalog):
    first_aid, abbreviations, respirators, symbols, protection = catalog
    matched, unknown = [], []

    def add(code, value, category):
        if value:
            description, page = value
            matched.append({"code": code, "description": description, "pdf_page": page, "category": category})
        else:
            unknown.append(code)

    if section == "First Aid":
        fields = list(re.finditer(r"\b(Eye|Skin|Breath|Swallow):\s*", content))
        for i, m in enumerate(fields):
            code = content[m.end():fields[i + 1].start() if i + 1 < len(fields) else len(content)].strip()
            if code:
                add(f"{m.group(1)}: {code}", first_aid.get((m.group(1), code.casefold())), "First Aid")
    elif section == "Exposure Routes, Symptoms, Target Organs":
        for code, value in abbreviations.items():
            if re.search(r"(?<![\w])" + re.escape(code) + r"(?![\w])", content, re.IGNORECASE):
                add(code, value, "Abbreviation")
        unknown.append("약어는 5개 시연 물질의 검증된 목록만 연결합니다. 그 외 표현은 원문을 확인하세요.")
    elif section == "Respirator Recommendations":
        parts = content.split(':', 1)
        raw = parts[1] if len(parts) == 2 else content
        seen = set()
        for token in re.findall(r"[A-Za-z][A-Za-z0-9]*(?::[A-Za-z]+(?:,[A-Za-z]+)?)*|[§*£¥]", raw):
            if token in {"ppm", "Escape", "NIOSH", "OSHA"} or token in seen:
                continue
            seen.add(token)
            add(token, symbols.get(token) if token in symbols else respirators.get(token), "Respirator")
    elif section == "Personal Protection/Sanitation":
        fields = list(re.finditer(r"\b(Wash skin|Skin|Eyes|Remove|Change|Provide):\s*", content))
        for i, match in enumerate(fields):
            value = content[match.end():fields[i + 1].start() if i + 1 < len(fields) else len(content)].strip()
            for (field, code), definition in protection.items():
                if field != match.group(1):
                    continue
                if re.search(r"(?<!\w)" + re.escape(code) + r"(?!\w)", value, re.IGNORECASE):
                    add(f"{field}: {code}", definition, "Personal Protection")
            known = any(field == match.group(1) and re.search(r"(?<!\w)" + re.escape(code) + r"(?!\w)", value, re.IGNORECASE)
                        for field, code in protection)
            if not known:
                unknown.append(f"{match.group(1)}: {value}")
    return matched, unknown
