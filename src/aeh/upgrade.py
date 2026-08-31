"""Plan-first runtime snapshot upgrade with manifest merge and safe rollback."""
import copy
import json
import os
import re

import jsonschema
import yaml

from . import paths as aeh_paths
from . import transaction as tx
from .bootstrap import pipeline as bp
from .doctor import doctor as doc


CONTRACT = "upgrade.plan"
CONTRACT_VERSION = 1
_VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:\.dev(\d+))?$")


class UpgradeError(RuntimeError):
    """Raised when an upgrade cannot be planned or applied safely."""


def _load_yaml(path):
    with open(path, "r", encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def _load_json(path):
    with open(path, "r", encoding="utf-8") as stream:
        return json.load(stream)


def _read_bytes(path):
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as stream:
        return stream.read()


def _version(value):
    match = _VERSION_RE.match(str(value))
    if not match:
        raise UpgradeError("BLOCKED_UPGRADE_UNSUPPORTED_VERSION: " + str(value))
    major, minor, patch, dev = match.groups()
    # Keep comparison deterministic without adding a packaging dependency.
    # A development build precedes the matching final release:
    # 0.2.1 < 0.3.0.dev0 < 0.3.0.dev1 < 0.3.0.
    release_rank = 1 if dev is None else 0
    dev_number = 0 if dev is None else int(dev)
    return int(major), int(minor), int(patch), release_rank, dev_number


def _endpoint(version, revision, digest):
    return {
        "harness_version": str(version),
        "source_revision": str(revision),
        "runtime_digest": str(digest).lower(),
    }


def _load_policy(ae_root):
    path = os.path.join(ae_root, "bootstrap", "upgrade", "policy.yaml")
    policy = _load_yaml(path)
    schema = _load_json(os.path.join(ae_root, "schemas", "upgrade-policy.schema.json"))
    jsonschema.validate(policy, schema)
    return policy


def _preflight(target):
    if not os.path.isdir(target):
        raise UpgradeError("BLOCKED_UPGRADE_TARGET: target is not a directory")
    for relative in (".aeh/manifest.yaml", ".aeh/runtime", ".aeh/runtime/core",
                     ".aeh/runtime/schemas"):
        tx.resolve_path(target, relative)
    runtime = os.path.join(target, ".aeh", "runtime")
    if os.path.isdir(runtime):
        for directory, names, files in os.walk(runtime, followlinks=False):
            if os.path.islink(directory):
                raise UpgradeError("BLOCKED_UPGRADE_UNSAFE_PATH: " + os.path.relpath(directory, target))
            for name in names + files:
                path = os.path.join(directory, name)
                if os.path.islink(path):
                    raise UpgradeError("BLOCKED_UPGRADE_UNSAFE_PATH: " + os.path.relpath(path, target))


def _operation(target, action, relative, policy, reason, content, source_ref):
    destination = tx.resolve_path(target, relative)
    before = _read_bytes(destination)
    public = {
        "action": action,
        "path": relative,
        "policy": policy,
        "reason": reason,
        "before_hash": tx.sha256_bytes(before) if before is not None else None,
        "after_hash": tx.sha256_bytes(content) if content is not None else None,
        "source_ref": source_ref,
    }
    mutation = {
        "action": action,
        "path": relative,
        "kind": "file",
        "content": content,
        "reason": reason,
    }
    return public, mutation


def _updated_manifest(manifest, source, destination, digests):
    updated = copy.deepcopy(manifest)
    updated.setdefault("harness", {})
    updated["harness"].update({
        "name": bp.HARNESS_NAME,
        "version": destination["harness_version"],
        "source_revision": destination["source_revision"],
    })
    updated.setdefault("compiler", {})["version"] = bp.COMPILER_VERSION
    updated.setdefault("schema", {})["version"] = bp.SCHEMA_VERSION
    updated["source_hashes"] = copy.deepcopy(digests)
    entry = {"from": source, "to": destination}
    history = list(updated.get("upgrade_history") or [])
    if not history or history[-1] != entry:
        history.append(entry)
    updated["upgrade_history"] = history
    return updated


def _build_plan(target, apply, destination_revision, ae_root):
    _preflight(target)
    policy = _load_policy(ae_root)
    managed = {item["path"]: item["strategy"] for item in policy["managed_paths"]}
    if managed.get(".aeh/runtime/") != "overwrite" or \
            managed.get(".aeh/manifest.yaml") != "merge":
        raise UpgradeError("BLOCKED_UPGRADE_POLICY: managed path strategies are incomplete")
    destination_revision = str(destination_revision).strip()
    if not destination_revision:
        raise UpgradeError("BLOCKED_UPGRADE_DESTINATION_REVISION: empty revision")
    manifest_path = tx.resolve_path(target, ".aeh/manifest.yaml")
    if not os.path.isfile(manifest_path):
        raise UpgradeError("BLOCKED_UPGRADE_MANIFEST_MISSING")
    manifest_bytes = _read_bytes(manifest_path)
    try:
        manifest = yaml.safe_load(manifest_bytes.decode("utf-8"))
        jsonschema.validate(manifest, _load_json(os.path.join(ae_root, "schemas", "manifest.schema.json")))
        source_name = manifest["harness"]["name"]
        source_version = manifest["harness"]["version"]
        installed_revision = str(manifest["harness"]["source_revision"])
        expected_runtime = str(manifest["source_hashes"]["runtime"]).lower()
    except (UnicodeError, KeyError, TypeError, jsonschema.ValidationError) as exc:
        raise UpgradeError("BLOCKED_UPGRADE_MANIFEST_INVALID: " + str(exc)) from exc
    if source_name != bp.HARNESS_NAME:
        raise UpgradeError("BLOCKED_UPGRADE_FOREIGN_HARNESS: " + str(source_name))

    actual_runtime = bp.runtime_digest_at(target)
    if actual_runtime is None or actual_runtime.lower() != expected_runtime:
        raise UpgradeError("BLOCKED_UPGRADE_SOURCE_INTEGRITY")

    destination_digests = bp.compute_digests(ae_root)
    destination_runtime = destination_digests["runtime"].lower()
    source_semver = _version(source_version)
    destination_semver = _version(bp.HARNESS_VERSION)
    if source_semver > destination_semver:
        raise UpgradeError("BLOCKED_UPGRADE_DOWNGRADE: %s -> %s" %
                           (source_version, bp.HARNESS_VERSION))
    if source_semver == destination_semver and expected_runtime != destination_runtime:
        raise UpgradeError("BLOCKED_UPGRADE_VERSION_COLLISION: %s" % source_version)

    source = _endpoint(source_version, installed_revision, expected_runtime)
    destination = _endpoint(bp.HARNESS_VERSION, destination_revision, destination_runtime)
    if source_semver == destination_semver and expected_runtime == destination_runtime:
        plan = {
            "contract": CONTRACT,
            "version": CONTRACT_VERSION,
            "target": os.path.abspath(target),
            "dry_run": not apply,
            "source": source,
            "destination": copy.deepcopy(source),
            "preserve_paths": policy["preserve_paths"],
            "operations": [],
        }
        jsonschema.validate(
            plan, _load_json(os.path.join(ae_root, "schemas", "upgrade-plan.schema.json")))
        return plan, []
    public = []
    mutations = []
    canonical = bp.canonical_runtime_files(ae_root)
    runtime_root = tx.resolve_path(target, ".aeh/runtime")
    for runtime_relative, content in canonical.items():
        relative = ".aeh/runtime/" + runtime_relative
        current = _read_bytes(os.path.join(target, *relative.split("/")))
        if current == content:
            continue
        action = "INSTALL_RUNTIME" if current is None else "REPLACE_RUNTIME"
        operation, mutation = _operation(
            target, action, relative, managed[".aeh/runtime/"],
            "install destination runtime snapshot",
            content, "package:" + runtime_relative)
        public.append(operation)
        mutations.append(mutation)
    for folder in ("core", "schemas"):
        actual_dir = os.path.join(runtime_root, folder)
        if not os.path.isdir(actual_dir):
            continue
        for name in sorted(os.listdir(actual_dir)):
            path = os.path.join(actual_dir, name)
            runtime_relative = folder + "/" + name
            if os.path.isfile(path) and runtime_relative not in canonical:
                relative = ".aeh/runtime/" + runtime_relative
                operation, mutation = _operation(
                    target, "REMOVE_RUNTIME", relative, "remove",
                    "remove file outside destination runtime snapshot", None,
                    "package:runtime-manifest")
                public.append(operation)
                mutations.append(mutation)

    updated_manifest = _updated_manifest(manifest, source, destination, destination_digests)
    updated_manifest_bytes = yaml.safe_dump(
        updated_manifest, sort_keys=True, allow_unicode=True).encode("utf-8")
    if updated_manifest_bytes != manifest_bytes:
        operation, mutation = _operation(
            target, "MERGE_MANIFEST", ".aeh/manifest.yaml", managed[".aeh/manifest.yaml"],
            "preserve install metadata and record destination source manifest",
            updated_manifest_bytes, "package:manifest+upgrade-history")
        public.append(operation)
        mutations.append(mutation)

    plan = {
        "contract": CONTRACT,
        "version": CONTRACT_VERSION,
        "target": os.path.abspath(target),
        "dry_run": not apply,
        "source": source,
        "destination": destination,
        "preserve_paths": policy["preserve_paths"],
        "operations": public,
    }
    jsonschema.validate(plan, _load_json(os.path.join(ae_root, "schemas", "upgrade-plan.schema.json")))
    return plan, mutations


def run_upgrade(target, apply=False, source_revision="dev", ae_root=None, _fail_after=None):
    """Build an upgrade plan and apply it only after explicit authorization."""
    ae_root = ae_root or aeh_paths.ae_root()
    try:
        plan, mutations = _build_plan(target, apply, source_revision, ae_root)
        if not mutations:
            return {"status": "UPGRADE_NOOP", "target": target, "plan": plan,
                    "doctor": doc.run_doctor(target, ae_root)}
        if not apply:
            return {"status": "UPGRADE_PLAN_READY", "target": target, "plan": plan}
        from .runtime import coordination as coord
        coord.assert_workspace_maintenance_allowed(target)
        journal = tx.apply_mutations(target, "upgrade", "UPG", mutations, plan, ae_root,
                                     fail_after=_fail_after)
        after = doc.run_doctor(target, ae_root)
        status = "UPGRADE_APPLIED" if after["overall"] != "BLOCKED" else "UPGRADE_APPLIED_WITH_BLOCKERS"
        return {"status": status, "target": target, "transaction_id": journal["transaction_id"],
                "plan": plan, "doctor": after}
    except (UpgradeError, tx.TransactionError, jsonschema.ValidationError,
            OSError, ValueError) as exc:
        status = str(exc).split(":")[0] if str(exc).startswith("BLOCKED_") else "UPGRADE_FAILED"
        return {"status": status, "target": target, "error": str(exc)}


def rollback(target, transaction_id, ae_root=None):
    ae_root = ae_root or aeh_paths.ae_root()
    try:
        from .runtime import coordination as coord
        drain = coord.coordination_drain_status(target)
        if drain["status"] != "COORDINATION_DRAINED":
            raise coord.CoordinationError(drain["status"])
        coord.assert_workspace_maintenance_allowed(target)
        journal = tx.rollback_transaction(target, transaction_id, ae_root)
        return {"status": "UPGRADE_ROLLED_BACK", "target": target,
                "transaction_id": transaction_id, "journal": journal,
                "doctor": doc.run_doctor(target, ae_root)}
    except (tx.TransactionError, OSError, jsonschema.ValidationError) as exc:
        status = str(exc).split(":")[0] if str(exc).startswith("BLOCKED_") else "UPGRADE_ROLLBACK_FAILED"
        return {"status": status, "target": target, "transaction_id": transaction_id,
                "error": str(exc)}
