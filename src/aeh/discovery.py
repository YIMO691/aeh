"""AEH Repository Discovery — 最小扫描器（Phase 2 Hardening）

信任/安全/可复现边界：
- 路径防逃逸：所有解析路径必须落在 target repository 内，越界 symlink 不跟随；
- content 证据最小化：只保留 relative path / rule_id / marker_index / match_line / file_hash，
  不保存原始匹配正文；
- 可复现 provenance：scanner_version + ruleset_digest + repository identity(base_commit/dirty)；
- 资源边界：binary/oversized 文件跳过，walk 文件数上限，超限记录 warning；
- 只读：不写任何文件；无网络：不引入任何网络库或调用。

约束：不做 Interview/Conflict/Compiler/Adapter/完整 Bootstrap。
"""
import fnmatch
import hashlib
import os
from datetime import datetime, timezone

import jsonschema
import yaml

CONTRACT = "bootstrap.discovery"
CONTRACT_VERSION = 2
SCANNER_VERSION = "0.2.0"
DOMAINS = ["repository", "testing", "ci", "git", "ai_rules", "architecture"]
CONFIDENCE_LEVELS = ["DETECTED", "INFERRED", "USER_CONFIRMED", "UNKNOWN"]

DEFAULT_LIMITS = {
    "max_content_bytes": 1024 * 1024,   # 1 MiB
    "max_walk_files": 50000,
}

BINARY_PROBE_BYTES = 8192


class DiscoveryError(ValueError):
    pass


def _resolve_within(root, rel):
    """安全解析相对路径：拒绝绝对路径、拒绝 .. 段、拒绝越界（含 symlink 越界）。"""
    if not isinstance(rel, str) or rel == "":
        return None
    if os.path.isabs(rel):
        return None
    norm = os.path.normpath(rel)
    if norm == ".." or norm.startswith(".." + os.sep) or ".." + os.sep in norm:
        return None
    try:
        real_root = os.path.realpath(root)
        real_target = os.path.realpath(os.path.join(root, norm))
        if os.path.commonpath([real_root, real_target]) != real_root:
            return None
    except (OSError, ValueError):
        return None
    return os.path.join(root, norm)


