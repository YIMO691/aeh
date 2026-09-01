"""Plan-first installation repair with journaled apply and drift-safe rollback."""
import json
import os

import jsonschema
import yaml

from . import paths as aeh_paths
from . import transaction as tx
from .adapters import render as ar
from .bootstrap import pipeline as bp
from .doctor import doctor as doc


CONTRACT = "repair.plan"
CONTRACT_VERSION = 1
MANAGED_BEGIN = "<!-- AEH:BEGIN MANAGED -->"
MANAGED_END = "<!-- AEH:END MANAGED -->"


class RepairError(RuntimeError):
    """Raised when a repair cannot be planned or applied safely."""


def _load_yaml(path):
    with open(path, "r", encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def _load_json(path):
    with open(path, "r", encoding="utf-8") as stream:
        return json.load(stream)


def _load_rules(ae_root):
    rules_path = os.path.join(ae_root, "bootstrap", "repair", "rules.yaml")
    rules = _load_yaml(rules_path)
    jsonschema.validate(rules, _load_json(os.path.join(ae_root, "schemas", "repair-rule.schema.json")))
    return rules["rules"]


def _read_bytes(path):
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as stream:
        return stream.read()


def _preflight_target_paths(target):
    sensitive = (".aeh/manifest.yaml", ".aeh/profile.yaml", ".aeh/effective-workflow.yaml",
                 ".aeh/runtime", ".aeh/runtime/core", ".aeh/runtime/schemas",
                 "AGENTS.md", "CLAUDE.md", ".gitignore")
    for relative in sensitive:
        tx.resolve_path(target, relative)
    runtime = os.path.join(target, ".aeh", "runtime")
    if os.path.isdir(runtime):
        for directory, names, files in os.walk(runtime, followlinks=False):
            if os.path.islink(directory):
                raise RepairError("BLOCKED_REPAIR_UNSAFE_PATH: " + os.path.relpath(directory, target))
            for name in names + files:
                path = os.path.join(directory, name)
                if os.path.islink(path):
                    raise RepairError("BLOCKED_REPAIR_UNSAFE_PATH: " + os.path.relpath(path, target))


def _public_operation(action, path, reason, content, source_ref):
    before = _read_bytes(path)
    return {
        "action": action,
        "path": None,
        "reason": reason,
        "before_hash": tx.sha256_bytes(before) if before is not None else None,
        "after_hash": tx.sha256_bytes(content) if content is not None else None,
        "source_ref": source_ref,
    }


def _repair_managed_text(existing, generated):
    """Replace one bounded managed envelope while preserving all exterior text."""
    begin = existing.find(MANAGED_BEGIN)
    if begin < 0:
        return None
    end = existing.find(MANAGED_END, begin + len(MANAGED_BEGIN))
    if end < 0:
        return None
    prefix = existing[:begin].replace(MANAGED_BEGIN, "").replace(MANAGED_END, "")
    suffix = existing[end + len(MANAGED_END):].replace(MANAGED_BEGIN, "").replace(MANAGED_END, "")
    return prefix + MANAGED_BEGIN + "\n" + generated + "\n" + MANAGED_END + suffix


def _matched_actions(doctor_report, rules):
    checks = {check["check_id"]: check for check in doctor_report["checks"]}
    matched = {}
    for rule in rules:
        hits = [checks[check_id] for check_id in rule["check_ids"]
                if check_id in checks and checks[check_id]["status"] in rule["statuses"]]
        if hits:
            matched.setdefault(rule["action"], []).extend(hits)
    return matched


def _add_operation(target, public, mutations, action, relative, reason, content, source_ref):
    destination = tx.resolve_path(target, relative)
    operation = _public_operation(action, destination, reason, content, source_ref)
    operation["path"] = relative
    public.append(operation)
    mutations.append({"action": action, "path": relative, "kind": "file",
                      "content": content, "reason": reason})


def _build_plan(target, apply, ae_root):
    _preflight_target_paths(target)
    doctor_before = doc.run_doctor(target, ae_root)
    rules = _load_rules(ae_root)
    matched = _matched_actions(doctor_before, rules)
    public = []
    mutations = []
    handled = set()
    planning_errors = []

    runtime_hits = matched.get("RESTORE_RUNTIME", [])
    if runtime_hits:
        manifest_path = tx.resolve_path(target, ".aeh/manifest.yaml")
        try:
            manifest = _load_yaml(manifest_path)
            expected_digest = manifest["source_hashes"]["runtime"]
            canonical_digest = bp.compute_digests(ae_root)["runtime"]
            if expected_digest != canonical_digest:
                raise RepairError("BLOCKED_REPAIR_SOURCE_MISMATCH")
            canonical = bp.canonical_runtime_files(ae_root)
            runtime_root = tx.resolve_path(target, ".aeh/runtime")
            for relative_source, content in canonical.items():
                relative_target = ".aeh/runtime/" + relative_source
                current = _read_bytes(os.path.join(target, *relative_target.split("/")))
                if current != content:
                    _add_operation(target, public, mutations, "WRITE_CANONICAL_RUNTIME",
                                   relative_target, "restore canonical runtime file", content,
                                   "package:" + relative_source)
            for folder in ("core", "schemas"):
                actual_dir = os.path.join(runtime_root, folder)
                if os.path.isdir(actual_dir):
                    for name in sorted(os.listdir(actual_dir)):
                        actual_path = os.path.join(actual_dir, name)
                        key = folder + "/" + name
                        if os.path.isfile(actual_path) and key not in canonical:
                            _add_operation(target, public, mutations, "REMOVE_UNEXPECTED_RUNTIME",
                                           ".aeh/runtime/" + key,
                                           "remove file outside manifest runtime snapshot", None,
                                           "manifest:source_hashes.runtime")
            handled.update(check["check_id"] for check in runtime_hits)
        except (OSError, KeyError, TypeError, RepairError) as exc:
            planning_errors.append(str(exc))

    managed_hits = matched.get("REPAIR_MANAGED", [])
    if managed_hits:
        try:
            profile = _load_yaml(tx.resolve_path(target, ".aeh/profile.yaml"))
            workflow = _load_yaml(tx.resolve_path(target, ".aeh/effective-workflow.yaml"))
            for check in managed_hits:
                if check["check_id"] == "adapter.agents_managed":
                    agent, relative = "codex", "AGENTS.md"
                elif check["check_id"] == "adapter.claude_managed":
                    agent, relative = "claude", "CLAUDE.md"
                else:
                    continue
                path = tx.resolve_path(target, relative)
                existing = (_read_bytes(path) or b"").decode("utf-8")
                rendered = ar.render(agent, profile, workflow)["managed_section"]
                repaired = _repair_managed_text(existing, rendered)
                if repaired is None:
                    planning_errors.append("BLOCKED_REPAIR_UNSAFE_MANAGED: " + relative)
                    continue
                _add_operation(target, public, mutations, "REPLACE_MANAGED_SECTION", relative,
                               "replace bounded AEH managed envelope", repaired.encode("utf-8"),
                               "installed-profile+effective-workflow:" + agent)
                handled.add(check["check_id"])
        except (OSError, UnicodeError, KeyError, ar.AdapterError) as exc:
            planning_errors.append("BLOCKED_REPAIR_MANAGED_SOURCE: " + str(exc))

    residue_hits = matched.get("REMOVE_RESIDUE", [])
    for check in residue_hits:
        for relative in sorted(check.get("evidence", [])):
            normalized = relative.replace("\\", "/")
            if normalized == ".aeh/private" or normalized.startswith(".aeh/private/"):
                continue
            if not normalized.endswith((".aeh-tmp", ".aeh-rollback")):
                continue
            path = tx.resolve_path(target, normalized)
            if os.path.isfile(path):
                _add_operation(target, public, mutations, "REMOVE_RESIDUE", normalized,
                               "remove incomplete atomic-write residue after backup", None,
                               "doctor:" + check["check_id"])
        if any(op["action"] == "REMOVE_RESIDUE" for op in public):
            handled.add(check["check_id"])

    gitignore_hits = matched.get("UPDATE_GITIGNORE", [])
    if gitignore_hits:
        relative = ".gitignore"
        path = tx.resolve_path(target, relative)
        existing_bytes = _read_bytes(path)
        existing = existing_bytes.decode("utf-8") if existing_bytes is not None else ""
        updated = bp.merge_gitignore(existing).encode("utf-8")
        if updated != existing_bytes:
            _add_operation(target, public, mutations, "UPDATE_GITIGNORE", relative,
                           "restore .aeh/private/ exclusion", updated,
                           "bootstrap:private-boundary")
        handled.update(check["check_id"] for check in gitignore_hits)

    public_mutations = sorted(zip(public, mutations), key=lambda pair: (pair[0]["path"], pair[0]["action"]))
    public = [pair[0] for pair in public_mutations]
    mutations = [pair[1] for pair in public_mutations]
    blocked = {check["check_id"] for check in doctor_before["checks"] if check["status"] == "BLOCKED"}
    unsupported = sorted(blocked - handled)
    plan = {
        "contract": CONTRACT,
        "version": CONTRACT_VERSION,
        "target": os.path.abspath(target),
        "dry_run": not apply,
        "doctor_overall_before": doctor_before["overall"],
        "repairable_checks": sorted(handled),
        "operations": public,
    }
    jsonschema.validate(plan, _load_json(os.path.join(ae_root, "schemas", "repair-plan.schema.json")))
    return plan, mutations, doctor_before, unsupported, planning_errors


def run_repair(target, apply=False, ae_root=None):
    """Build a repair plan; apply it only when explicitly requested."""
    ae_root = ae_root or aeh_paths.ae_root()
    try:
        plan, mutations, before, unsupported, errors = _build_plan(target, apply, ae_root)
        if errors:
            return {"status": errors[0].split(":")[0], "target": target,
                    "errors": errors, "blocking_checks": unsupported, "plan": plan}
        if unsupported:
            return {"status": "BLOCKED_REPAIR_UNSUPPORTED", "target": target,
                    "blocking_checks": unsupported, "plan": plan}
        if not mutations:
            return {"status": "REPAIR_NOOP", "target": target, "plan": plan,
                    "doctor": before}
        if not apply:
            return {"status": "REPAIR_PLAN_READY", "target": target, "plan": plan}
        from .runtime import coordination as coord
        coord.assert_workspace_maintenance_allowed(target)
        journal = tx.apply_mutations(target, "repair", "RPR", mutations, plan, ae_root)
        after = doc.run_doctor(target, ae_root)
        status = "REPAIR_APPLIED" if after["overall"] != "BLOCKED" else "REPAIR_APPLIED_WITH_BLOCKERS"
        return {"status": status, "target": target, "transaction_id": journal["transaction_id"],
                "plan": plan, "doctor": after}
    except (RepairError, tx.TransactionError, jsonschema.ValidationError, OSError, ValueError) as exc:
        status = str(exc).split(":")[0] if str(exc).startswith("BLOCKED_") else "REPAIR_FAILED"
        return {"status": status, "target": target, "error": str(exc)}


def rollback(target, transaction_id, ae_root=None):
    ae_root = ae_root or aeh_paths.ae_root()
    try:
        from .runtime import coordination as coord
        coord.assert_workspace_maintenance_allowed(target)
        journal = tx.rollback_transaction(target, transaction_id, ae_root)
        return {"status": "REPAIR_ROLLED_BACK", "target": target,
                "transaction_id": transaction_id, "journal": journal,
                "doctor": doc.run_doctor(target, ae_root)}
    except (tx.TransactionError, OSError, jsonschema.ValidationError) as exc:
        status = str(exc).split(":")[0] if str(exc).startswith("BLOCKED_") else "REPAIR_ROLLBACK_FAILED"
        return {"status": status, "target": target, "transaction_id": transaction_id,
                "error": str(exc)}
