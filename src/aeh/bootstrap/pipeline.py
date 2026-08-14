"""AEH Bootstrap Install Pipeline（Phase 6）

AEH 第一次正式写用户仓库：写盘安全优先于功能数量。

- --dry-run：完整计算 + Install Plan + 零写盘；
- Install Plan 确定性：content_hash 只取 semantic 字段（剔除 scanned_at/answered_at/installed_at）；
- manifest.installed_at 仅首次安装写入；重复 Bootstrap 不得因时间产生 diff；
- Apply：stage → validate staged → atomic per-file replace + 失败回滚（用户原文不丢失）；
- 失败绝不返回 BOOTSTRAP_COMPLETE；
- minimum disclosure：私有正文不进 AGENTS/CLAUDE/profile/plan。

不实现：doctor、Runtime Change Workflow、change new、CI Gate、Approval Enforcement、
chmod/ACL、upgrade。
"""
import copy
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone

import jsonschema
import yaml

from .. import compiler as cm
from .. import conflict as cf
from .. import discovery as disc
from .. import interview as iv
from ..adapters import render as ar

CONTRACT = "bootstrap.install-plan"
CONTRACT_VERSION = 1
HARNESS_NAME = "adaptive-engineering-harness"
HARNESS_VERSION = "0.1.0"
COMPILER_VERSION = "0.1.0"
SCHEMA_VERSION = "1"
GITIGNORE_ENTRY = ".aeh/private/"

MANAGED_BEGIN = "<!-- AEH:BEGIN MANAGED -->"
MANAGED_END = "<!-- AEH:END MANAGED -->"

SEMANTIC_STRIP_KEYS = {"scanned_at", "answered_at", "installed_at", "recompiled_at"}


class BootstrapError(ValueError):
    pass


def _default_root():
    # src/aeh/bootstrap/pipeline.py -> 4 层到项目根
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def _load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _dump_yaml(obj):
    return yaml.safe_dump(obj, sort_keys=True, allow_unicode=True)


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _strip_timestamps(obj):
    """深拷贝并剔除非语义时间字段。"""
    if isinstance(obj, dict):
        return {k: _strip_timestamps(v) for k, v in obj.items() if k not in SEMANTIC_STRIP_KEYS}
    if isinstance(obj, list):
        return [_strip_timestamps(v) for v in obj]
    return obj


def semantic_hash(obj):
    """确定性语义哈希：与时间字段无关。"""
    return _sha256(json.dumps(_strip_timestamps(obj), sort_keys=True, ensure_ascii=False, default=str).encode("utf-8"))


def _path_safe(target, rel):
    if os.path.isabs(rel):
        return None
    norm = os.path.normpath(rel)
    if norm == ".." or norm.startswith(".." + os.sep) or ".." + os.sep in norm:
        return None
    return os.path.join(target, norm)


def tree_digest(root, rel_globs):
    """对 root 下匹配 rel_globs 的文件做确定性 digest（同 discovery ruleset 公式）。"""
    parts = []
    for rel in rel_globs:
        path = os.path.join(root, rel)
        if not os.path.isfile(path):
            continue
        with open(path, "rb") as f:
            parts.append(rel + "\0" + _sha256(f.read()))
    return _sha256(("\n".join(sorted(parts))).encode("utf-8"))


def merge_gitignore(existing_text, entry=GITIGNORE_ENTRY):
    """幂等合并 .gitignore 条目；保留原内容；不重复插入。"""
    existing = existing_text or ""
    lines = existing.splitlines()
    if any(line.strip() == entry for line in lines):
        return existing
    tail = existing.rstrip("\n")
    return (tail + "\n\n" if tail else "") + entry + "\n"


def load_answers(path):
    if not path or not os.path.isfile(path):
        return {"contract": "bootstrap.interview.answers", "version": 1, "answers": {}, "reset": []}
    data = _load_yaml(path)
    schema = _load_yaml(os.path.join(_default_root(), "schemas", "answers.schema.json"))
    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as e:
        raise BootstrapError("BOOTSTRAP_FAILED_VALIDATION: answers schema: " + e.message)
    return data