def _sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def _load_rule_schema(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_rules(rules_root, rule_schema_path):
    """加载并校验规则；非法规则直接拒绝（DiscoveryError）。"""
    if not os.path.isdir(rules_root):
        raise DiscoveryError("rules root does not exist: " + rules_root)
    rule_schema = None
    with open(rule_schema_path, "r", encoding="utf-8") as f:
        rule_schema = yaml.safe_load(f)
    rules = []
    digest_parts = []
    for fname in sorted(os.listdir(rules_root)):
        if not fname.endswith(".yaml"):
            continue
        path = os.path.join(rules_root, fname)
        with open(path, "rb") as f:
            raw = f.read()
        digest_parts.append(fname + "\0" + _sha256_bytes(raw))
        try:
            rule = yaml.safe_load(raw)
        except yaml.YAMLError as e:
            raise DiscoveryError("invalid rule yaml " + fname + ": " + str(e))
        try:
            jsonschema.validate(rule, rule_schema)
        except jsonschema.ValidationError as e:
            raise DiscoveryError("invalid rule " + fname + ": " + e.message)
        rules.append(rule)
    digest = _sha256_bytes(("\n".join(sorted(digest_parts))).encode("utf-8"))
    return rules, digest


def _is_binary(path, limits):
    try:
        if os.path.getsize(path) > limits["max_content_bytes"]:
            return True
        with open(path, "rb") as f:
            head = f.read(BINARY_PROBE_BYTES)
        return b"\x00" in head
    except OSError:
        return True


def _content_match(root, marker, ctx, limits):
    rel = marker["path"]
    target = _resolve_within(root, rel)
    if target is None or not os.path.isfile(target):
        if any(ch in rel for ch in "*?["):
            # glob 形式的 content 路径：取第一个安全命中文件
            for dp, dns, fns in os.walk(root):
                if ".git" in dp or ".aeh" in dp:
                    continue
                ctx["walk_files"] += 1
                if ctx["walk_files"] > limits["max_walk_files"]:
                    ctx["warnings"].append({"code": "resource_limit", "detail": "max_walk_files exceeded"})
                    return False, {}
                for fn in fns:
                    full = os.path.join(dp, fn)
                    rel_hit = os.path.relpath(full, root)
                    if fnmatch.fnmatch(rel_hit, rel) and _resolve_within(root, rel_hit):
                        target = full
                        break
        if target is None or not os.path.isfile(target):
            return False, {}
    if _is_binary(target, limits):
        return False, {}
    try:
        with open(target, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError:
        return False, {}
    needle = marker.get("contains", "")
    idx = text.find(needle)
    if idx < 0:
        return False, {}
    line = text[:idx].count("\n") + 1
    with open(target, "rb") as fh:
        file_hash = _sha256_bytes(fh.read())
    evidence = {
        "type": "content",
        "path": os.path.relpath(target, root),
        "rule_id": ctx.get("rule_id"),
        "marker_index": ctx.get("marker_index"),
        "match_line": line,
        "file_hash": file_hash,
    }
    return True, evidence


def _match_marker(root, marker, ctx, limits):
    kind = marker["type"]
    if kind == "file":
        target = _resolve_within(root, marker["path"])
        if target is None or not os.path.isfile(target):
            return False, {}
        return True, {"type": "file", "path": marker["path"], "detail": "file exists"}
    if kind == "dir":
        target = _resolve_within(root, marker["path"])
        if target is None or not os.path.isdir(target):
            return False, {}
        return True, {"type": "dir", "path": marker["path"], "detail": "dir exists"}
    if kind == "glob":
        hits = []
        for dp, dns, fns in os.walk(root):
            if ".git" in dp or ".aeh" in dp:
                continue
            ctx["walk_files"] += len(fns)
            if ctx["walk_files"] > limits["max_walk_files"]:
                ctx["warnings"].append({"code": "resource_limit", "detail": "max_walk_files exceeded"})
                break
            for fn in fns:
                rel = os.path.relpath(os.path.join(dp, fn), root)
                if fnmatch.fnmatch(rel, marker["pattern"]) and _resolve_within(root, rel):
                    hits.append(rel)
        if not hits:
            return False, {}
        return True, {"type": "glob", "path": hits[0],
                      "detail": str(len(hits)) + " match(es) for " + marker["pattern"]}
    if kind == "content":
        return _content_match(root, marker, ctx, limits)
    return False, {}


def _git_identity(root):
    """只读本地 git 信息（无网络）；不可用时返回 null。"""
    try:
        import subprocess
        base = subprocess.run(["git", "-C", root, "rev-parse", "HEAD"],
                              capture_output=True, text=True, timeout=5)
        status = subprocess.run(["git", "-C", root, "status", "--porcelain"],
                                capture_output=True, text=True, timeout=5)
        return {
            "base_commit": base.stdout.strip() or None,
            "dirty": bool(status.stdout.strip()),
        }
    except Exception:
        return {"base_commit": None, "dirty": None}




def collect_multi_fields(rules_root):
    """收集规则中声明为 multi-valued 的 field（domain.field），用于编译器折叠事实。"""
    out = []
    if not os.path.isdir(rules_root):
        return out
    for fname in sorted(os.listdir(rules_root)):
        if not fname.endswith(".yaml"):
            continue
        with open(os.path.join(rules_root, fname), "r", encoding="utf-8") as f:
            rule = yaml.safe_load(f)
        for field in rule.get("multi_fields", []):
            out.append(rule["domain"] + "." + field)
    return sorted(set(out))
def discover(repository_root, rules_root, rule_schema_path=None, limits=None):
    """扫描仓库，返回 discovery.yaml 结构（dict）。只读、无网络。"""
    if not os.path.isdir(repository_root):
        raise DiscoveryError("repository root does not exist: " + repository_root)
    if rule_schema_path is None:
        rule_schema_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "schemas", "discovery-rule.schema.json")
    limits = dict(DEFAULT_LIMITS if limits is None else {**DEFAULT_LIMITS, **limits})
    rules, digest = _load_rules(rules_root, rule_schema_path)
    ctx = {"walk_files": 0, "warnings": []}
    facts = []
    unknowns = []
    counter = 0

    for domain_rule in rules:
        domain = domain_rule["domain"]
        matched_fields = set()
        for detector in domain_rule.get("detectors", []):
            markers = detector.get("markers", [])
            match_mode = detector.get("match", "any")
            evidence = []
            for mi, m in enumerate(markers):
                ctx["rule_id"] = detector["id"]
                ctx["marker_index"] = mi
                ok, ev = _match_marker(repository_root, m, ctx, limits)
                if ok:
                    evidence.append(ev)
            if match_mode == "all":
                matched = len(evidence) == len(markers)
            else:
                matched = len(evidence) > 0
            if matched:
                counter += 1
                facts.append({
                    "id": "F-%03d" % counter,
                    "domain": domain,
                    "field": detector["field"],
                    "value": detector["value"],
                    "confidence": detector.get("confidence", "DETECTED"),
                    "evidence": evidence,
                })
                matched_fields.add(detector["field"])
        for field in domain_rule.get("unknown_fields", []):
            if field not in matched_fields:
                unknowns.append({"domain": domain, "field": field, "reason": "no_markers_matched"})

    git_id = _git_identity(repository_root)
    return {
        "contract": CONTRACT,
        "version": CONTRACT_VERSION,
        "scanner_version": SCANNER_VERSION,
        "ruleset_digest": digest,
        "repository_root": repository_root,
        "repository": {"root": repository_root, "base_commit": git_id["base_commit"], "dirty": git_id["dirty"]},
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "facts": facts,
        "unknowns": unknowns,
        "warnings": ctx["warnings"],
    }