"""Journaled, rollback-aware file transactions for bootstrap, repair, and upgrade."""
import hashlib
import json
import ntpath
import os
import re
from datetime import datetime, timezone

import jsonschema
import yaml

from . import paths as aeh_paths


CONTRACT = "aeh.transaction-journal"
CONTRACT_VERSION = 1
_ID_RE = re.compile(r"^(BST|RPR)-(\d{4})-(\d{4})$")


class TransactionError(RuntimeError):
    """Raised when a transaction cannot safely prepare, apply, or roll back."""


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def plan_digest(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return sha256_bytes(raw.encode("utf-8"))


def _safe_path(target, relative):
    if not isinstance(relative, str) or not relative:
        raise TransactionError("invalid empty transaction path")
    normalized = relative.replace("\\", "/")
    if os.path.isabs(relative) or ntpath.isabs(relative):
        raise TransactionError("absolute transaction path rejected: " + relative)
    if any(part == ".." for part in normalized.split("/")):
        raise TransactionError("transaction path escape rejected: " + relative)
    root = os.path.realpath(target)
    destination = os.path.abspath(os.path.join(target, *normalized.split("/")))
    parent = os.path.realpath(os.path.dirname(destination))
    try:
        if os.path.commonpath([root, parent]) != root:
            raise TransactionError("transaction path escapes target: " + relative)
        if os.path.lexists(destination) and os.path.commonpath([root, os.path.realpath(destination)]) != root:
            raise TransactionError("transaction symlink escapes target: " + relative)
    except ValueError as exc:
        raise TransactionError("transaction path is on a different volume: " + relative) from exc
    if os.path.islink(destination):
        raise TransactionError("transaction refuses symlink target: " + relative)
    return destination


def resolve_path(target, relative):
    """Resolve a transaction path without following a target symlink."""
    return _safe_path(target, relative)


def _state(path):
    if os.path.islink(path):
        raise TransactionError("transaction refuses symlink target: " + path)
    if os.path.isfile(path):
        with open(path, "rb") as stream:
            digest = sha256_bytes(stream.read())
        return {"exists": True, "kind": "file", "sha256": digest}
    if os.path.isdir(path):
        return {"exists": True, "kind": "directory", "sha256": None}
    if os.path.lexists(path):
        raise TransactionError("unsupported filesystem object: " + path)
    return {"exists": False, "kind": None, "sha256": None}


def _desired_state(mutation):
    kind = mutation.get("kind", "file")
    if kind == "directory":
        if mutation.get("content") is not None:
            raise TransactionError("directory mutation cannot carry content")
        return {"exists": True, "kind": "directory", "sha256": None}
    content = mutation.get("content")
    if content is None:
        return {"exists": False, "kind": None, "sha256": None}
    if not isinstance(content, bytes):
        raise TransactionError("file mutation content must be bytes")
    return {"exists": True, "kind": "file", "sha256": sha256_bytes(content)}


def _journal_schema(ae_root=None):
    root = ae_root or aeh_paths.ae_root()
    with open(os.path.join(root, "schemas", "transaction-journal.schema.json"), encoding="utf-8") as stream:
        return json.load(stream)


def _validate_journal(journal, ae_root=None):
    jsonschema.validate(journal, _journal_schema(ae_root))


def _write_journal(path, journal, ae_root=None):
    _validate_journal(journal, ae_root)
    tmp = path + ".aeh-tmp"
    with open(tmp, "w", encoding="utf-8") as stream:
        yaml.safe_dump(journal, stream, sort_keys=True, allow_unicode=True)
    os.replace(tmp, path)


def _transactions_root(target):
    return os.path.join(target, ".aeh", "transactions")


def _allocate_id(target, prefix, now=None):
    year = (now or datetime.now(timezone.utc)).year
    root = _transactions_root(target)
    max_number = 0
    if os.path.isdir(root):
        for name in os.listdir(root):
            match = _ID_RE.match(name)
            if match and match.group(1) == prefix and int(match.group(2)) == year:
                max_number = max(max_number, int(match.group(3)))
    number = max_number + 1
    while os.path.exists(os.path.join(root, "%s-%04d-%04d" % (prefix, year, number))):
        number += 1
    return "%s-%04d-%04d" % (prefix, year, number)


def _prepare(target, mutations):
    prepared = []
    for mutation in mutations:
        relative = mutation["path"].replace("\\", "/")
        destination = _safe_path(target, relative)
        before = _state(destination)
        after = _desired_state(mutation)
        if before == after:
            continue
        if before["exists"] and before["kind"] != after["kind"] and after["exists"]:
            raise TransactionError("transaction type conflict at " + relative)
        prepared.append({**mutation, "path": relative, "destination": destination,
                         "before": before, "after": after})
    return prepared


def _apply_one(item):
    destination = item["destination"]
    after = item["after"]
    if not after["exists"]:
        if os.path.isfile(destination):
            os.remove(destination)
        elif os.path.isdir(destination):
            os.rmdir(destination)
        return
    if after["kind"] == "directory":
        os.makedirs(destination, exist_ok=True)
        return
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    tmp = destination + ".aeh-tmp"
    with open(tmp, "wb") as stream:
        stream.write(item["content"])
    os.replace(tmp, destination)


def _restore_one(target, operation, transaction_dir):
    destination = _safe_path(target, operation["path"])
    before = operation["before"]
    if not before["exists"]:
        if os.path.isfile(destination):
            os.remove(destination)
        elif os.path.isdir(destination):
            os.rmdir(destination)
        return
    if before["kind"] == "directory":
        os.makedirs(destination, exist_ok=True)
        return
    backup_ref = operation.get("backup_ref")
    if not backup_ref:
        raise TransactionError("missing transaction backup for " + operation["path"])
    backup_path = os.path.join(transaction_dir, *backup_ref.split("/"))
    with open(backup_path, "rb") as stream:
        content = stream.read()
    if sha256_bytes(content) != before["sha256"]:
        raise TransactionError("transaction backup digest mismatch for " + operation["path"])
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    tmp = destination + ".aeh-rollback"
    with open(tmp, "wb") as stream:
        stream.write(content)
    os.replace(tmp, destination)


def apply_mutations(target, kind, prefix, mutations, source_plan, ae_root=None, now=None,
                    fail_after=None, _before_operation=None):
    """Apply file mutations after persisting backups and a PREPARED journal."""
    prepared = _prepare(target, mutations)
    if not prepared:
        return None
    transaction_id = _allocate_id(target, prefix, now)
    transaction_dir = os.path.join(_transactions_root(target), transaction_id)
    backups_dir = os.path.join(transaction_dir, "backups")
    os.makedirs(backups_dir, exist_ok=False)
    created_at = (now or datetime.now(timezone.utc)).isoformat()
    operations = []
    for index, item in enumerate(prepared, 1):
        operations.append({
            "index": index,
            "action": item["action"],
            "path": item["path"],
            "reason": item.get("reason", ""),
            "before": item["before"],
            "after": item["after"],
            "status": "PENDING",
        })
    journal = {
        "contract": CONTRACT,
        "version": CONTRACT_VERSION,
        "transaction_id": transaction_id,
        "kind": kind,
        "target": os.path.abspath(target),
        "plan_digest": plan_digest(source_plan),
        "status": "PREPARING",
        "created_at": created_at,
        "operations": operations,
    }
    journal_path = os.path.join(transaction_dir, "journal.yaml")
    _write_journal(journal_path, journal, ae_root)
    for item, operation in zip(prepared, operations):
        if item["before"]["kind"] == "file":
            backup_ref = "backups/%04d.bin" % operation["index"]
            backup_path = os.path.join(transaction_dir, *backup_ref.split("/"))
            with open(item["destination"], "rb") as source, open(backup_path, "wb") as backup:
                content = source.read()
                if sha256_bytes(content) != item["before"]["sha256"]:
                    raise TransactionError("BLOCKED_APPLY_DRIFT: " + item["path"])
                backup.write(content)
            operation["backup_ref"] = backup_ref
    journal["status"] = "PREPARED"
    _write_journal(journal_path, journal, ae_root)

    applied = []
    try:
        journal["status"] = "APPLYING"
        _write_journal(journal_path, journal, ae_root)
        for item, operation in zip(prepared, operations):
            if _before_operation is not None:
                _before_operation(item, operation)
            if _state(item["destination"]) != item["before"]:
                raise TransactionError("BLOCKED_APPLY_DRIFT: " + item["path"])
            _apply_one(item)
            if _state(item["destination"]) != item["after"]:
                raise TransactionError("post-write digest mismatch at " + item["path"])
            operation["status"] = "APPLIED"
            applied.append(operation)
            _write_journal(journal_path, journal, ae_root)
            if fail_after is not None and len(applied) >= fail_after:
                raise TransactionError("injected transaction failure")
        journal["status"] = "APPLIED"
        journal["completed_at"] = datetime.now(timezone.utc).isoformat()
        _write_journal(journal_path, journal, ae_root)
        return journal
    except Exception as exc:
        rollback_errors = []
        for operation in reversed(applied):
            try:
                _restore_one(target, operation, transaction_dir)
                operation["status"] = "ROLLED_BACK"
            except Exception as rollback_exc:
                rollback_errors.append(str(rollback_exc))
        journal["status"] = "APPLY_FAILED" if rollback_errors else "APPLY_FAILED_ROLLED_BACK"
        journal["error"] = str(exc) + (("; rollback: " + "; ".join(rollback_errors)) if rollback_errors else "")
        journal["completed_at"] = datetime.now(timezone.utc).isoformat()
        _write_journal(journal_path, journal, ae_root)
        raise TransactionError(journal["error"]) from exc


def load_journal(target, transaction_id, ae_root=None):
    if not _ID_RE.match(transaction_id):
        raise TransactionError("invalid transaction id: " + transaction_id)
    transaction_dir = os.path.join(_transactions_root(target), transaction_id)
    journal_path = os.path.join(transaction_dir, "journal.yaml")
    if not os.path.isfile(journal_path):
        raise TransactionError("transaction journal not found: " + transaction_id)
    with open(journal_path, encoding="utf-8") as stream:
        journal = yaml.safe_load(stream)
    _validate_journal(journal, ae_root)
    return journal, transaction_dir, journal_path


def rollback_transaction(target, transaction_id, ae_root=None, now=None):
    """Roll back an applied or interrupted transaction when all states are known."""
    journal, transaction_dir, journal_path = load_journal(target, transaction_id, ae_root)
    eligible = {"APPLIED", "PREPARING", "PREPARED", "APPLYING", "APPLY_FAILED"}
    if journal["status"] not in eligible:
        raise TransactionError("transaction is not rollback-eligible: " + journal["status"])
    observed = {}
    for operation in journal["operations"]:
        destination = _safe_path(target, operation["path"])
        current = _state(destination)
        observed[operation["index"]] = current
        allowed = (operation["after"],) if journal["status"] == "APPLIED" else (
            operation["before"], operation["after"])
        if current not in allowed:
            raise TransactionError("BLOCKED_ROLLBACK_DRIFT: " + operation["path"])
    for operation in reversed(journal["operations"]):
        if observed[operation["index"]] == operation["after"]:
            _restore_one(target, operation, transaction_dir)
        if _state(_safe_path(target, operation["path"])) != operation["before"]:
            raise TransactionError("rollback verification failed: " + operation["path"])
        operation["status"] = "ROLLED_BACK"
        _write_journal(journal_path, journal, ae_root)
    journal["status"] = "ROLLED_BACK"
    journal["rolled_back_at"] = (now or datetime.now(timezone.utc)).isoformat()
    _write_journal(journal_path, journal, ae_root)
    return journal