def compute_digests(ae_root):
    def dir_digest(folders, exts):
        parts = []
        for folder in folders:
            for dp, _, fns in os.walk(os.path.join(ae_root, folder)):
                for fn in sorted(fns):
                    if fn.endswith(exts):
                        rel = os.path.relpath(os.path.join(dp, fn), ae_root)
                        with open(os.path.join(dp, fn), "rb") as f:
                            parts.append(rel.replace(os.sep, "/") + "\0" + _sha256(f.read()))
        return _sha256(("\n".join(sorted(parts))).encode("utf-8"))
    runtime = dir_digest(["core", "schemas"], (".yaml", ".json"))
    compiler = tree_digest(ae_root, ["src/aeh/compiler.py", "src/aeh/conflict.py",
                                     "src/aeh/discovery.py", "src/aeh/interview.py",
                                     "src/aeh/adapters/render.py"])
    bootstrap_contract = dir_digest(["bootstrap"], (".yaml",))
    adapters = dir_digest(["adapters"], (".yaml", ".md"))
    return {"runtime": runtime, "compiler": compiler, "bootstrap_contract": bootstrap_contract, "adapters": adapters}


def build_manifest_base(source_revision, digests):
    return {
        "harness": {"name": HARNESS_NAME, "version": HARNESS_VERSION, "source_revision": source_revision},
        "compiler": {"version": COMPILER_VERSION},
        "schema": {"version": SCHEMA_VERSION},
        "source_hashes": digests,
    }


def build_staged(target, ae_root, profile, ewf, discovery_out, answers, codex_out, claude_out,
                 pending_questions, source_revision, digests):
    """返回 {relpath: {kind, content}} 与 plan 操作列表（确定性，语义哈希）。"""
    staged = {}
    ops = []

    def add(path, kind, content, action, reason, semantic_obj):
        staged[path] = {"kind": kind, "content": content}
        h = semantic_hash(semantic_obj) if kind == "file" else None
        ops.append({"action": action, "path": path, "reason": reason,
                    "content_hash": h, "kind": "file" if kind == "file" else "directory"})

    manifest_base = build_manifest_base(source_revision, digests)
    add(".aeh/manifest.yaml", "file", manifest_base, "CREATE", "manifest (installed_at written at apply)", manifest_base)
    add(".aeh/profile.yaml", "file", profile, "CREATE", "compiled project profile", profile)
    add(".aeh/effective-workflow.yaml", "file", ewf, "CREATE", "compiled effective workflow", ewf)
    add(".aeh/bootstrap/discovery.yaml", "file", discovery_out, "CREATE", "repository discovery facts", discovery_out)
    add(".aeh/bootstrap/answers.yaml", "file", answers, "CREATE", "interview answers", answers)
    conflicts = {"contract": "bootstrap.conflicts", "version": 1, "conflicts": profile.get("conflicts", [])}
    add(".aeh/bootstrap/conflicts.yaml", "file", conflicts, "CREATE", "conflict records", conflicts)
    report = {"contract": "bootstrap.compiler-report", "version": 1,
              "profile_status": profile.get("status"),
              "pending_questions": pending_questions}
    add(".aeh/bootstrap/compiler-report.yaml", "file", report, "CREATE", "compiler report", report)
    add(".aeh/private/", "dir", None, "CREATE", "private policy boundary (gitignored)", None)
    add(".aeh/changes/", "dir", None, "CREATE", "per-change workspaces", None)
    # runtime snapshot（core + schemas；skills 尚无内容，不创建空目录）
    runtime_files = []
    for folder, exts in (("core", (".yaml",)), ("schemas", (".json",))):
        src_dir = os.path.join(ae_root, folder)
        for fname in sorted(os.listdir(src_dir)):
            if fname.endswith(exts):
                rel = ".aeh/runtime/" + folder + "/" + fname
                with open(os.path.join(src_dir, fname), "rb") as f:
                    content = f.read()
                staged[rel] = {"kind": "file", "content": content}
                runtime_files.append(rel)
    for rel in runtime_files:
        ops.append({"action": "INSTALL_RUNTIME", "path": rel, "reason": "versioned runtime snapshot",
                    "content_hash": _sha256(staged[rel]["content"]), "kind": "file"})
    # managed sections（apply 时再与现有内容合并）
    add("AGENTS.md", "managed", codex_out["managed_section"], "REPLACE_MANAGED_SECTION",
        "codex managed section", codex_out["managed_section"])
    add("CLAUDE.md", "managed", claude_out["managed_section"], "REPLACE_MANAGED_SECTION",
        "claude managed section", claude_out["managed_section"])
    add(".gitignore", "gitignore", GITIGNORE_ENTRY, "UPDATE_GITIGNORE", "ignore .aeh/private/", GITIGNORE_ENTRY)
    return staged, ops


