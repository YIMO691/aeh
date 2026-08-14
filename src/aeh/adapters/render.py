"""AEH Agent Adapters — 纯 Renderer/Translator（Phase 5）

原则（frozen）：
- Adapter 不重算 precedence、不解决 conflict、不修改 Profile/Workflow。
- Profile status=BLOCKED → 拒绝生成（AdapterError: BLOCKED_PROFILE_CONFLICT）。
- 语义决策全部来自 Phase 4 编译结果；本模块只翻译。
- deny 不得被放宽为 ask/allow；required 不得降级为 optional。
- 平台无法表达的 Enforcement 必须记录 unsupported_capabilities（GUIDANCE_ONLY），
  降级合法性由 capability_map 声明，Adapter 自身不决定。
- minimum disclosure：只读取/表达 effective constraint 与 ref ID，不复制私有正文。
- 只读、无网络、不写盘；merge_managed_section 是纯函数。
"""
import copy
import os

import jsonschema
import yaml

CONTRACT = "adapter.render"
DEFAULT_MARKERS = {
    "begin": "<!-- AEH:BEGIN MANAGED -->",
    "end": "<!-- AEH:END MANAGED -->",
}


class AdapterError(ValueError):
    pass


def _default_root():
    # src/aeh/adapters/render.py -> 4 层到项目根
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def _load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _read_text(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def load_adapter(agent, adapter_root=None, adapter_schema_path=None):
    adapter_root = adapter_root or os.path.join(_default_root(), "adapters", agent)
    adapter_schema_path = adapter_schema_path or os.path.join(_default_root(), "schemas", "adapter.schema.json")
    decl = _load_yaml(os.path.join(adapter_root, "adapter.yaml"))
    schema = _load_yaml(adapter_schema_path)
    jsonschema.validate(decl, schema)
    template = _read_text(os.path.join(adapter_root, decl["template"]))
    return decl, template


def _prov(profile, section, key, default):
    entry = (profile or {}).get(section, {}).get(key)
    if isinstance(entry, dict) and "value" in entry:
        return entry["value"]
    if isinstance(entry, list):
        values = [i["value"] if isinstance(i, dict) else i for i in entry]
        return ",".join(sorted(str(v) for v in values))
    return entry if entry is not None else default


def extract_semantics(profile):
    """从 Profile 提取 canonical 有效语义（两平台共用，等价性由构造保证）。只读 semantic 字段。"""
    return {
        "permissions": {
            "modify_source": _prov(profile, "permissions", "modify_source", "ask"),
            "git_commit": _prov(profile, "permissions", "git_commit", "ask"),
            "git_push": _prov(profile, "permissions", "git_push", "deny"),
            "shell": _prov(profile, "permissions", "shell", "ask"),
            "web_access": _prov(profile, "permissions", "web_access", "ask"),
        },
        "testing": {"tdd": _prov(profile, "testing", "tdd", "risk_based")},
        "review": {"human_required_for": _prov(profile, "review", "human_required_for", "critical")},
        "workflow": {"default_level": _prov(profile, "workflow", "default_level", "STANDARD")},
        "developer": {"plan_before_code": _prov(profile, "developer", "plan_before_code", "risk_based")},
        "team": {"code_review_policy": _prov(profile, "team", "code_review_policy", "major")},
    }


_PERMISSION_LABELS = {
    "modify_source": "modify source files",
    "git_commit": "git commit",
    "git_push": "git push",
    "shell": "run shell commands",
    "web_access": "network / web access",
}


def _permission_expression(agent, field, value):
    """平台表达：不改变语义；deny 永远输出 deny 级表达。"""
    label = _PERMISSION_LABELS.get(field, field)
    if agent == "codex":
        if value == "allow":
            return {"instruction": "ALLOWED: agent may " + label + "."}
        if value == "ask":
            return {"instruction": "ASK: agent must request approval before: " + label + "."}
        return {"instruction": "DENY: agent must NOT " + label + " (do not bypass)."}
    # claude
    if field == "modify_source":
        rules = {"Edit", "Write"}
    elif field == "git_commit":
        rules = {"Bash(git commit:*)"}
    elif field == "git_push":
        rules = {"Bash(git push:*)"}
    elif field == "shell":
        rules = {"Bash"}
    else:
        rules = set()
    bucket = {"allow": "allow", "ask": "ask", "deny": "deny"}[value]
    expr = {"allow": [], "ask": [], "deny": []}
    if rules:
        expr[bucket] = sorted(rules)
    else:
        expr[bucket] = ["instruction: " + label]
    return expr


def render(agent, profile, effective_workflow, manifest=None, adapter_root=None):
    """渲染单个 Adapter 输出（纯函数，输入不被修改）。"""
    if (profile or {}).get("status") == "BLOCKED":
        raise AdapterError("BLOCKED_PROFILE_CONFLICT")
    decl, template = load_adapter(agent, adapter_root)
    semantics = extract_semantics(profile)

    permission_mapping = []
    unsupported = []
    for key, value in semantics["permissions"].items():
        field = "permissions." + key
        cap = decl["capability_map"].get(field, {"channel": "instruction", "status": "GUIDANCE_ONLY"})
        permission_mapping.append({
            "field": field,
            "value": value,
            "channel": cap["channel"],
            "status": cap["status"],
            "expression": _permission_expression(agent, key, value),
        })
        if value == "deny" and cap["status"] != "ENFORCEABLE":
            unsupported.append({"field": field, "required_semantic": "deny",
                                "adapter": agent, "status": cap["status"]})
    review_value = semantics["review"]["human_required_for"]
    if review_value != "none":
        cap = decl["capability_map"].get("review.human_required_for",
                                         {"channel": "instruction", "status": "GUIDANCE_ONLY"})
        unsupported.append({"field": "review.human_required_for",
                            "required_semantic": "required:" + str(review_value),
                            "adapter": agent, "status": cap["status"]})

    summary_lines = []
    for key, value in sorted(semantics["permissions"].items()):
        summary_lines.append("- " + key + ": " + str(value))
    summary_lines.append("- review.human_required_for: " + str(review_value))
    summary_lines.append("- testing.tdd: " + str(semantics["testing"]["tdd"]))
    summary_lines.append("- team.code_review_policy: " + str(semantics["team"]["code_review_policy"]))
    summary_lines.append("- developer.plan_before_code: " + str(semantics["developer"]["plan_before_code"]))

    tcb = "\n".join("- " + item for item in decl.get("tcb_notice", []))
    managed = template
    managed = managed.replace("{{PERMISSION_SUMMARY}}", "\n".join(summary_lines))
    managed = managed.replace("{{DEFAULT_LEVEL}}", str(semantics["workflow"]["default_level"]))
    managed = managed.replace("{{TCB_NOTICE}}", tcb)

    output = {
        "adapter": agent,
        "status": "RENDERED",
        "managed_section": managed,
        "permission_mapping": permission_mapping,
        "semantics": semantics,
        "diagnostics": {"unsupported_capabilities": unsupported},
    }
    out_schema = _load_yaml(os.path.join(_default_root(), "schemas", "adapter-output.schema.json"))
    jsonschema.validate(output, out_schema)
    return output


def merge_managed_section(existing_text, generated_section, markers=None):
    """纯函数 merge：保留用户原文；幂等；malformed markers → AdapterError（不静默覆盖）。"""
    markers = markers or DEFAULT_MARKERS
    begin, end = markers["begin"], markers["end"]
    existing = existing_text or ""
    has_begin = begin in existing
    has_end = end in existing
    if has_begin != has_end:
        raise AdapterError("MALFORMED_MANAGED_MARKERS")
    if not has_begin:
        tail = existing.rstrip("\n")
        return (tail + "\n\n" if tail else "") + begin + "\n" + generated_section + "\n" + end + "\n"
    if existing.count(begin) != 1 or existing.count(end) != 1:
        raise AdapterError("MALFORMED_MANAGED_MARKERS")
    b = existing.index(begin)
    e = existing.index(end)
    if e < b:
        raise AdapterError("MALFORMED_MANAGED_MARKERS")
    prefix = existing[:b]
    suffix = existing[e + len(end):]
    return prefix + begin + "\n" + generated_section + "\n" + end + suffix