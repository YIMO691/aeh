"""Bounded AEH coordination for a single-host local-filesystem.

This module does not provide cross-host or network-filesystem correctness.
M6.3A exposes observation only; lease/reservation mutators remain deferred.
"""
from contextlib import contextmanager
from dataclasses import dataclass
import errno
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import time

import jsonschema

from .. import paths as aeh_paths
from . import ownership


STORE_CONTRACT = "coordination.store"
STORE_VERSION = 1
RECEIPT_CONTRACT = "coordination.receipt"
RECEIPT_VERSION = 1
_CHANGE_ID = __import__("re").compile(r"^CHG-[0-9]{4}-[0-9]{4,}$")
_TEMP_SUFFIXES = (".aeh-tmp", ".aeh-rollback", ".tmp", ".temp")
_MAX_CHANGE_FILES = 10000
_MAX_CHANGE_BYTES = 256 * 1024 * 1024


class CoordinationError(ValueError):
    """Fail-closed coordination error containing a stable, non-secret code."""


@dataclass(frozen=True)
class CoordinationPaths:
    state_root: Path
    repository_dir: Path
    lock: Path
    store: Path
    repository_id_sha256: str
    workspace_id_sha256: str


def _blocked(code):
    return CoordinationError(code)


def _sha256(value):
    return hashlib.sha256(value).hexdigest()


