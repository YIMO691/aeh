"""Build and verify the AEH Design & Evidence Baseline v0.2 handbook."""

from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "AEH_Engineering_Architecture_Handbook_v0.2.md"
MANIFEST = ROOT / "FILE_MANIFEST.sha256"
PREAMBLE = """# AEH Engineering & Architecture Handbook v0.2
## 《AEH 工程与架构手册》

> Research cutoff: **2026-08-19**  
> AEH software baseline: **v0.1.0 / YIMO691/aeh @ 6513102**  
> Evidence baseline: **Phase 1.1 / protocol v1.6**  
> Strategic verdict: **CONTINUE_BUT_NARROW — conditional**  
> Product efficacy: **NOT_YET_PROVEN**  
> Phase 2 / 72-run: **NOT AUTHORIZED**

> **The generator proposes. The evidence records. The verifier decides.**
"""
ID_PATTERN = re.compile(
    r"(?<![A-Z0-9_-])(?:CLM-\d{3}|ADR-HB-\d{3}|(?:AEH|EVAL|EXT|INT)-[A-Z0-9][A-Z0-9._-]*)"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")


def source_files() -> list[Path]:
    chapters: list[Path] = []
    for number in range(27):
        matches = list(ROOT.glob(f"part-*/*/{number:02d}_*.md"))
        if not matches:
            matches = list(ROOT.glob(f"part-*/{number:02d}_*.md"))
        if len(matches) != 1:
            raise ValueError(f"chapter {number:02d}: expected one file, found {len(matches)}")
        chapters.append(matches[0])
    appendices = []
    for letter in "ABCDEFG":
        matches = list((ROOT / "appendices").glob(f"{letter}_*.md"))
        if len(matches) != 1:
            raise ValueError(f"appendix {letter}: expected one file, found {len(matches)}")
        appendices.append(matches[0])
    return chapters + appendices


def assembled_master() -> str:
    sections = [_read(path).strip() for path in source_files()]
    return PREAMBLE.strip() + "\n\n---\n\n" + "\n\n---\n\n".join(sections) + "\n"


def _manifest_files() -> list[Path]:
    return sorted(
        (path for path in ROOT.rglob("*")
         if path.is_file()
         and path != MANIFEST
         and "__pycache__" not in path.parts),
        key=lambda path: path.relative_to(ROOT).as_posix(),
    )


def _portable_bytes(path: Path) -> bytes:
    """Normalize text line endings so hashes survive Git autocrlf checkouts."""
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw
    return text.replace("\r\n", "\n").encode("utf-8")


def manifest_text() -> str:
    rows = []
    for path in _manifest_files():
        digest = hashlib.sha256(_portable_bytes(path)).hexdigest()
        rows.append(f"{digest}  {path.relative_to(ROOT).as_posix()}")
    return "\n".join(rows) + "\n"


def _registry_ids() -> tuple[set[str], list[str]]:
    specs = (
        ("source-registry.yaml", "sources"),
        ("claim-registry.yaml", "claims"),
        ("decision-registry.yaml", "decisions"),
    )
    ids: list[str] = []
    registry_ids: set[str] = set()
    for filename, key in specs:
        data = yaml.safe_load(_read(ROOT / "references" / filename))
        registry_ids.add(data["registry"]["id"])
        ids.extend(item["id"] for item in data[key])
    duplicates = sorted(item for item in set(ids) if ids.count(item) > 1)
    return set(ids) | registry_ids, duplicates


def check() -> list[str]:
    errors: list[str] = []
    try:
        sources = source_files()
    except ValueError as exc:
        return [str(exc)]

    non_ascii = [
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("*")
        if any(ord(char) > 127 for char in path.relative_to(ROOT).as_posix())
    ]
    if non_ascii:
        errors.append("non-ASCII paths: " + ", ".join(non_ascii))

    if not MASTER.is_file() or _read(MASTER) != assembled_master():
        errors.append("single-file master is not the deterministic projection of split sources")

    defined, duplicates = _registry_ids()
    if duplicates:
        errors.append("duplicate registry IDs: " + ", ".join(duplicates))
    text = "\n".join(_read(path) for path in sources + [ROOT / "README.md"])
    refs = {
        token for token in ID_PATTERN.findall(text)
        if not token.endswith(("-", ".")) and ".." not in token
    }
    missing = sorted(refs - defined)
    if missing:
        errors.append("undefined referenced IDs: " + ", ".join(missing))

    stale_markers = (
        "NOT IN CURRENT HANDBOOK EVIDENCE BASE",
        "Phase 1.1 final evidence not integrated",
        "Phase 1.1 最终证据未纳入",
        "Phase 1.1、72-run、A01–A08 正式结果尚未进入",
    )
    full_text = "\n".join(_read(path) for path in ROOT.rglob("*.md"))
    for marker in stale_markers:
        if marker in full_text:
            errors.append(f"stale evidence marker remains: {marker}")
    if "NOT_YET_PROVEN" not in _read(ROOT / "HANDBOOK_STATUS.yaml"):
        errors.append("product efficacy boundary is missing")
    status = yaml.safe_load(_read(ROOT / "HANDBOOK_STATUS.yaml"))
    if status.get("handbook_version") != "v0.2":
        errors.append("handbook_version must be v0.2")
    if status.get("aeh_software_version") != "v0.1.0":
        errors.append("AEH software baseline must remain v0.1.0")
    if status.get("phase2_72_run", {}).get("authorized") is not False:
        errors.append("Phase 2 / 72-run must remain unauthorized")

    if not MANIFEST.is_file() or _read(MANIFEST) != manifest_text():
        errors.append("FILE_MANIFEST.sha256 is stale or incomplete")
    return errors


def write() -> None:
    MASTER.write_text(assembled_master(), encoding="utf-8", newline="\n")
    MANIFEST.write_text(manifest_text(), encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="regenerate master and manifest")
    parser.add_argument("--check", action="store_true", help="verify the handbook package")
    args = parser.parse_args()
    if not args.write and not args.check:
        parser.error("select --write and/or --check")
    if args.write:
        write()
    if args.check:
        errors = check()
        if errors:
            for error in errors:
                print("FAIL: " + error)
            return 1
        print("HANDBOOK_CHECK_PASS")
        print("chapters=27 appendices=7")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
