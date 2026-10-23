"""공단 MSDS API 연결 연습: 물질 검색 → 취급·저장 정보 조회."""

import argparse
import asyncio
import os
from pathlib import Path
from urllib.parse import unquote
from xml.etree import ElementTree

import aiohttp
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
BASE_URL = "https://apis.data.go.kr/B552468/msdschem1"


def get_key() -> str:
    load_dotenv(BASE_DIR / ".env")
    key = os.getenv("KOSHA_API_KEY", "").strip()
    if not key or key == "여기에_인증키_입력":
        raise ValueError(".env에 KOSHA_API_KEY를 설정해 주세요.")
    # 공공데이터포털의 인코딩 키를 입력해도 요청 시 중복 인코딩하지 않도록 처리한다.
    return unquote(key)


async def fetch_xml(session: aiohttp.ClientSession, path: str, params: dict) -> ElementTree.Element:
    async with session.get(f"{BASE_URL}/{path}", params=params, timeout=aiohttp.ClientTimeout(total=20)) as response:
        if response.status != 200:
            raise RuntimeError(f"API HTTP 오류: {response.status}")
        content = await response.read()
    try:
        root = ElementTree.fromstring(content)
    except ElementTree.ParseError:
        raise RuntimeError("API 응답이 XML이 아닙니다. 인증 및 서비스 상태를 확인해 주세요.") from None
    code = root.findtext(".//resultCode") or root.findtext(".//returnReasonCode")
    if code and code.strip() not in {"00", "0", "0000"}:
        raise RuntimeError(f"API 결과 코드: {code.strip()} (활용 신청과 인증키를 확인하세요)")
    return root


async def main() -> None:
    parser = argparse.ArgumentParser(description="안전보건공단 MSDS API 연결 테스트")
    parser.add_argument("--cas", default="64-17-5", help="검색할 CAS 번호 (기본값: 에탄올)")
    parser.add_argument("--name", help="CAS 번호 대신 국문 물질명으로 검색")
    parser.add_argument("--chem-id", help="검색 결과가 여러 개일 때 확인한 화학물질 ID")
    args = parser.parse_args()
    key = get_key()
    search_value = args.name if args.name else args.cas
    async with aiohttp.ClientSession() as session:
        root = await fetch_xml(session, "getChemList001", {
            "serviceKey": key, "searchWrd": search_value,
            "searchCnd": 0 if args.name else 1, "numOfRows": 10, "pageNo": 1,
        })
        matches = []
        for node in root.iter():
            chem_id = node.findtext("chemId")
            if chem_id:
                matches.append((chem_id.strip(), (node.findtext("chemNameKor") or "").strip(),
                                (node.findtext("casNo") or "").strip()))
        print(f"검색 결과 (첫 페이지): {len(matches)}건")
        for chem_id, name, cas in matches:
            print(f"  ID: {chem_id} | 물질명: {name or '-'} | CAS: {cas or '-'}")
        if not matches:
            print("검색 결과가 없습니다. 검색어와 API 응답을 확인하세요.")
            return
        selected = [m for m in matches if m[0] == args.chem_id] if args.chem_id else matches
        if len(selected) != 1:
            print("결과를 확인한 후 --chem-id 화학물질ID 를 지정해 다시 실행하세요.")
            return
        chem_id, name, cas = selected[0]
        detail = await fetch_xml(session, "getChemDetail071", {"serviceKey": key, "chemId": chem_id})
        print(f"\n취급 및 저장방법: {name or '-'} (CAS: {cas or '-'}, ID: {chem_id})")
        count = 0
        for node in detail.iter():
            label = (node.findtext("msdsItemNameKor") or "").strip()
            value = (node.findtext("itemDetail") or "").strip()
            if label or value:
                print(f"  {label or '항목'}: {value or '(내용 없음)'}")
                count += 1
        if not count:
            print("상세 항목이 없거나 응답 구조 확인이 필요합니다.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (ValueError, RuntimeError) as exc:
        print(f"확인 필요: {exc}")
        raise SystemExit(1) from None
    except (aiohttp.ClientError, asyncio.TimeoutError):
        # 요청 URL에 키가 포함될 수 있으므로 예외 원문을 출력하지 않는다.
        print("연결 실패: 네트워크와 API 서비스 상태를 확인하세요.")
        raise SystemExit(1) from None
