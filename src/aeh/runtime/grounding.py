"""AEH Change-scoped Repository Grounding（Phase 9）

GROUND 从"状态"变成真正执行阶段：围绕当前 Change 定向搜索、留证、验证，
证据充分时 GROUNDING Gate PASS，允许进入 SPEC。

安全边界（继承 Phase 2 Hardening）：只读、无网络、repository-root 边界、
symlink 逃逸防护、binary/oversized 防护、资源上限、minimum disclosure、no secret echo。
写入仅限 .aeh/changes/CHG-*/。

不实现：Spec Runtime、自动 REQ/AC、Test Design、RED/GREEN、Approval Enforcement。
"""
import hashlib
import os
import re
from datetime import datetime, timezone

import jsonschema
import yaml

from .. import paths as aeh_paths
from ..discovery import _resolve_within, _is_binary
from ..doctor import doctor as doc
from . import change as ch
from . import coordination as coord

CONTRACT = "bootstrap.evidence-index"
CONTRACT_VERSION = 1
DEFAULT_LIMITS = {"max_content_bytes": 1048576, "max_walk_files": 20000, "max_hits_per_file": 8, "max_evidence": 40}

CJK_RE = re.compile(r"[\u4e00-\u9fff]+")
LATIN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


class GroundingError(ValueError):
    pass


def _load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _dump_yaml(obj):
    return yaml.safe_dump(obj, sort_keys=True, allow_unicode=True)