def validate_plan(plan, schema_path):
    schema = _load_yaml(schema_path or os.path.join(_default_root(), "schemas", "install-plan.schema.json"))
    jsonschema.validate(plan, schema)
    for op in plan["operations"]:
        _path_safe(plan["target"], op["path"])


def apply_staged(target, staged, ops):
    """stage 校验通过后原子 apply：逐文件 os.replace；失败回滚，用户原文不丢失。"""
    journal = []  # (path, original_bytes | None)
    created = []
    try:
        for op in ops:
            rel = op["path"]
            entry = staged.get(rel)
            if entry is None:
                continue
            dest = os.path.join(target, rel)
            kind = entry["kind"]
            if kind == "dir":
                os.makedirs(dest, exist_ok=True)
                continue
            if kind == "file":
                content = entry["content"]
                if isinstance(content, dict):
                    content = _dump_yaml(content).encode("utf-8")
                elif isinstance(content, str):
                    content = content.encode("utf-8")
                if os.path.isfile(dest) and open(dest, "rb").read() == content:
                    continue  # 相同内容：不制造无意义写
                if op["action"] == "CREATE" and os.path.isfile(dest):
                    continue  # 已存在：幂等跳过（installed_at 等由首装保留）
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                backup = open(dest, "rb").read() if os.path.isfile(dest) else None
                tmp = dest + ".aeh-tmp"
                with open(tmp, "wb") as f:
                    f.write(content)
                os.replace(tmp, dest)
                journal.append((dest, backup))
                created.append(dest)
            elif kind == "managed":
                dest = os.path.join(target, rel)
                existing = ""
                if os.path.isfile(dest):
                    with open(dest, "r", encoding="utf-8") as fh:
                        existing = fh.read()
                merged = ar.merge_managed_section(existing, entry["content"])
                backup = existing if os.path.isfile(dest) else None
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                tmp = dest + ".aeh-tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    f.write(merged)
                os.replace(tmp, dest)
                journal.append((dest, backup))
                created.append(dest)
            elif kind == "gitignore":
                dest = os.path.join(target, rel)
                existing = ""
                if os.path.isfile(dest):
                    with open(dest, "r", encoding="utf-8") as fh:
                        existing = fh.read()
                merged = merge_gitignore(existing, entry["content"])
                backup = existing if os.path.isfile(dest) else None
                tmp = dest + ".aeh-tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    f.write(merged)
                os.replace(tmp, dest)
                journal.append((dest, backup))
                created.append(dest)
    except Exception:
        for dest, backup in reversed(journal):
            try:
                if backup is None:
                    if os.path.isfile(dest):
                        os.remove(dest)
                else:
                    tmp = dest + ".aeh-rollback"
                    with open(tmp, "wb") as f:
                        f.write(backup)
                    os.replace(tmp, dest)
            except OSError:
                pass
        raise BootstrapError("BOOTSTRAP_FAILED")


def finalize_manifest(target, source_revision, digests):
    """installed_at 仅首次安装写入；已存在则保留原值（不因时间产生 diff）。"""
    path = os.path.join(target, ".aeh", "manifest.yaml")
    if os.path.isfile(path):
        return None
    base = build_manifest_base(source_revision, digests)
    base["installed_at"] = datetime.now(timezone.utc).isoformat()
    return base


def runtime_digest_at(target):
    root = os.path.join(target, ".aeh", "runtime")
    if not os.path.isdir(root):
        return None
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
                parts.append(folder + "/" + fname + "\0" + _sha256(f.read()))
    return _sha256(("\n".join(sorted(parts))).encode("utf-8"))


def validate_runtime_integrity(target):
    manifest = _load_yaml(os.path.join(target, ".aeh", "manifest.yaml"))
    expected = manifest["source_hashes"]["runtime"]
    actual = runtime_digest_at(target)
    return actual, expected


