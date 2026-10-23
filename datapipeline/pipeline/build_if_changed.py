"""Build the shared FAISS index only when its inputs have changed.

The stable ``indexes/current`` symlink always points to a complete build.  A
failed refresh leaves the previous build available to the RAG server.
"""

import argparse
import asyncio
import fcntl
import hashlib
import json
import os
import tempfile
import time
import uuid
from pathlib import Path
from types import SimpleNamespace

from dotenv import load_dotenv

from .pipeline import CHEMICALS, INDEX_CONFIG, PDF_PATH, SECTIONS, collect, index


ROOT = Path(__file__).resolve().parent.parent
INPUT_FILES = (
    "pipeline/pipeline.py",
    "pipeline/test_msds_api.py",
    "pipeline/niosh_pdf.py",
    "pipeline/niosh_codes.py",
    "pyproject.toml",
    "uv.lock",
)


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def input_fingerprint(pdf: Path) -> str:
    digest = hashlib.sha256()
    for path in (pdf, *(ROOT / name for name in INPUT_FILES)):
        digest.update(str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path).encode())
        digest.update(_hash_file(path).encode())
    digest.update(json.dumps(INDEX_CONFIG, sort_keys=True).encode())
    return digest.hexdigest()


def records_fingerprint(data: dict) -> str:
    """Ignore collection timestamps and ordering when comparing source content."""
    records = []
    for record in data["records"]:
        stable = {key: value for key, value in record.items() if key != "retrieved_at"}
        records.append(json.dumps(stable, sort_keys=True, ensure_ascii=False))
    return hashlib.sha256("\n".join(sorted(records)).encode()).hexdigest()


def validate_collection(data: dict) -> None:
    """Reject incomplete API responses before they can replace a good index."""
    records = data.get("records", [])
    statuses = data.get("status", {})
    for cas in CHEMICALS:
        status = statuses.get(cas, {})
        kosha = status.get("kosha", {})
        if set(kosha) != {str(section) for section in SECTIONS} or any(
            item.get("status") not in {"ok", "empty"} for item in kosha.values()
        ):
            raise ValueError(f"{cas}: KOSHA 수집 항목이 불완전합니다.")
        if status.get("niosh_pdf", {}).get("status") != "ok":
            raise ValueError(f"{cas}: NIOSH PDF 수집이 불완전합니다.")
        for source in ("KOSHA", "NIOSH PDF"):
            if not any(record.get("cas_no") == cas and record.get("source") == source
                       for record in records):
                raise ValueError(f"{cas}: {source} 문서가 없습니다.")


def _valid_index(path: Path) -> bool:
    try:
        return (path / "index.faiss").is_file() and (path / "index.pkl").is_file() and (
            json.loads((path / "config.json").read_text()) == INDEX_CONFIG
        )
    except (OSError, ValueError):
        return False


def _manifest(path: Path) -> dict:
    try:
        return json.loads((path / "manifest.json").read_text())
    except (OSError, ValueError):
        return {}


def _write_json_atomic(path: Path, value: dict) -> None:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def build_if_changed(data_dir: Path, pdf: Path, refresh_hours: float, force_refresh: bool = False) -> str:
    if refresh_hours < 0:
        raise ValueError("KOSHA_REFRESH_HOURS must be non-negative")
    raw_dir = data_dir / "raw"
    indexes_dir = data_dir / "indexes"
    raw_dir.mkdir(parents=True, exist_ok=True)
    indexes_dir.mkdir(parents=True, exist_ok=True)
    current = indexes_dir / "current"
    raw_current = raw_dir / "current.json"
    fingerprint = input_fingerprint(pdf)

    with (indexes_dir / ".build.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        valid = _valid_index(current)
        manifest = _manifest(current) if valid else {}
        local_changed = manifest.get("input_fingerprint") != fingerprint
        last_check = float(manifest.get("checked_at", 0))
        due = force_refresh or time.time() - last_check >= refresh_hours * 3600
        if valid and not local_changed and not due:
            print("인덱스 재사용: 입력 변경 없음, KOSHA 갱신 시점 전")
            return "reused"

        with tempfile.TemporaryDirectory(prefix=".collect-", dir=raw_dir) as temp_raw_dir:
            collected = Path(temp_raw_dir) / "collected.json"
            try:
                asyncio.run(collect(SimpleNamespace(pdf=str(pdf), output=str(collected),
                                                    reuse_kosha=None, cas=list(CHEMICALS))))
                data = json.loads(collected.read_text())
                validate_collection(data)
            except Exception:
                if valid:
                    print("KOSHA 갱신 실패: 기존 인덱스를 계속 사용합니다.")
                    return "stale"
                raise
            records_hash = records_fingerprint(data)
            checked_at = time.time()
            if valid and not local_changed and manifest.get("records_fingerprint") == records_hash:
                _write_json_atomic(current / "manifest.json", {**manifest, "checked_at": checked_at})
                os.replace(collected, raw_current)
                print("인덱스 재사용: KOSHA·PDF 내용 변경 없음")
                return "unchanged"

            try:
                with tempfile.TemporaryDirectory(prefix=".index-", dir=indexes_dir) as temp_index_dir:
                    staging = Path(temp_index_dir) / "build"
                    index(SimpleNamespace(input=str(collected), output=str(staging), kosha_only=False))
                    if not _valid_index(staging):
                        raise RuntimeError("새 인덱스 검증 실패")
                    _write_json_atomic(staging / "manifest.json", {
                        "input_fingerprint": fingerprint,
                        "records_fingerprint": records_hash,
                        "checked_at": checked_at,
                        "record_count": len(data["records"]),
                    })
                    version = indexes_dir / f"build-{int(checked_at)}-{uuid.uuid4().hex[:8]}"
                    os.replace(staging, version)
                    link = indexes_dir / f".current-{uuid.uuid4().hex}"
                    try:
                        link.symlink_to(version.name, target_is_directory=True)
                        os.replace(link, current)
                    finally:
                        link.unlink(missing_ok=True)
            except Exception:
                if valid:
                    print("새 인덱스 생성 실패: 기존 인덱스를 계속 사용합니다.")
                    return "stale"
                raise
            os.replace(collected, raw_current)
            print(f"새 인덱스 적용: {version.name} / 문서 {len(data['records'])}개")
            return "rebuilt"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="KOSHA 갱신 주기를 무시하고 확인")
    args = parser.parse_args()
    load_dotenv(ROOT.parent / ".env")
    data_dir = Path(os.getenv("DATA_DIR", str(ROOT / "data")))
    pdf = Path(os.getenv("NIOSH_PDF_PATH", str(PDF_PATH)))
    hours = float(os.getenv("KOSHA_REFRESH_HOURS", "24"))
    build_if_changed(data_dir, pdf, hours, args.refresh)


if __name__ == "__main__":
    main()
