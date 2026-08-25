"""Controller-owned checkpoints for change-scoped machine truth.

The checkpoint is established at RED/LOCK_TEST, before the coding agent starts,
and deliberately stored outside the governed repository. A hash written next to
the artifacts would only prove that the same workspace writer changed both
files; it would not establish an ownership boundary.
"""
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone


CONTRACT = "aeh.controller-checkpoint"
VERSION = 1
STATE_DIR_ENV = "AEH_CONTROLLER_STATE_DIR"
_CHANGE_ID_RE = re.compile(r"^CHG-\d{4}-\d{4}$")


class OwnershipError(ValueError):
    """Raised when machine truth is outside the last Controller checkpoint."""


def _canonical(path):
    return os.path.normcase(os.path.realpath(os.path.abspath(path)))


def _default_state_root():
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if not base:
            base = os.path.join(os.path.expanduser("~"), "AppData", "Local")
        return os.path.join(base, "AEH", "controller-state-v1")
    base = os.environ.get("XDG_STATE_HOME")
    if not base:
        base = os.path.join(os.path.expanduser("~"), ".local", "state")
    return os.path.join(base, "aeh", "controller-state-v1")


def state_root(target):
    """Resolve a durable state root and reject roots inside the agent workspace."""
    root = _canonical(os.environ.get(STATE_DIR_ENV) or _default_state_root())
    governed = _canonical(target)
    try:
        inside_target = os.path.commonpath([root, governed]) == governed
    except ValueError as exc:
        raise OwnershipError("BLOCKED_CONTROLLER_STATE_PATH: " + root) from exc
    if inside_target:
        raise OwnershipError(
            "BLOCKED_CONTROLLER_STATE_INSIDE_TARGET: " + root
        )
    return root


def _checkpoint_path(target, change_id):
    if not _CHANGE_ID_RE.fullmatch(change_id or ""):
        raise OwnershipError("BLOCKED_INVALID_CHANGE_ID: " + str(change_id))
    repo_id = hashlib.sha256(_canonical(target).encode("utf-8")).hexdigest()
    return os.path.join(state_root(target), repo_id, change_id + ".json")


def _machine_truth_snapshot(target, change_id):
    cdir = os.path.join(target, ".aeh", "changes", change_id)
    if not os.path.isdir(cdir):
        raise OwnershipError("BLOCKED_CHANGE_WORKSPACE_MISSING: " + change_id)
    snapshot = {}
    for current, dirs, files in os.walk(cdir, followlinks=False):
        for name in dirs:
            path = os.path.join(current, name)
            if os.path.islink(path):
                rel = os.path.relpath(path, cdir).replace(os.sep, "/")
                raise OwnershipError("BLOCKED_MACHINE_TRUTH_SYMLINK: " + rel)
        dirs[:] = sorted(dirs)
        for name in sorted(files):
            if not name.lower().endswith((".yaml", ".yml", ".json")):
                continue
            path = os.path.join(current, name)
            if os.path.islink(path):
                rel = os.path.relpath(path, cdir).replace(os.sep, "/")
                raise OwnershipError("BLOCKED_MACHINE_TRUTH_SYMLINK: " + rel)
            rel = os.path.relpath(path, cdir).replace(os.sep, "/")
            with open(path, "rb") as stream:
                snapshot[rel] = hashlib.sha256(stream.read()).hexdigest()
    return snapshot


def _write_json_atomic(path, body):
    parent = os.path.dirname(path)
    os.makedirs(parent, mode=0o700, exist_ok=True)
    tmp = path + ".aeh-tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as stream:
        json.dump(body, stream, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    os.replace(tmp, path)


def ensure_state_available(target, change_id):
    """Prove the external Controller store is writable before workspace mutation."""
    path = _checkpoint_path(target, change_id)
    parent = os.path.dirname(path)
    probe = None
    try:
        os.makedirs(parent, mode=0o700, exist_ok=True)
        descriptor, probe = tempfile.mkstemp(prefix=".aeh-probe-", dir=parent)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(b"controller-state-probe\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.remove(probe)
        return path
    except OSError as exc:
        if probe and os.path.isfile(probe):
            try:
                os.remove(probe)
            except OSError:
                pass
        raise OwnershipError(
            "BLOCKED_CONTROLLER_CHECKPOINT_UNAVAILABLE: " + str(exc)
        ) from exc


def record_checkpoint(target, change_id):
    """Seal the current Controller-produced change truth outside ``target``."""
    path = ensure_state_available(target, change_id)
    try:
        body = {
            "contract": CONTRACT,
            "version": VERSION,
            "target": _canonical(target),
            "change_id": change_id,
            "machine_truth": _machine_truth_snapshot(target, change_id),
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        _write_json_atomic(path, body)
        return body
    except OSError as exc:
        raise OwnershipError(
            "BLOCKED_CONTROLLER_CHECKPOINT_UNAVAILABLE: " + str(exc)
        ) from exc


def checkpoint_exists(target, change_id):
    return os.path.isfile(_checkpoint_path(target, change_id))


def assert_checkpoint(target, change_id):
    """Fail closed when change truth differs from the last Controller snapshot."""
    path = _checkpoint_path(target, change_id)
    if not os.path.isfile(path):
        raise OwnershipError(
            "BLOCKED_CONTROLLER_CHECKPOINT_MISSING: replay RED through governed repair or restart the change"
        )
    try:
        with open(path, "r", encoding="utf-8") as stream:
            saved = json.load(stream)
    except (OSError, ValueError) as exc:
        raise OwnershipError("BLOCKED_CONTROLLER_CHECKPOINT_INVALID") from exc
    if (saved.get("contract") != CONTRACT or saved.get("version") != VERSION or
            saved.get("target") != _canonical(target) or saved.get("change_id") != change_id or
            not isinstance(saved.get("machine_truth"), dict)):
        raise OwnershipError("BLOCKED_CONTROLLER_CHECKPOINT_INVALID")
    expected = saved["machine_truth"]
    actual = _machine_truth_snapshot(target, change_id)
    added = sorted(set(actual) - set(expected))
    removed = sorted(set(expected) - set(actual))
    modified = sorted(name for name in set(actual) & set(expected)
                      if actual[name] != expected[name])
    if added or removed or modified:
        details = []
        if added:
            details.append("added=" + ",".join(added))
        if removed:
            details.append("removed=" + ",".join(removed))
        if modified:
            details.append("modified=" + ",".join(modified))
        raise OwnershipError("BLOCKED_MACHINE_TRUTH_PROVENANCE: " + "; ".join(details))
    return saved