def _sha256_file(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _tokens(title):
    tokens = [t.lower() for t in LATIN_RE.findall(title or "")]
    for run in CJK_RE.findall(title or ""):
        tokens.append(run)
        if len(run) >= 2:
            tokens.extend(run[i:i + 2] for i in range(len(run) - 1))
    return [t for t in tokens if len(t) >= 2]


def _scan(root, needles, limits):
    hits = []
    walk_files = 0
    resource_limited = False
    for dp, dns, fns in os.walk(root):
        if ".git" in dp or ".aeh" in dp or "__pycache__" in dp:
            continue
        dns[:] = [d for d in dns if ".git" not in d and ".aeh" not in d]
        for fn in sorted(fns):
            walk_files += 1
            if walk_files > limits["max_walk_files"]:
                resource_limited = True
                break
            full = os.path.join(dp, fn)
            rel = os.path.relpath(full, root)
            if _resolve_within(root, rel) is None:
                continue
            if _is_binary(full, limits):
                continue
            try:
                with open(full, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            low = text.lower()
            file_hits = 0
            for needle in needles:
                if file_hits >= limits["max_hits_per_file"]:
                    break
                idx = low.find(needle.lower())
                if idx >= 0:
                    line = low[:idx].count("\n") + 1
                    hits.append({"path": rel, "line": line, "token": needle,
                                 "file_hash": _sha256_file(full)})
                    file_hits += 1
        if resource_limited:
            break
    return hits, resource_limited

def _test_search(root, tokens, rules, limits):
    test_dir_hits = []
    for td in rules["test_dirs"]:
        d = os.path.join(root, td)
        if os.path.isdir(d):
            hits, limited = _scan(d, tokens, limits)
            # release-fix 003：_scan 的 rel 相对其 root（此处是 tests/），
            # 证据 rel_path 必须相对仓库根，否则后续 stale 检查必然误判。
            for h in hits:
                # cwd 无关：join 必须先锚定 root，否则 relpath 会按进程 cwd 绝对化（跨盘 ValueError）
                h["path"] = os.path.relpath(os.path.join(root, td, h["path"]), root)
            test_dir_hits.extend(hits)
            if hits:
                return hits, "FOUND", limited
    pattern_hits = []
    for pattern in rules["test_file_patterns"]:
        for dp, dns, fns in os.walk(root):
            if ".git" in dp or ".aeh" in dp:
                continue
            for fn in fns:
                from fnmatch import fnmatch
                if fnmatch(fn, pattern):
                    rel = os.path.relpath(os.path.join(dp, fn), root)
                    full = os.path.join(dp, fn)
                    if _resolve_within(root, rel) is None or _is_binary(full, limits):
                        continue
                    with open(full, "r", encoding="utf-8", errors="ignore") as f:
                        text = f.read().lower()
                    if any(t in text for t in tokens):
                        pattern_hits.append({"path": rel, "line": 1, "token": tokens[0],
                                             "file_hash": _sha256_file(full)})
                    else:
                        pattern_hits.append({"path": rel, "line": 1, "token": None,
                                             "file_hash": _sha256_file(full)})
    if pattern_hits:
        return pattern_hits, "FOUND", False
    return [], "NOT_FOUND", False


def _config_search(root, tokens, rules, limits):
    hits, limited = _scan(root, tokens, limits)
    config_hits = [h for h in hits if any(h["path"].endswith(ext) for ext in rules["config_extensions"])]
    return config_hits, limited


def _git_identity(root):
    try:
        import subprocess
        base = subprocess.run(["git", "-C", root, "rev-parse", "HEAD"],
                              capture_output=True, text=True, timeout=5)
        status = subprocess.run(["git", "-C", root, "status", "--porcelain"],
                                capture_output=True, text=True, timeout=5)
        return {"base_commit": base.stdout.strip() or None, "dirty": bool(status.stdout.strip())}
    except Exception:
        return {"base_commit": None, "dirty": None}


def domains_of(classification):
    domains = []
    for e in classification.get("evidence", []) or []:
        if isinstance(e, dict):
            domains.append(e["domain"])
        elif isinstance(e, str) and e.startswith("hard_escalation:"):
            domains.append(e.split(":", 1)[1].strip())
    return sorted(set(domains))

def build_evidence(target, change, ae_root, limits=None):
    rules = _load_yaml(os.path.join(ae_root, "bootstrap", "grounding.yaml"))
    limits = dict(DEFAULT_LIMITS if limits is None else {**DEFAULT_LIMITS, **limits})
    title = change.get("title", "")
    tokens = _tokens(title)
    hits, resource_limited = _scan(target, tokens, limits)
    git_id = _git_identity(target)
    evidence = []
    counter = 0

    def evid(etype, finding, confidence, **kw):
        nonlocal counter
        counter += 1
        item = {"id": "EV-%03d" % counter, "type": etype, "finding": finding,
                "confidence": confidence}
        for k, v in kw.items():
            if v is not None:
                item[k] = v
        return item

    for h in hits[:limits["max_evidence"]]:
        evidence.append(evid("SOURCE", "keyword match: " + h["token"] + " in " + h["path"] + ":" + str(h["line"]),
                             "DIRECT",
                             location={"path": h["path"], "symbol": h["token"], "line": h["line"]},
                             relevance={"kind": "task_keyword", "detail": "title token matched"},
                             source_state={"base_commit": git_id["base_commit"], "dirty": git_id["dirty"],
                                           "file_hash": h["file_hash"], "rel_path": h["path"]},
                             query={"rule": "title_keyword", "pattern": h["token"]}))

    test_hits, test_status, test_limited = _test_search(target, tokens, rules, limits)
    if test_status == "FOUND":
        for h in test_hits[:5]:
            evidence.append(evid("TEST", "existing test file: " + h["path"], "DIRECT",
                                 location={"path": h["path"], "line": h["line"]},
                                 relevance={"kind": "existing_test_relation"},
                                 source_state={"base_commit": git_id["base_commit"], "dirty": git_id["dirty"],
                                               "file_hash": h["file_hash"], "rel_path": h["path"]},
                                 test_result="FOUND"))
    else:
        evidence.append(evid("NEGATIVE_SEARCH", "no test files/dirs matched title keywords", "DIRECT",
                             relevance={"kind": "negative_search"},
                             query={"rule": "test_search", "pattern": ",".join(rules["test_dirs"] + rules["test_file_patterns"])},
                             test_result="NOT_FOUND"))

    src_paths = sorted(set(h["path"] for h in hits))
    if len(src_paths) >= 2:
        evidence.append(evid("CALL_PATH", "keyword co-occurrence across " + str(len(src_paths)) + " files: " + ", ".join(src_paths[:4]),
                             "INFERRED",
                             relevance={"kind": "call_relation", "detail": "co-occurrence, not verified"},
                             limitations=["call relation inferred from keyword co-occurrence; not symbolically verified"]))

    config_hits, _ = _config_search(target, tokens, rules, limits)
    for h in config_hits[:5]:
        evidence.append(evid("CONFIG", "config file match: " + h["path"] + ":" + str(h["line"]), "DIRECT",
                             location={"path": h["path"], "line": h["line"]},
                             relevance={"kind": "configuration_relation"},
                             source_state={"base_commit": git_id["base_commit"], "dirty": git_id["dirty"],
                                           "file_hash": h["file_hash"], "rel_path": h["path"]}))

    grounded_domains = []
    class_contract = _load_yaml(os.path.join(ae_root, "core", "classifications.yaml"))
    for domain, keywords in class_contract.get("keyword_hints", {}).items():
        dhits, _ = _scan(target, keywords, limits)
        if dhits:
            grounded_domains.append(domain)
    for d in sorted(grounded_domains):
        evidence.append(evid("SOURCE", "risk domain marker found in repository: " + d, "DIRECT",
                             relevance={"kind": "configuration_relation", "detail": "risk domain grounding"},
                             query={"rule": "risk_domain", "pattern": d}))

    evidence.append(evid("UNKNOWN", "architecture constraints not symbolically verified in Phase 9 scan", "INDIRECT",
                         limitations=["no constraint extraction implemented; treat as unknown, not absent"]))
    unknowns = []
    if resource_limited:
        unknowns.append({"field": "scan_completeness", "reason": "LIMITED_BY_RESOURCE_BOUND"})
    index = {"contract": CONTRACT, "version": CONTRACT_VERSION, "change_id": change["change_id"],
             "repository": {"root": target, "base_commit": git_id["base_commit"], "dirty": git_id["dirty"]},
             "generated_at": datetime.now(timezone.utc).isoformat(),
             "evidence": evidence, "unknowns": unknowns}
    schema = _load_yaml(os.path.join(ae_root, "schemas", "evidence-index.schema.json"))
    jsonschema.validate(index, schema)
    return index, grounded_domains


def gate_sufficient(level, index, grounded_domains, known_domains, rules):
    req = rules["gate_requirements"].get(level, {})
    if not req:
        return True, []
    missing = []
    kinds = [e["type"] for e in index["evidence"]]
    if req.get("source", 0) and "SOURCE" not in kinds:
        missing.append("source")
    if req.get("test_search") and "TEST" not in kinds and "NEGATIVE_SEARCH" not in kinds:
        missing.append("test_search")
    if req.get("constraint_or_unknown") and not (index.get("unknowns") or "UNKNOWN" in kinds or "ARCHITECTURE_CONSTRAINT" in kinds):
        missing.append("constraint_or_unknown")
    if req.get("call_path", 0) and "CALL_PATH" not in kinds:
        missing.append("call_path")
    if req.get("risk_domain_evidence") and not (grounded_domains or known_domains):
        missing.append("risk_domain_evidence")
    if req.get("limitations") and not any(e.get("limitations") for e in index["evidence"]):
        missing.append("limitations")
    return (len(missing) == 0), missing


def check_stale(target, change_id):
    path = os.path.join(ch._change_dir(target, change_id), "evidence.yaml")
    if not os.path.isfile(path):
        return {"change_id": change_id, "stale": []}
    index = _load_yaml(path)
    stale = []
    for e in index.get("evidence", []):
        ss = e.get("source_state") or {}
        rel = ss.get("rel_path")
        expected = ss.get("file_hash")
        if rel and expected:
            full = os.path.join(target, rel)
            if not os.path.isfile(full) or _sha256_file(full) != expected:
                stale.append(e["id"])
    return {"change_id": change_id, "stale": stale}


@coord.coordinated_change_mutator("CHANGE_GROUND")
def change_ground(target, change_id, ae_root=None, limits=None):
    ae_root = ae_root or aeh_paths.ae_root()
    try:
        d = doc.run_doctor(target, ae_root)
        if d["overall"] == "BLOCKED":
            return {"status": "BLOCKED_DOCTOR", "change_id": change_id,
                    "blocking": [c["check_id"] for c in d["checks"] if c["status"] == "BLOCKED"]}
        change = ch.load_change(target, change_id)
        if change["state"]["current"] == "INTAKE":
            tr0 = ch.change_transition(target, change_id, "CLASSIFY")
            if tr0["status"] != "TRANSITION_OK":
                return {"status": "BLOCKED_CHANGE_STATE", "change_id": change_id,
                        "state": "INTAKE", "transition": tr0}
            change = ch.load_change(target, change_id)
        if change["state"]["current"] not in ("CLASSIFY", "GROUND"):
            return {"status": "BLOCKED_CHANGE_STATE", "change_id": change_id,
                    "state": change["state"]["current"]}
        rules = _load_yaml(os.path.join(ae_root, "bootstrap", "grounding.yaml"))
        level = change.get("workflow", {}).get("level")
        if level == "DIRECT":
            return {"status": "GROUNDING_NOT_REQUIRED", "change_id": change_id, "level": level}
        index, grounded_domains = build_evidence(target, change, ae_root, limits)
        known = domains_of(change.get("classification", {}))
        satisfied, missing = gate_sufficient(level, index, grounded_domains, known, rules)
        cdir = ch._change_dir(target, change_id)
        coord.atomic_write_text(
            os.path.join(cdir, "evidence.yaml"), _dump_yaml(index))
        md_lines = ["# Grounding Evidence", "", "machine truth in evidence.yaml", ""]
        for e in index["evidence"]:
            md_lines.append("- " + e["id"] + " [" + e["type"] + "] " + e["finding"])
        coord.atomic_write_text(
            os.path.join(cdir, "evidence.md"), "\n".join(md_lines) + "\n")
        new_domains = sorted(set(grounded_domains) - set(known))
        escalated = False
        if new_domains and level != "CRITICAL":
            escalated = True
            if isinstance(change.get("classification"), str):
                change["classification"] = {"level": change["classification"], "reasons": []}
            change["classification"]["level"] = "CRITICAL"
            change["classification"]["escalated"] = True
            change["classification"]["reasons"] = list(change["classification"].get("reasons", [])) + ["grounding_escalation: " + d for d in new_domains]
            change["classification"]["evidence"] = list(change["classification"].get("evidence", [])) + [{"kind": "repository_evidence", "domain": d, "confidence": "direct"} for d in new_domains]
            ewf, lv = ch._workflow_for(target, "CRITICAL")
            change["workflow"] = {"level": "CRITICAL", "phases": list(lv["phases"])}
            level = "CRITICAL"
            satisfied, missing = gate_sufficient(level, index, grounded_domains, known + new_domains, rules)
        if satisfied:
            change["gates"] = dict(change.get("gates") or {})
            change["gates"]["grounding"] = "PASS"
            ch.save_change(target, change)
            if change["state"]["current"] == "CLASSIFY":
                tr = ch.change_transition(target, change_id, "GROUND")
                if tr["status"] != "TRANSITION_OK":
                    return {"status": "GROUNDING_COMPLETE_BUT_TRANSITION_FAILED", "change_id": change_id,
                            "transition": tr}
            return {"status": "GROUNDING_COMPLETE", "change_id": change_id, "level": level,
                    "evidence_count": len(index["evidence"]), "escalated": escalated,
                    "gate": "PASS", "state": "GROUND"}
        ch.save_change(target, change)
        return {"status": "GROUNDING_INCOMPLETE", "change_id": change_id, "level": level,
                "missing": missing, "evidence_count": len(index["evidence"]), "gate": "PENDING"}
    except (GroundingError, ch.ChangeError, jsonschema.ValidationError) as e:
        return {"status": "GROUNDING_FAILED", "change_id": change_id, "error": str(e)}
