"""AEH Profile / Workflow Compiler（Phase 4）

职责：Normalize → Resolve → Compile。
- Profile Compiler：输入 Discovery + Interview Answers + Harness Defaults，
  输出符合 schemas/profile.schema.json 的数据模型（不写盘）。
- Workflow Compiler：输入 core/workflow.yaml + compiled profile，
  输出符合 schemas/effective-workflow.schema.json 的数据模型；绝不修改 core/workflow.yaml。
- 确定性：只读 semantic 字段；scanned_at/answered_at 不参与编译。
- 最小披露：private ref 只进 source.ref，绝不携带正文。
"""
import os

import yaml

from . import conflict as cf


DEFAULT_LEVEL = "STANDARD"

# field 前缀 → profile 分区路由（CD-019）
ROUTES = [
    ("permissions.", "permissions", lambda rest: rest),
    ("developer.", "developer", lambda rest: rest),
    ("testing.", "testing", lambda rest: rest),
    ("review.", "review", lambda rest: rest),
    ("team.", "team", lambda rest: rest),
    ("organization.", "organization", lambda rest: rest),
    ("workflow.default_level", "workflow", lambda rest: "default_level"),
    ("repository.language", "project", lambda rest: "languages"),
]


def _default_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _provenance(record, shadowed_records=None):
    entry = {
        "value": record["value"],
        "source": {"type": record["source"], "ref": record["origin_ref"]},
        "confidence": record["confidence"],
        "type": record["type"],
    }
    if shadowed_records:
        entry["shadowed"] = [
            {"type": r["source"], "ref": r["origin_ref"]} for r in shadowed_records
        ]
    return entry


def _route_field(field, entry, profile):
    for prefix, section, rest_fn in ROUTES:
        if field == prefix.rstrip(".") or field.startswith(prefix):
            rest = field[len(prefix):] if field.startswith(prefix) else ""
            key = rest_fn(rest)
            if section == "project" and key == "languages":
                langs = profile.setdefault("project", {}).setdefault("languages", [])
                if entry["value"] not in [i["value"] for i in langs if isinstance(i, dict)]:
                    langs.append(entry)
                profile["project"]["languages"] = sorted(langs, key=lambda i: i["value"] if isinstance(i, dict) else str(i))
                return
            target = profile.setdefault(section, {})
            if key == "human_required_for":
                target[key] = [entry]
            else:
                target[key] = entry
            return
    # 未路由字段（含 FACT 事实）：进 top-level facts，避免污染政策分区（CD-020）
    profile.setdefault("facts", {})[field] = entry


def compile_profile(questions, answers, discovery, precedence_order,
                    harness_defaults=None, repository_name=None, multi_fields=None):
    """编译 profile 数据模型；同级冲突字段被排除在 effective 分区之外。"""
    records = cf.normalize(questions, answers, discovery, precedence_order, harness_defaults, multi_fields)
    outcome = cf.resolve(records, precedence_order)
    profile = {
        "profile_version": "1.0",
        "project": {"name": repository_name or os.path.basename(os.path.abspath(discovery.get("repository_root", "."))),
                    "languages": []},
        "workflow": {"default_level": DEFAULT_LEVEL},
        "sources": {
            "repository_discovery": {"root": discovery.get("repository_root"),
                                     "ruleset_digest": discovery.get("ruleset_digest"),
                                     "scanner_version": discovery.get("scanner_version")},
            "interview": {"answers_count": len((answers or {}).get("answers", {}))},
        },
        "status": "COMPILED",
        "conflicts": [],
    }
    for field in sorted(outcome["resolved"]):
        record = outcome["resolved"][field]
        shadowed = outcome["shadowed"].get(field, [])
        entry = _provenance(record, shadowed)
        _route_field(field, entry, profile)
    profile["conflicts"] = sorted(outcome["conflicts"], key=lambda c: c["conflict_id"])
    if profile["conflicts"]:
        profile["status"] = "BLOCKED"
    return profile


def compile_effective_workflow(core_workflow, profile, core_revision=None):
    """编译 effective-workflow 数据模型；不修改 core_workflow（只读深拷贝）。"""
    levels = {}
    for lv in core_workflow.get("levels", []):
        levels[lv["id"]] = {
            "phases": list(lv["phases"]),
            "required_artifacts": list(lv.get("required_artifacts", [])),
            "narrative_artifacts": list(lv.get("narrative_artifacts", [])),
        }
        if lv.get("terminal_options"):
            levels[lv["id"]]["terminal_options"] = list(lv["terminal_options"])
    return {
        "workflow_version": "1",
        "default_level": profile.get("workflow", {}).get("default_level", DEFAULT_LEVEL),
        "source": {
            "core_revision": core_revision or ("core.workflow:v" + str(core_workflow.get("version", 1))),
            "profile_ref": ".aeh/profile.yaml",
        },
        "levels": levels,
    }