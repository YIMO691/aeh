"""Read-only AEW integration and local source-control inspection.

AEH owns engineering Change Assurance truth.  An Agent Engineering Workspace
(AEW) may own Task/Run/runtime state and reference the deterministic envelope
produced here.  This module intentionally contains no AEW state store, runtime,
memory, or orchestration implementation.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import jsonschema
import yaml

from .. import paths as aeh_paths
from ..runtime import change as change_module
from ..runtime import coordination


SCM_CONTRACT = "aeh.scm-inspection"
SCM_CONTRACT_VERSION = 1
AEW_CONTRACT = "aeh.aew-governance-adapter"
AEW_CONTRACT_VERSION = 2

_PRUNED_DIRECTORIES = {
    ".aeh", ".git", ".svn", ".hg", ".venv", "__pycache__", "node_modules",
    "Library", "Temp", "obj", "bin",
}

_CHANGE_ARTIFACTS = {
    "change.yaml": "CHANGE_CONTRACT",
    "bugfix.yaml": "BUG_CONTRACT",
    "spec.yaml": "SPECIFICATION",
    "test-plan.yaml": "TEST_PLAN",
    "red.yaml": "RED_EVIDENCE",
    "test-lock.yaml": "TEST_LOCK",
    "green.yaml": "GREEN_EVIDENCE",
    "verification.yaml": "VERIFICATION",
    "traceability.yaml": "TRACEABILITY",
    "approvals.yaml": "APPROVALS",
}


class IntegrationError(ValueError):
    """Raised when a read-only integration contract cannot be produced."""


def _load_schema(name: str, ae_root: str | None = None) -> dict:
    root = ae_root or aeh_paths.ae_root()
    with open(os.path.join(root, "schemas", name), "r", encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def _validate(report: dict, schema_name: str, ae_root: str | None = None) -> None:
    try:
        jsonschema.validate(report, _load_schema(schema_name, ae_root))
    except (OSError, jsonschema.ValidationError) as exc:
        raise IntegrationError("integration contract validation failed: " + str(exc)) from exc


def _sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _checked_file(path: str, target: str) -> str:
    target_real = os.path.realpath(target)
    real = os.path.realpath(path)
    try:
        contained = os.path.commonpath([target_real, real]) == target_real
    except ValueError:
        contained = False
    if not contained or os.path.islink(path):
        raise IntegrationError("artifact path escapes target or is a symlink: " + path)
    return real


def _run(argv: list[str], timeout: int = 8) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        shell=False,
    )


def _marker_type(path: str) -> str | None:
    if os.path.isdir(os.path.join(path, ".svn")):
        return "SVN"
    if os.path.isdir(os.path.join(path, ".git")) or os.path.isfile(os.path.join(path, ".git")):
        return "GIT"
    return None


def _git_identity(path: str, warnings: list[dict]) -> dict:
    identity = {"commit": None, "branch": None, "revision": None,
                "repository_uuid": None, "dirty": None}
    try:
        head = _run(["git", "-C", path, "rev-parse", "HEAD"])
        branch = _run(["git", "-C", path, "symbolic-ref", "--short", "-q", "HEAD"])
        status = _run(["git", "--no-optional-locks", "-C", path, "status", "--porcelain"])
        if head.returncode == 0:
            identity["commit"] = head.stdout.strip() or None
        else:
            warnings.append({"code": "git_identity_unavailable", "path": "."})
        if branch.returncode == 0:
            identity["branch"] = branch.stdout.strip() or None
        if status.returncode == 0:
            identity["dirty"] = bool(status.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        warnings.append({"code": "git_command_unavailable", "path": "."})
    return identity


def _svn_identity(path: str, warnings: list[dict]) -> dict:
    identity = {"commit": None, "branch": None, "revision": None,
                "repository_uuid": None, "dirty": None}
    try:
        result = _run(["svn", "info", "--xml", path])
        if result.returncode != 0:
            warnings.append({"code": "svn_identity_unavailable", "path": "."})
            return identity
        root = ET.fromstring(result.stdout)
        entry = root.find("entry")
        if entry is not None:
            identity["revision"] = entry.attrib.get("revision")
        uuid = root.findtext("./entry/repository/uuid")
        identity["repository_uuid"] = uuid or None
        # Recursive status is deliberately not run: large working copies must
        # remain bounded and the result must not pretend that root-only status
        # represents the whole checkout.
        warnings.append({"code": "svn_dirty_not_scanned", "path": "."})
    except (OSError, subprocess.SubprocessError, ET.ParseError):
        warnings.append({"code": "svn_command_unavailable", "path": "."})
    return identity


def _nested_repositories(root: str, max_depth: int, max_directories: int,
                         warnings: list[dict]) -> list[dict]:
    repositories = []
    pending = [(root, 0)]
    visited = 0
    while pending:
        directory, depth = pending.pop(0)
        if depth >= max_depth:
            continue
        try:
            entries = sorted(os.scandir(directory), key=lambda item: item.name.casefold())
        except OSError:
            warnings.append({"code": "directory_unreadable",
                             "path": os.path.relpath(directory, root).replace("\\", "/")})
            continue
        for entry in entries:
            try:
                is_directory = entry.is_dir(follow_symlinks=False)
            except OSError:
                continue
            if not is_directory or entry.name in _PRUNED_DIRECTORIES:
                continue
            visited += 1
            if visited > max_directories:
                warnings.append({"code": "directory_limit_reached", "path": "."})
                return repositories
            candidate = entry.path
            scm_type = _marker_type(candidate)
            if scm_type:
                repositories.append({
                    "path": os.path.relpath(candidate, root).replace("\\", "/"),
                    "type": scm_type,
                })
                # A nested repository is an ownership boundary. Do not scan
                # through it looking for more repositories.
                continue
            pending.append((candidate, depth + 1))
    return repositories


def inspect_scm(target: str, *, max_depth: int = 4, max_directories: int = 5000,
                ae_root: str | None = None) -> dict:
    """Inspect local SCM boundaries without changing the target or using a network."""
    if max_depth < 0 or max_depth > 16:
        raise IntegrationError("max_depth must be between 0 and 16")
    if max_directories < 1 or max_directories > 100000:
        raise IntegrationError("max_directories must be between 1 and 100000")
    root = os.path.realpath(os.path.abspath(target))
    if not os.path.isdir(root):
        raise IntegrationError("target directory does not exist: " + target)

    warnings: list[dict] = []
    scm_type = _marker_type(root) or "NONE"
    if scm_type == "GIT":
        identity = _git_identity(root, warnings)
    elif scm_type == "SVN":
        identity = _svn_identity(root, warnings)
    else:
        identity = {"commit": None, "branch": None, "revision": None,
                    "repository_uuid": None, "dirty": None}

    report = {
        "status": "INSPECTION_COMPLETE",
        "contract": SCM_CONTRACT,
        "version": SCM_CONTRACT_VERSION,
        "read_only": True,
        "network_used": False,
        "target_root": root,
        "root_repository": {"type": scm_type, "identity": identity},
        "nested_repositories": _nested_repositories(
            root, max_depth, max_directories, warnings),
        "limits": {"max_depth": max_depth, "max_directories": max_directories},
        "warnings": warnings,
    }
    _validate(report, "scm-inspection.schema.json", ae_root)
    return report


def _portable_verdict(verification: dict | None) -> tuple[str, str]:
    if not verification or not verification.get("overall"):
        return "NOT_AVAILABLE", "NOT_VERIFIED"
    native = verification["overall"]
    if native in ("MERGE_READY", "READY_WITH_WARNINGS"):
        return native, "VERIFIED"
    results = verification.get("results", [])
    failed = any(
        item.get("status") == "fail" or item.get("verdict") in ("fail", "rejected")
        for item in results
    )
    return native, "FAILED" if failed else "INCONCLUSIVE"


def _artifact_refs(change_dir: str, target: str) -> list[dict]:
    refs = []
    for name, kind in sorted(_CHANGE_ARTIFACTS.items()):
        path = os.path.join(change_dir, name)
        if os.path.isfile(path):
            _checked_file(path, target)
            refs.append({
                "kind": kind,
                "path": os.path.relpath(path, target).replace("\\", "/"),
                "sha256": _sha256(path),
            })
    evidence_dir = os.path.join(change_dir, "evidence")
    if os.path.isdir(evidence_dir):
        evidence_files = []
        for directory, dirs, files in os.walk(evidence_dir):
            dirs[:] = sorted(dirs)
            for name in sorted(files):
                evidence_files.append(os.path.join(directory, name))
                if len(evidence_files) > 1000:
                    raise IntegrationError("change evidence exceeds bounded export limit (1000 files)")
        for path in evidence_files:
            _checked_file(path, target)
            refs.append({
                "kind": "EVIDENCE",
                "path": os.path.relpath(path, target).replace("\\", "/"),
                "sha256": _sha256(path),
            })
    return sorted(refs, key=lambda item: (item["path"], item["kind"]))


def _load_optional_yaml(path: str) -> dict | None:
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as stream:
            value = yaml.safe_load(stream)
    except (OSError, yaml.YAMLError) as exc:
        raise IntegrationError("cannot read integration source artifact: " + path) from exc
    return value if isinstance(value, dict) else None


def _export_change_snapshot(target: str, change_id: str, *, task_id: str,
                            run_id: str, project_id: str | None = None,
                            ae_root: str | None = None) -> dict:
    if not task_id or not run_id:
        raise IntegrationError("task_id and run_id are required AEW references")
    root = os.path.realpath(os.path.abspath(target))
    if not os.path.isdir(root):
        raise IntegrationError("target directory does not exist: " + target)
    if not change_module.CHG_RE.fullmatch(change_id):
        raise IntegrationError("invalid change_id: " + str(change_id))
    change_dir = os.path.join(root, ".aeh", "changes", change_id)
    change_path = os.path.join(change_dir, "change.yaml")
    if os.path.isfile(change_path):
        _checked_file(change_path, root)
    try:
        change = change_module.load_change(root, change_id)
    except (change_module.ChangeError, OSError, yaml.YAMLError) as exc:
        raise IntegrationError(str(exc)) from exc

    verification_path = os.path.join(change_dir, "verification.yaml")
    if os.path.isfile(verification_path):
        _checked_file(verification_path, root)
    verification = _load_optional_yaml(verification_path)
    native_verdict, portable_verdict = _portable_verdict(verification)
    artifacts = _artifact_refs(change_dir, root)
    manifest_path = os.path.join(root, ".aeh", "manifest.yaml")
    manifest_real = None
    if os.path.isfile(manifest_path):
        manifest_real = _checked_file(manifest_path, root)
    manifest = _load_optional_yaml(manifest_path) or {}
    harness = manifest.get("harness", {}) if isinstance(manifest.get("harness", {}), dict) else {}

    scm_report = inspect_scm(root, max_depth=0, ae_root=ae_root)
    source_control = {
        "type": scm_report["root_repository"]["type"],
        "identity": scm_report["root_repository"]["identity"],
    }
    external_refs = {"task_id": task_id, "run_id": run_id}
    if project_id:
        external_refs["project_id"] = project_id

    report = {
        "status": "EXPORT_COMPLETE",
        "contract": AEW_CONTRACT,
        "version": AEW_CONTRACT_VERSION,
        "read_only": True,
        "network_used": False,
        "external_refs": external_refs,
        "governance": {
            "provider": "AEH",
            "change_id": change_id,
            "classification": (
                change.get("classification", {}).get("level")
                if isinstance(change.get("classification"), dict)
                else change.get("classification")
            ),
            "workflow_level": change.get("workflow", {}).get("level"),
            "phase": change.get("state", {}).get("current"),
            "gates": change.get("gates", {}),
            "native_verdict": native_verdict,
            "portable_verdict": portable_verdict,
        },
        "source": {
            "repository_ref": ".",
            "source_control": source_control,
            "harness_version": harness.get("version"),
            "harness_source_revision": harness.get("source_revision"),
            "manifest_sha256": _sha256(manifest_real) if manifest_real else None,
        },
        "artifacts": artifacts,
        "metadata": {
            "scope": {"kind": "CHANGE", "ref": change_id},
            "ownership": {
                "operational_task_run": "AEW_OR_EXTERNAL_OWNER",
                "engineering_change": "AEH",
                "repository": "SCM_OR_PROJECT",
            },
            "authority": "ENGINEERING_CHANGE_ASSURANCE",
            "lifecycle": "DERIVED_READ_ONLY_SNAPSHOT",
            "provenance": {
                "change_contract_sha256": next(
                    (item["sha256"] for item in artifacts if item["kind"] == "CHANGE_CONTRACT"),
                    None,
                ),
                "artifact_count": len(artifacts),
            },
            "cost": {"class": "BOUNDED_LOCAL_READ", "writes": False, "network": False},
        },
    }
    return report


def export_change(target: str, change_id: str, *, task_id: str, run_id: str,
                  project_id: str | None = None, ae_root: str | None = None,
                  coordination_state_root: str | None = None,
                  coordination_repository_id: str | None = None,
                  coordination_timeout_seconds: float = 5.0) -> dict:
    """Export one stable, deterministic and read-only AEW v2 envelope."""
    snapshot = coordination.stable_change_snapshot(
        target, change_id,
        lambda: _export_change_snapshot(
            target, change_id, task_id=task_id, run_id=run_id,
            project_id=project_id, ae_root=ae_root),
        repository_id=coordination_repository_id,
        state_root=coordination_state_root,
        timeout_seconds=coordination_timeout_seconds)
    report = snapshot["value"]
    report["coordination"] = snapshot["coordination"]
    _validate(report, "aew-governance-adapter.schema.json", ae_root)
    return report
