"""AEH Doctor — observe / validate / diagnose（Phase 7）

Doctor 只读：不写 .aeh/、不修改任何用户文件、不自动修复、无网络。
发现 staging/journal/partial 残留只报告（BLOCKED_INCOMPLETE_INSTALL），不删除。

职责边界（frozen）：
- Validator 不得基于被篡改的 runtime contract 声明 READY（digest 不一致 → BLOCKED_RUNTIME_INTEGRITY）。
- GUIDANCE_ONLY capability → WARN；UNENFORCEABLE 且语义为 deny → BLOCKED（按 Contract）。
- 环境检查诚实降级（UNKNOWN_ENVIRONMENT / 不可用），不猜测、不安装、不联网。
- Doctor evidence 不回显 private 原文。
"""
import json
import os
import shutil
from datetime import datetime, timezone

import jsonschema
import yaml

from .. import paths as aeh_paths

CONTRACT = "doctor.report"
CONTRACT_VERSION = 1
HARNESS_VERSION = "0.1.0"
SCHEMA_VERSION = "1"
MANAGED_BEGIN = "<!-- AEH:BEGIN MANAGED -->"
MANAGED_END = "<!-- AEH:END MANAGED -->"
GITIGNORE_ENTRY = ".aeh/private/"


class DoctorError(ValueError):
    pass


def _load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _check(check_id, domain, status, message, evidence=None, remediation=None):
    return {"check_id": check_id, "domain": domain, "status": status,
            "message": message, "evidence": evidence or [], "remediation": remediation or ""}


def _overall(checks):
    if any(c["status"] == "BLOCKED" for c in checks):
        return "BLOCKED"
    if any(c["status"] == "WARN" for c in checks):
        return "READY_WITH_WARNINGS"
    return "READY"


def _runtime_digest(target):
    root = os.path.join(target, ".aeh", "runtime")
    if not os.path.isdir(root):
        return None
    import hashlib
    parts = []
    for folder in ("core", "schemas"):
        d = os.path.join(root, folder)
        if not os.path.isdir(d):
            continue
        for fname in sorted(os.listdir(d)):
            p = os.path.join(d, fname)
            if not os.path.isfile(p):
                continue
            with open(p, "rb") as f:
                parts.append(folder + "/" + fname + "\0" + hashlib.sha256(f.read()).hexdigest())
    return hashlib.sha256(("\n".join(sorted(parts))).encode("utf-8")).hexdigest()


def _managed_status(text):
    if MANAGED_BEGIN not in text and MANAGED_END not in text:
        return "absent"
    if text.count(MANAGED_BEGIN) != 1 or text.count(MANAGED_END) != 1:
        return "malformed"
    if text.index(MANAGED_END) < text.index(MANAGED_BEGIN):
        return "malformed"
    return "ok"


def _load_adapter_decls(ae_root, overrides=None):
    decls = {}
    for agent in ("codex", "claude"):
        decl = _load_yaml(os.path.join(ae_root, "adapters", agent, "adapter.yaml"))
        if overrides and agent in overrides:
            for field, patch in overrides[agent].items():
                decl.setdefault("capability_map", {})[field] = {**decl["capability_map"].get(field, {}), **patch}
        decls[agent] = decl
    return decls


def _prov_value(profile, section, key):
    entry = (profile or {}).get(section, {}).get(key)
    if isinstance(entry, dict) and "value" in entry:
        return entry["value"]
    if isinstance(entry, list):
        return ",".join(sorted(str(i["value"] if isinstance(i, dict) else i) for i in entry))
    return entry


