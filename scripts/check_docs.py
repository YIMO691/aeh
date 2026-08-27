#!/usr/bin/env python3
"""Validate AEH's bounded public documentation contract.

This checker deliberately validates only current public claims and local links
from maintained entry documents. Historical release/archive content remains
version-bound evidence and is not rewritten or promoted to current truth.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote

import yaml


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "docs" / "documentation-contract.yaml"

LINK_DOCUMENTS = (
    "README.md",
    "CONTRIBUTING.md",
    "docs/README.md",
    "docs/about.md",
    "docs/status.md",
    "docs/architecture-current.md",
    "docs/engineering-guide.md",
    "docs/roadmap-v0.2.md",
    "docs/decisions.md",
    "docs/architecture.md",
    "docs/repository-panorama.md",
    "docs/handbook/README.md",
    "docs/handbook/CURRENT_SUPPLEMENT.md",
    "docs/research/README.md",
    "docs/integrations/aew.md",
    "docs/m4-governance.md",
    "examples/README.md",
)

LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as stream:
        value = yaml.safe_load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"expected mapping: {path.relative_to(ROOT)}")
    return value


def project_version() -> str:
    """Read the bounded PEP 621 version without requiring Python 3.11 tomllib."""
    in_project = False
    for raw_line in (ROOT / "pyproject.toml").read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line == "[project]":
            in_project = True
            continue
        if in_project and line.startswith("["):
            break
        if in_project:
            match = re.fullmatch(r'version\s*=\s*["\']([^"\']+)["\']', line)
            if match:
                return match.group(1)
    raise ValueError("pyproject.toml is missing [project].version")


def text(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def local_link_target(source: Path, raw_target: str) -> Path | None:
    target = raw_target.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    target = target.split(maxsplit=1)[0]
    if not target or target.startswith(("#", "http://", "https://", "mailto:")):
        return None
    target = unquote(target.split("#", 1)[0].split("?", 1)[0])
    if not target:
        return None
    if target.startswith("/") or re.match(r"^[A-Za-z]:", target):
        raise ValueError(f"absolute local link is not public-safe: {raw_target}")
    return (source.parent / target).resolve()


def validate() -> list[str]:
    errors: list[str] = []
    contract = load_yaml(CONTRACT_PATH)
    release = contract["release"]
    roadmap = contract["roadmap"]
    validation = contract["validation"]

    source_version = str(release["source_version"])
    latest_release = str(release["latest_github_release"])
    if project_version() != source_version:
        errors.append(
            f"source version drift: pyproject={project_version()} docs={source_version}"
        )

    current_files = [str(item) for item in contract["current_claim_files"]]
    for rel_path in current_files:
        path = ROOT / rel_path
        if not path.is_file():
            errors.append(f"missing current claim file: {rel_path}")
            continue
        body = text(rel_path)
        if "CURRENT" not in body:
            errors.append(f"missing CURRENT label: {rel_path}")
        if source_version not in body:
            errors.append(f"missing source version {source_version}: {rel_path}")

    status = text("docs/status.md")
    readme = text("README.md")
    for rel_path, body in (("README.md", readme), ("docs/status.md", status)):
        required = (
            latest_release,
            "M1–M4",
            "M5–M6",
            "PyPI",
            str(validation["local_tests_discovered"]),
            str(validation["local_tests_passed"]),
            str(validation["local_tests_skipped"]),
        )
        for claim in required:
            if claim not in body:
                errors.append(f"missing canonical claim {claim!r}: {rel_path}")

    merged = [str(item) for item in roadmap["merged"]]
    planned = [str(item) for item in roadmap["planned"]]
    for milestone in merged:
        if f"| {milestone} | MERGED |" not in status:
            errors.append(f"missing merged milestone row: {milestone}")
    for milestone in planned:
        if f"| {milestone} | PLANNED |" not in status:
            errors.append(f"missing planned milestone row: {milestone}")

    changelog = text("CHANGELOG.md")
    if f"## [{source_version}]" not in changelog:
        errors.append("CHANGELOG is missing the current source version section")
    if f"## [{latest_release.removeprefix('v')}]" not in changelog:
        errors.append("CHANGELOG is missing the latest release section")

    for rel_path in contract["version_bound_documents"]:
        body = text(str(rel_path))
        if "VERSION-BOUND" not in body:
            errors.append(f"missing VERSION-BOUND label: {rel_path}")

    for rel_path in contract["frozen_evidence_roots"]:
        if not (ROOT / str(rel_path)).is_dir():
            errors.append(f"missing frozen evidence root: {rel_path}")

    for rel_path in LINK_DOCUMENTS:
        source = ROOT / rel_path
        if not source.is_file():
            errors.append(f"missing link-check document: {rel_path}")
            continue
        for match in LINK_RE.finditer(source.read_text(encoding="utf-8")):
            raw_target = match.group(1)
            try:
                target = local_link_target(source, raw_target)
            except ValueError as exc:
                errors.append(f"{rel_path}: {exc}")
                continue
            if target is not None and not target.exists():
                errors.append(
                    f"broken local link: {rel_path} -> {raw_target}"
                )

    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("DOCUMENTATION_CHECK_FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("DOCUMENTATION_CHECK_PASS")
    print("source_version=0.3.0.dev0")
    print("latest_github_release=v0.2.0")
    print("roadmap=M1-M4_MERGED+M5-M6_PLANNED")
    print(f"link_documents={len(LINK_DOCUMENTS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