def post_validate(target):
    checks = {}
    manifest = _load_yaml(os.path.join(target, ".aeh", "manifest.yaml"))
    jsonschema.validate(manifest, _load_yaml(os.path.join(_default_root(), "schemas", "manifest.schema.json")))
    checks["manifest_schema"] = True
    profile = _load_yaml(os.path.join(target, ".aeh", "profile.yaml"))
    jsonschema.validate(profile, _load_yaml(os.path.join(_default_root(), "schemas", "profile.schema.json")))
    checks["profile_schema"] = True
    if profile.get("status") == "BLOCKED":
        raise BootstrapError("BOOTSTRAP_FAILED_VALIDATION: profile BLOCKED")
    ewf = _load_yaml(os.path.join(target, ".aeh", "effective-workflow.yaml"))
    jsonschema.validate(ewf, _load_yaml(os.path.join(_default_root(), "schemas", "effective-workflow.schema.json")))
    checks["effective_workflow_schema"] = True
    actual, expected = validate_runtime_integrity(target)
    if actual != expected:
        raise BootstrapError("BLOCKED_RUNTIME_INTEGRITY")
    checks["runtime_digest"] = True
    for name in ("AGENTS.md", "CLAUDE.md"):
        p = os.path.join(target, name)
        if os.path.isfile(p):
            with open(p, "r", encoding="utf-8") as fh:
                text = fh.read()
            if text.count(MANAGED_BEGIN) != 1 or text.count(MANAGED_END) != 1:
                raise BootstrapError("BOOTSTRAP_FAILED_VALIDATION: " + name)
        checks[name] = True
    gi = os.path.join(target, ".gitignore")
    if os.path.isfile(gi):
        with open(gi, "r", encoding="utf-8") as fh:
            gi_text = fh.read()
        if GITIGNORE_ENTRY not in gi_text:
            raise BootstrapError("BOOTSTRAP_FAILED_VALIDATION: gitignore missing private entry")
    checks["gitignore"] = True
    return checks


def bootstrap(target, answers_path=None, dry_run=False, source_revision="dev", ae_root=None, interview_rules=None):
    """Bootstrap 主入口。返回结构化 report（不抛 BLOCKED，以 status 表达）。"""
    ae_root = ae_root or _default_root()
    try:
        if not os.path.isdir(target):
            raise BootstrapError("target not a directory: " + target)
        questions, _ = iv.load_questions(interview_rules or os.path.join(ae_root, "bootstrap", "interview"))
        rules_dir = os.path.join(ae_root, "bootstrap", "discovery")
        discovery_out = disc.discover(target, rules_dir,
                                      os.path.join(ae_root, "schemas", "discovery-rule.schema.json"))
        answers = load_answers(answers_path)
        prec = cf.load_precedence(os.path.join(ae_root, "core", "precedence.yaml"))
        profile = cm.compile_profile(questions, answers, discovery_out, prec,
                                     multi_fields=disc.collect_multi_fields(rules_dir))
        if profile.get("status") == "BLOCKED":
            return {"status": "BLOCKED_PROFILE_CONFLICT", "target": target, "conflicts": profile["conflicts"]}
        core_workflow = _load_yaml(os.path.join(ae_root, "core", "workflow.yaml"))
        ewf = cm.compile_effective_workflow(core_workflow, profile)
        codex_out = ar.render("codex", profile, ewf)
        claude_out = ar.render("claude", profile, ewf)
        decisions = iv.plan(questions, discovery_out, answers)
        pending = [d for d in decisions if d["decision"] == "ASK"]
        digests = compute_digests(ae_root)
        staged, ops = build_staged(target, ae_root, profile, ewf, discovery_out, answers,
                                   codex_out, claude_out, pending, source_revision, digests)
        plan = {"contract": CONTRACT, "version": CONTRACT_VERSION, "target": target,
                "dry_run": dry_run, "operations": ops}
        validate_plan(plan, None)
        if dry_run:
            return {"status": "PLAN_READY", "target": target, "plan": plan,
                    "pending_questions": pending, "runtime_digest": digests["runtime"]}
        manifest_final = finalize_manifest(target, source_revision, digests)
        if manifest_final is not None:
            staged[".aeh/manifest.yaml"] = {"kind": "file", "content": manifest_final}
        apply_staged(target, staged, ops)
        checks = post_validate(target)
        return {"status": "BOOTSTRAP_COMPLETE", "target": target, "plan": plan,
                "validations": checks, "pending_questions": pending}
    except BootstrapError as e:
        return {"status": str(e).split(":")[0] if str(e).startswith(("BLOCKED", "BOOTSTRAP")) else "BOOTSTRAP_FAILED",
                "target": target, "error": str(e)}
    except (ar.AdapterError, cf.CompilerError) as e:
        return {"status": "BOOTSTRAP_FAILED", "target": target, "error": str(e)}