def run_doctor(target, ae_root=None, which=None, capability_overrides=None, now=None):
    ae_root = ae_root or aeh_paths.ae_root()
    which = which or shutil.which
    checks = []

    # ---- INSTALL 域 ----
    aeh_dir = os.path.join(target, ".aeh")
    if not os.path.isdir(target):
        checks.append(_check("install.target", "install", "BLOCKED", "target is not a directory",
                             [target], "verify target path"))
        return _report(target, checks, now)
    if not os.path.isdir(aeh_dir):
        checks.append(_check("install.aeh_exists", "install", "BLOCKED", ".aeh/ does not exist",
                             [aeh_dir], "run aeh bootstrap <target>"))
        return _report(target, checks, now)
    for rel, cid in (("manifest.yaml", "install.manifest"), ("profile.yaml", "install.profile"),
                     ("effective-workflow.yaml", "install.effective_workflow")):
        p = os.path.join(aeh_dir, rel)
        if os.path.isfile(p):
            checks.append(_check(cid, "install", "PASS", rel + " present", [p]))
        else:
            checks.append(_check(cid, "install", "BLOCKED", "missing " + rel,
                                 [p], "re-run aeh bootstrap"))
    runtime_dir = os.path.join(aeh_dir, "runtime")
    if os.path.isdir(runtime_dir):
        checks.append(_check("install.runtime_dir", "install", "PASS", "runtime/ present", [runtime_dir]))
    else:
        checks.append(_check("install.runtime_dir", "install", "BLOCKED", "runtime/ missing",
                             [runtime_dir], "re-run aeh bootstrap"))

    # staging / journal / partial 残留（RISK-INSTALL-CRASH-001 的发现路径）
    residues = []
    for dp, _, fns in os.walk(target):
        for fn in fns:
            if fn.endswith(".aeh-tmp") or fn.endswith(".aeh-rollback"):
                residues.append(os.path.relpath(os.path.join(dp, fn), target))
    if residues:
        checks.append(_check("install.staging_residue", "install", "BLOCKED",
                             "BLOCKED_INCOMPLETE_INSTALL: staging/journal residue found",
                             sorted(residues), "manual review; repair command 属后续阶段"))
    else:
        checks.append(_check("install.staging_residue", "install", "PASS", "no staging residue"))

    # ---- CONTRACT / RUNTIME INTEGRITY ----
    manifest_path = os.path.join(aeh_dir, "manifest.yaml")
    manifest = None
    if os.path.isfile(manifest_path):
        try:
            manifest = _load_yaml(manifest_path)
            jsonschema.validate(manifest, _load_yaml(os.path.join(ae_root, "schemas", "manifest.schema.json")))
            checks.append(_check("contract.manifest_schema", "contract", "PASS", "manifest schema valid"))
        except Exception as e:
            checks.append(_check("contract.manifest_schema", "contract", "BLOCKED",
                                 "manifest invalid: " + str(e)[:200], [manifest_path]))
    if manifest is not None:
        hv = manifest.get("harness", {}).get("version")
        sv = manifest.get("schema", {}).get("version")
        if hv == HARNESS_VERSION and sv == SCHEMA_VERSION:
            checks.append(_check("contract.version_compat", "contract", "PASS",
                                 "harness/schema version compatible", ["harness=" + str(hv), "schema=" + str(sv)]))
        else:
            checks.append(_check("contract.version_compat", "contract", "BLOCKED",
                                 "BLOCKED_VERSION_INCOMPATIBLE: harness=" + str(hv) + " schema=" + str(sv),
                                 [], "upgrade 属后续阶段"))
        expected_runtime = manifest.get("source_hashes", {}).get("runtime")
        actual_runtime = _runtime_digest(target)
        if actual_runtime == expected_runtime:
            checks.append(_check("contract.runtime_digest", "contract", "PASS",
                                 "runtime snapshot digest matches manifest", [actual_runtime]))
        else:
            checks.append(_check("contract.runtime_digest", "contract", "BLOCKED",
                                 "BLOCKED_RUNTIME_INTEGRITY: runtime contract may be tampered",
                                 ["expected=" + str(expected_runtime), "actual=" + str(actual_runtime)],
                                 "re-run aeh bootstrap; 不得基于被篡改契约继续 READY"))
        # core contract readability
        try:
            for fname in sorted(os.listdir(os.path.join(runtime_dir, "core"))):
                if fname.endswith(".yaml"):
                    _load_yaml(os.path.join(runtime_dir, "core", fname))
            checks.append(_check("contract.core_readable", "contract", "PASS", "runtime core contracts readable"))
        except Exception as e:
            checks.append(_check("contract.core_readable", "contract", "BLOCKED",
                                 "runtime core contract unreadable: " + str(e)[:200]))
        try:
            for fname in sorted(os.listdir(os.path.join(runtime_dir, "schemas"))):
                if fname.endswith(".json"):
                    _load_json(os.path.join(runtime_dir, "schemas", fname))
            checks.append(_check("contract.schemas_valid", "contract", "PASS", "runtime schemas are valid JSON"))
        except Exception as e:
            checks.append(_check("contract.schemas_valid", "contract", "BLOCKED",
                                 "runtime schema invalid: " + str(e)[:200]))

    # ---- PROFILE / WORKFLOW ----
    profile = None
    profile_path = os.path.join(aeh_dir, "profile.yaml")
    if os.path.isfile(profile_path):
        try:
            profile = _load_yaml(profile_path)
            jsonschema.validate(profile, _load_yaml(os.path.join(ae_root, "schemas", "profile.schema.json")))
            checks.append(_check("profile.schema", "profile", "PASS", "profile schema valid"))
        except Exception as e:
            checks.append(_check("profile.schema", "profile", "BLOCKED",
                                 "profile schema invalid: " + str(e)[:200], [profile_path]))
        if profile is not None:
            if profile.get("status") == "BLOCKED":
                checks.append(_check("profile.status", "profile", "BLOCKED", "BLOCKED_PROFILE",
                                     [], "resolve conflicts and re-bootstrap"))
            else:
                checks.append(_check("profile.status", "profile", "PASS", "profile not blocked"))
            unresolved = [c for c in profile.get("conflicts", []) if c.get("status") == "BLOCKED_POLICY_CONFLICT"]
            if unresolved:
                checks.append(_check("profile.conflicts", "profile", "BLOCKED",
                                     "unresolved BLOCKED_POLICY_CONFLICT: " + str(len(unresolved)),
                                     [c.get("field", "") for c in unresolved], "authorized policy authority 裁决后重编译"))
            else:
                checks.append(_check("profile.conflicts", "profile", "PASS", "no unresolved conflicts"))
            prov_missing = []
            for section in ("permissions", "developer", "testing"):
                for key, entry in (profile.get(section) or {}).items():
                    if isinstance(entry, dict) and ("source" not in entry or "confidence" not in entry):
                        prov_missing.append(section + "." + key)
            if prov_missing:
                checks.append(_check("profile.provenance", "profile", "WARN",
                                     "provenance incomplete for: " + ", ".join(sorted(prov_missing)),
                                     [], "re-bootstrap to regenerate provenance"))
            else:
                checks.append(_check("profile.provenance", "profile", "PASS", "key provenance complete"))
    ewf_path = os.path.join(aeh_dir, "effective-workflow.yaml")
    if os.path.isfile(ewf_path):
        try:
            ewf = _load_yaml(ewf_path)
            jsonschema.validate(ewf, _load_yaml(os.path.join(ae_root, "schemas", "effective-workflow.schema.json")))
            checks.append(_check("workflow.schema", "profile", "PASS", "effective-workflow schema valid"))
        except Exception as e:
            checks.append(_check("workflow.schema", "profile", "BLOCKED",
                                 "effective-workflow invalid: " + str(e)[:200], [ewf_path]))

    # ---- ADAPTER 域 ----
    for name in ("AGENTS.md", "CLAUDE.md"):
        p = os.path.join(target, name)
        cid = "adapter." + ("agents" if name == "AGENTS.md" else "claude") + "_managed"
        if os.path.isfile(p):
            with open(p, "r", encoding="utf-8") as f:
                status = _managed_status(f.read())
            if status == "ok":
                checks.append(_check(cid, "adapters", "PASS", name + " managed section valid"))
            else:
                checks.append(_check(cid, "adapters", "BLOCKED",
                                     "malformed managed block in " + name + " (" + status + ")",
                                     [p], "re-run aeh bootstrap"))
        else:
            checks.append(_check(cid, "adapters", "WARN", name + " missing (adapter not installed)",
                                 [], "re-run aeh bootstrap"))
    # capability 语义检查（deny 不得被静默放宽）
    if profile is not None:
        decls = _load_adapter_decls(ae_root, capability_overrides)
        from ..adapters import render as ar
        semantics = ar.extract_semantics(profile)
        for agent, decl in decls.items():
            guidance, unenforceable = [], []
            for key, value in semantics["permissions"].items():
                field = "permissions." + key
                cap = decl["capability_map"].get(field, {"channel": "instruction", "status": "GUIDANCE_ONLY"})
                if value == "deny":
                    if cap["status"] == "UNENFORCEABLE":
                        unenforceable.append(field)
                    elif cap["status"] == "GUIDANCE_ONLY":
                        guidance.append(field)
            if unenforceable:
                checks.append(_check("adapter." + agent + ".capabilities", "adapters", "BLOCKED",
                                     "required enforcement unavailable (deny + UNENFORCEABLE): " + ", ".join(unenforceable),
                                     [], "按 Contract 阻塞，不得放宽 deny"))
            elif guidance:
                checks.append(_check("adapter." + agent + ".capabilities", "adapters", "WARN",
                                     "guidance-only deny fields for " + agent + ": " + ", ".join(guidance),
                                     [], "后续 Enforcement Phase 可升级"))
            else:
                checks.append(_check("adapter." + agent + ".capabilities", "adapters", "PASS",
                                     "no guidance-only deny fields for " + agent))

    # ---- PRIVATE / SECURITY ----
    gi_path = os.path.join(target, ".gitignore")
    if os.path.isfile(gi_path):
        with open(gi_path, "r", encoding="utf-8") as f:
            gi_text = f.read()
        if GITIGNORE_ENTRY in gi_text:
            checks.append(_check("private.gitignore", "private", "PASS", ".aeh/private/ gitignored"))
        else:
            checks.append(_check("private.gitignore", "private", "BLOCKED",
                                 ".aeh/private/ not covered by .gitignore", [gi_path],
                                 "add \".aeh/private/\" to .gitignore"))
    else:
        checks.append(_check("private.gitignore", "private", "WARN",
                             ".gitignore absent; .aeh/private/ coverage unknown", [], "create .gitignore"))
    private_dir = os.path.join(aeh_dir, "private")
    if os.path.isdir(private_dir):
        names = sorted(os.listdir(private_dir))
        if names:
            checks.append(_check("private.presence", "private", "WARN",
                                 "private files present (" + str(len(names)) + "); contents not inspected",
                                 [], "keep local-only"))
        else:
            checks.append(_check("private.presence", "private", "PASS", "private dir empty"))
    # 不回显 private 原文：本函数从不读取 private 文件内容（结构上保证）

    # ---- ENVIRONMENT ----
    git_path = which("git")
    if git_path:
        checks.append(_check("env.git", "environment", "PASS", "git available", [git_path]))
    else:
        checks.append(_check("env.git", "environment", "WARN",
                             "UNKNOWN_ENVIRONMENT: git not found on PATH (no fabrication)",
                             [], "install git or treat git-dependent checks as unavailable"))

    return _report(target, checks, now)


def _report(target, checks, now):
    return {
        "contract": CONTRACT,
        "version": CONTRACT_VERSION,
        "target": target,
        "scanned_at": (now or datetime.now(timezone.utc)).isoformat(),
        "overall": _overall(checks),
        "checks": checks,
    }


def runtime_preflight(doctor_result, profile=None, workflow=None):
    """纯逻辑：ready/blocked 决策。不创建 CHG、不修改任何东西。"""
    blocking = [c for c in doctor_result.get("checks", []) if c["status"] == "BLOCKED"]
    warnings = [c for c in doctor_result.get("checks", []) if c["status"] == "WARN"]
    if profile is not None and profile.get("status") == "BLOCKED":
        blocking.append({"check_id": "preflight.profile", "domain": "preflight",
                         "status": "BLOCKED", "message": "BLOCKED_PROFILE"})
    if workflow is None:
        warnings.append({"check_id": "preflight.workflow", "domain": "preflight",
                         "status": "WARN", "message": "workflow not provided to preflight"})
    verdict = "BLOCKED" if blocking else ("READY_WITH_WARNINGS" if warnings else "READY")
    return {"contract": "runtime.preflight", "version": 1, "verdict": verdict,
            "blocking_checks": blocking, "warnings": warnings}