def _canonical_json(body):
    return json.dumps(
        body, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")


def _is_link_or_reparse(path):
    if os.path.islink(path):
        return True
    try:
        attrs = getattr(os.lstat(path), "st_file_attributes", 0)
    except OSError:
        return False
    return bool(attrs & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def _assert_existing_components_safe(path, code):
    absolute = Path(os.path.abspath(os.fspath(path)))
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current = current / part
        if os.path.lexists(current) and _is_link_or_reparse(current):
            raise _blocked(code)


def _safe_directory(path, missing_code="BLOCKED_COORDINATION_TARGET_INVALID"):
    raw = os.fspath(path)
    if (os.name == "nt" and raw.startswith("\\\\")) or raw.startswith("//"):
        raise _blocked("BLOCKED_COORDINATION_NETWORK_PATH")
    _assert_existing_components_safe(raw, "BLOCKED_COORDINATION_REPARSE_PATH")
    canonical = os.path.realpath(os.path.abspath(raw))
    if not os.path.isdir(canonical):
        raise _blocked(missing_code)
    return canonical


def workspace_identity(target):
    canonical = _safe_directory(target)
    return _sha256(("workspace\0" + os.path.normcase(canonical)).encode("utf-8"))


def _git_common_directory(target):
    # AEH is invoked against many bootstrapped non-Git fixtures.  Avoid a
    # process launch unless the target itself has a Git directory/file marker.
    if not os.path.exists(os.path.join(target, ".git")):
        return None
    try:
        result = subprocess.run(
            ["git", "-C", target, "rev-parse", "--path-format=absolute", "--git-common-dir"],
            capture_output=True, text=True, timeout=5, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    if not value:
        return None
    _assert_existing_components_safe(value, "BLOCKED_COORDINATION_REPARSE_PATH")
    return os.path.normcase(os.path.realpath(os.path.abspath(value)))


def repository_identity(target, repository_id=None):
    canonical = _safe_directory(target)
    if repository_id is not None:
        if not isinstance(repository_id, str) or not repository_id or len(repository_id) > 4096:
            raise _blocked("BLOCKED_COORDINATION_REPOSITORY_ID_INVALID")
        material = "explicit\0" + repository_id
    else:
        common = _git_common_directory(canonical)
        material = "git-common-dir\0" + common if common else "directory\0" + os.path.normcase(canonical)
    return _sha256(material.encode("utf-8"))


def _state_root(target, state_root=None):
    try:
        raw = os.fspath(state_root) if state_root is not None else ownership.state_root(target)
    except ownership.OwnershipError:
        raise _blocked("BLOCKED_COORDINATION_STATE_ROOT_INVALID") from None
    if (os.name == "nt" and raw.startswith("\\\\")) or raw.startswith("//"):
        raise _blocked("BLOCKED_COORDINATION_NETWORK_PATH")
    _assert_existing_components_safe(raw, "BLOCKED_COORDINATION_REPARSE_PATH")
    root = os.path.realpath(os.path.abspath(raw))
    governed = os.path.realpath(os.path.abspath(target))
    try:
        inside = os.path.commonpath([root, governed]) == governed
    except ValueError:
        inside = False
    if inside:
        raise _blocked("BLOCKED_COORDINATION_STATE_INSIDE_TARGET")
    return Path(root)


def resolve_store_paths(target, repository_id=None, state_root=None):
    canonical = _safe_directory(target)
    repo_hash = repository_identity(canonical, repository_id=repository_id)
    workspace_hash = workspace_identity(canonical)
    root = _state_root(canonical, state_root=state_root)
    repository_dir = root / "coordination-v1" / "repositories" / repo_hash
    _assert_existing_components_safe(
        repository_dir, "BLOCKED_COORDINATION_REPARSE_PATH")
    return CoordinationPaths(
        state_root=root,
        repository_dir=repository_dir,
        lock=repository_dir / "store.lock",
        store=repository_dir / "store.json",
        repository_id_sha256=repo_hash,
        workspace_id_sha256=workspace_hash,
    )


def _lock_attempt(stream, shared):
    if os.name == "nt":
        import msvcrt
        stream.seek(0)
        mode = msvcrt.LK_NBRLCK if shared else msvcrt.LK_NBLCK
        msvcrt.locking(stream.fileno(), mode, 1)
    else:
        import fcntl
        mode = fcntl.LOCK_SH if shared else fcntl.LOCK_EX
        fcntl.flock(stream.fileno(), mode | fcntl.LOCK_NB)


def _lock_release(stream):
    if os.name == "nt":
        import msvcrt
        stream.seek(0)
        msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


@contextmanager
def repository_lock(target, repository_id=None, state_root=None, shared=True,
                    timeout_seconds=5.0, create=False):
    if not isinstance(timeout_seconds, (int, float)) or timeout_seconds < 0 or timeout_seconds > 300:
        raise _blocked("BLOCKED_COORDINATION_LOCK_TIMEOUT_INVALID")
    paths = resolve_store_paths(target, repository_id=repository_id, state_root=state_root)
    if create:
        paths.repository_dir.mkdir(parents=True, exist_ok=True)
        if not paths.lock.exists():
            try:
                with open(paths.lock, "xb") as initial:
                    initial.write(b"0")
                    initial.flush()
                    os.fsync(initial.fileno())
            except FileExistsError:
                # Another contender atomically created the same lock inode.
                pass
    if not paths.lock.is_file():
        yield None
        return
    if _is_link_or_reparse(paths.lock):
        raise _blocked("BLOCKED_COORDINATION_REPARSE_PATH")
    stream = open(paths.lock, "r+b", buffering=0)
    deadline = time.monotonic() + float(timeout_seconds)
    acquired = False
    try:
        while True:
            try:
                _lock_attempt(stream, shared)
                acquired = True
                break
            except OSError as exc:
                if exc.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK, 13, 33, 36):
                    raise _blocked("BLOCKED_COORDINATION_LOCK_UNAVAILABLE") from None
                if time.monotonic() >= deadline:
                    raise _blocked("BLOCKED_COORDINATION_LOCK_TIMEOUT")
                time.sleep(min(0.01, max(0.0, deadline - time.monotonic())))
        yield paths
    finally:
        if acquired:
            try:
                _lock_release(stream)
            except OSError:
                pass
        stream.close()


def _schema(name):
    try:
        with open(aeh_paths.join("schemas", name), "r", encoding="utf-8") as stream:
            return json.load(stream)
    except (OSError, ValueError) as exc:
        raise _blocked("BLOCKED_COORDINATION_SCHEMA_UNAVAILABLE") from exc


def _validate_store(body):
    if not isinstance(body, dict):
        raise _blocked("BLOCKED_COORDINATION_STORE_INVALID")
    if body.get("contract") != STORE_CONTRACT or body.get("version") != STORE_VERSION:
        raise _blocked("BLOCKED_COORDINATION_STORE_VERSION")
    try:
        jsonschema.validate(body, _schema("coordination-store.schema.json"))
    except jsonschema.ValidationError as exc:
        raise _blocked("BLOCKED_COORDINATION_STORE_INVALID") from exc
    return body


def new_store(repository_id_sha256, observed_at, revision=0):
    body = {
        "contract": STORE_CONTRACT,
        "version": STORE_VERSION,
        "repository_id_sha256": repository_id_sha256,
        "revision": revision,
        "last_observed_at": observed_at,
        "reservations": [],
        "change_leases": [],
        "workspace_bindings": [],
        "last_receipt_digest": None,
    }
    return _validate_store(body)


def read_store(target, repository_id=None, state_root=None, timeout_seconds=5.0):
    paths = resolve_store_paths(target, repository_id=repository_id, state_root=state_root)
    if not os.path.lexists(paths.store):
        return None
    if not paths.store.is_file() or _is_link_or_reparse(paths.store):
        raise _blocked("BLOCKED_COORDINATION_STORE_UNSAFE")
    if not paths.lock.is_file() or _is_link_or_reparse(paths.lock):
        # Preserve the most specific version/schema verdict for malformed
        # externally-created state, then reject an otherwise valid unlocked
        # store because a stable read cannot be proven.
        try:
            with open(paths.store, "rb") as stream:
                raw = stream.read(16 * 1024 * 1024 + 1)
            if len(raw) > 16 * 1024 * 1024:
                raise _blocked("BLOCKED_COORDINATION_STORE_INVALID")
            _validate_store(json.loads(raw.decode("utf-8")))
        except CoordinationError:
            raise
        except (OSError, UnicodeError, ValueError):
            raise _blocked("BLOCKED_COORDINATION_STORE_INVALID") from None
        raise _blocked("BLOCKED_COORDINATION_LOCK_UNAVAILABLE")
    try:
        with repository_lock(
                target, repository_id=repository_id, state_root=state_root,
                shared=True, timeout_seconds=timeout_seconds, create=False):
            with open(paths.store, "rb") as stream:
                raw = stream.read(16 * 1024 * 1024 + 1)
        if len(raw) > 16 * 1024 * 1024:
            raise _blocked("BLOCKED_COORDINATION_STORE_INVALID")
        return _validate_store(json.loads(raw.decode("utf-8")))
    except CoordinationError:
        raise
    except (OSError, UnicodeError, ValueError):
        raise _blocked("BLOCKED_COORDINATION_STORE_INVALID") from None


def write_store_atomic(target, body, repository_id=None, state_root=None,
                       timeout_seconds=5.0, fault=None):
    _validate_store(body)
    paths = resolve_store_paths(target, repository_id=repository_id, state_root=state_root)
    temp_path = None
    try:
        with repository_lock(
                target, repository_id=repository_id, state_root=state_root,
                shared=False, timeout_seconds=timeout_seconds, create=True):
            descriptor, temp_path = tempfile.mkstemp(
                prefix=".store-", suffix=".aeh-tmp", dir=paths.repository_dir)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(_canonical_json(body) + b"\n")
                stream.flush()
                os.fsync(stream.fileno())
            if fault == "before_replace":
                raise OSError("injected before replacement")
            os.replace(temp_path, paths.store)
            temp_path = None
            if fault == "after_replace":
                raise OSError("injected after replacement")
            try:
                directory_fd = os.open(paths.repository_dir, os.O_RDONLY)
            except OSError:
                directory_fd = None
            if directory_fd is not None:
                try:
                    os.fsync(directory_fd)
                except OSError:
                    pass
                finally:
                    os.close(directory_fd)
    except CoordinationError:
        raise
    except OSError:
        raise _blocked("BLOCKED_COORDINATION_ATOMIC_WRITE") from None
    finally:
        if temp_path and os.path.isfile(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
    return body


def _change_paths(change_dir):
    paths = []
    for current, directories, files in os.walk(change_dir, followlinks=False):
        directories.sort()
        files.sort()
        for name in directories:
            path = os.path.join(current, name)
            if name.lower().endswith(_TEMP_SUFFIXES):
                raise _blocked("BLOCKED_COORDINATION_CHANGE_TEMP")
            if _is_link_or_reparse(path):
                raise _blocked("BLOCKED_COORDINATION_CHANGE_LINK")
        for name in files:
            path = os.path.join(current, name)
            if name.lower().endswith(_TEMP_SUFFIXES):
                raise _blocked("BLOCKED_COORDINATION_CHANGE_TEMP")
            if _is_link_or_reparse(path):
                raise _blocked("BLOCKED_COORDINATION_CHANGE_LINK")
            try:
                info = os.stat(path, follow_symlinks=False)
            except OSError:
                raise _blocked("BLOCKED_COORDINATION_CHANGE_DRIFT") from None
            if not stat.S_ISREG(info.st_mode):
                raise _blocked("BLOCKED_COORDINATION_CHANGE_TYPE")
            paths.append(os.path.relpath(path, change_dir).replace(os.sep, "/"))
    return sorted(paths)


def change_truth(target, change_id, max_files=_MAX_CHANGE_FILES, max_bytes=_MAX_CHANGE_BYTES):
    canonical = _safe_directory(target)
    if not _CHANGE_ID.fullmatch(change_id or ""):
        raise _blocked("BLOCKED_COORDINATION_CHANGE_ID_INVALID")
    change_dir = Path(canonical) / ".aeh" / "changes" / change_id
    _assert_existing_components_safe(
        change_dir, "BLOCKED_COORDINATION_CHANGE_LINK")
    if not change_dir.is_dir() or _is_link_or_reparse(change_dir):
        raise _blocked("BLOCKED_COORDINATION_CHANGE_UNSAFE")
    relative_paths = _change_paths(change_dir)
    if len(relative_paths) > max_files:
        raise _blocked("BLOCKED_COORDINATION_CHANGE_OVERFLOW")
    entries = []
    total = 0
    for rel in relative_paths:
        path = change_dir.joinpath(*rel.split("/"))
        try:
            before = os.stat(path, follow_symlinks=False)
        except OSError:
            raise _blocked("BLOCKED_COORDINATION_CHANGE_DRIFT") from None
        if not stat.S_ISREG(before.st_mode):
            raise _blocked("BLOCKED_COORDINATION_CHANGE_TYPE")
        if total + before.st_size > max_bytes:
            raise _blocked("BLOCKED_COORDINATION_CHANGE_OVERFLOW")
        digest = hashlib.sha256()
        length = 0
        try:
            with open(path, "rb") as stream:
                while True:
                    chunk = stream.read(1024 * 1024)
                    if not chunk:
                        break
                    digest.update(chunk)
                    length += len(chunk)
            after = os.stat(path, follow_symlinks=False)
        except OSError:
            raise _blocked("BLOCKED_COORDINATION_CHANGE_DRIFT") from None
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
                after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) or length != before.st_size:
            raise _blocked("BLOCKED_COORDINATION_CHANGE_DRIFT")
        entries.append({"path": rel, "length": length, "sha256": digest.hexdigest()})
        total += length
    if _change_paths(change_dir) != relative_paths:
        raise _blocked("BLOCKED_COORDINATION_CHANGE_DRIFT")
    entries.sort(key=lambda item: item["path"])
    body = {"entries": entries}
    return {"entries": entries, "digest": _sha256(_canonical_json(body))}


def build_receipt(operation, outcome, repository_id_sha256, workspace_id_sha256,
                  change_id, change_truth_sha256, store_revision, observed_at):
    body = {
        "contract": RECEIPT_CONTRACT,
        "version": RECEIPT_VERSION,
        "operation": operation,
        "outcome": outcome,
        "repository_id_sha256": repository_id_sha256,
        "workspace_id_sha256": workspace_id_sha256,
        "change_id": change_id,
        "change_truth_sha256": change_truth_sha256,
        "store_revision": store_revision,
        "observed_at": observed_at,
    }
    body["digest"] = _sha256(_canonical_json(body))
    try:
        jsonschema.validate(body, _schema("coordination-receipt.schema.json"))
    except jsonschema.ValidationError as exc:
        raise _blocked("BLOCKED_COORDINATION_RECEIPT_INVALID") from exc
    return body


def coordination_status(target, change_id=None, repository_id=None, state_root=None,
                        timeout_seconds=5.0):
    paths = resolve_store_paths(target, repository_id=repository_id, state_root=state_root)
    store = read_store(
        target, repository_id=repository_id, state_root=state_root,
        timeout_seconds=timeout_seconds)
    result = {
        "contract": "coordination.status",
        "version": 1,
        "boundary": "single-host-local-filesystem",
        "status": "NOT_ACTIVATED" if store is None else "READY",
        "repository_id_sha256": paths.repository_id_sha256,
        "workspace_id_sha256": paths.workspace_id_sha256,
        "store_revision": 0 if store is None else store["revision"],
    }
    if change_id is not None:
        result["change_id"] = change_id
        result["change_truth_sha256"] = change_truth(target, change_id)["digest"]
    return result
