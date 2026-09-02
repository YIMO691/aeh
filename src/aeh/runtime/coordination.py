"""Bounded AEH coordination for a single-host local-filesystem.

This module does not provide cross-host or network-filesystem correctness.
M6.3B adds repository reservations, WRITE leases, optimistic Change-truth CAS,
maintenance guards, and a drain Gate on top of the M6.3A substrate. M6.3C
adds stable shared-lock snapshots for token-free Change readers.
"""
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import errno
import functools
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat
import subprocess
import tempfile
import threading
import time

import jsonschema

from .. import paths as aeh_paths
from . import ownership


STORE_CONTRACT = "coordination.store"
STORE_VERSION = 1
RECEIPT_CONTRACT = "coordination.receipt"
RECEIPT_VERSION = 1
_CHANGE_ID = re.compile(r"^CHG-[0-9]{4}-[0-9]{4,}$")
_TEMP_SUFFIXES = (".aeh-tmp", ".aeh-rollback", ".tmp", ".temp")
_MAX_CHANGE_FILES = 10000
_MAX_CHANGE_BYTES = 256 * 1024 * 1024
_MAX_STORE_BYTES = 16 * 1024 * 1024
_MIN_TTL_SECONDS = 30
_MAX_TTL_SECONDS = 86400
_TOKEN_PATTERN = re.compile(br"^[0-9a-f]{64}$")
# v1 begins after the two pre-coordination Change slots retained by the
# M6.3 migration contract.  The external high-water mark is never rewound.
_RESERVATION_SEQUENCE_FLOOR = 2
_PROCESS_LOCKS = {}
_PROCESS_LOCKS_GUARD = threading.Lock()
_MUTATION_CONTEXT = threading.local()


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


def _process_lock(path):
    key = os.path.normcase(os.path.abspath(os.fspath(path)))
    with _PROCESS_LOCKS_GUARD:
        return _PROCESS_LOCKS.setdefault(key, threading.RLock())


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
        import ctypes
        import msvcrt
        from ctypes import wintypes

        class Overlapped(ctypes.Structure):
            _fields_ = [
                ("Internal", ctypes.c_void_p),
                ("InternalHigh", ctypes.c_void_p),
                ("Offset", wintypes.DWORD),
                ("OffsetHigh", wintypes.DWORD),
                ("hEvent", wintypes.HANDLE),
            ]

        overlapped = Overlapped()
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        lock_file = kernel32.LockFileEx
        lock_file.argtypes = [
            wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD,
            wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(Overlapped),
        ]
        lock_file.restype = wintypes.BOOL
        flags = 0x00000001  # LOCKFILE_FAIL_IMMEDIATELY
        if not shared:
            flags |= 0x00000002  # LOCKFILE_EXCLUSIVE_LOCK
        handle = wintypes.HANDLE(msvcrt.get_osfhandle(stream.fileno()))
        if not lock_file(handle, flags, 0, 1, 0, ctypes.byref(overlapped)):
            error = ctypes.get_last_error()
            raise OSError(error, "LockFileEx failed")
        return overlapped
    else:
        import fcntl
        mode = fcntl.LOCK_SH if shared else fcntl.LOCK_EX
        fcntl.flock(stream.fileno(), mode | fcntl.LOCK_NB)
        return None


def _lock_release(stream, lock_state=None):
    if os.name == "nt":
        import ctypes
        import msvcrt
        from ctypes import wintypes
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        unlock_file = kernel32.UnlockFileEx
        unlock_file.argtypes = [
            wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD,
            wintypes.DWORD, ctypes.c_void_p,
        ]
        unlock_file.restype = wintypes.BOOL
        handle = wintypes.HANDLE(msvcrt.get_osfhandle(stream.fileno()))
        if not unlock_file(handle, 0, 1, 0, ctypes.byref(lock_state)):
            error = ctypes.get_last_error()
            raise OSError(error, "UnlockFileEx failed")
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
    process_lock = _process_lock(paths.lock)
    if not process_lock.acquire(timeout=float(timeout_seconds)):
        raise _blocked("BLOCKED_COORDINATION_LOCK_TIMEOUT")
    try:
        stream = open(paths.lock, "r+b", buffering=0)
    except OSError:
        process_lock.release()
        raise _blocked("BLOCKED_COORDINATION_LOCK_UNAVAILABLE") from None
    deadline = time.monotonic() + float(timeout_seconds)
    acquired = False
    lock_state = None
    try:
        while True:
            try:
                lock_state = _lock_attempt(stream, shared)
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
                _lock_release(stream, lock_state)
            except OSError:
                pass
        stream.close()
        process_lock.release()


@functools.lru_cache(maxsize=None)
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
        for reservation in body.get("reservations", []):
            jsonschema.validate(
                reservation, _schema("change-reservation.schema.json"))
        for lease in body.get("change_leases", []):
            jsonschema.validate(lease, _schema("change-lease.schema.json"))
        for binding in body.get("workspace_bindings", []):
            jsonschema.validate(binding, _schema("workspace-binding.schema.json"))
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


def atomic_write_bytes(path, content):
    """Durably replace one already-contained local file with unique temp state."""
    destination = os.path.abspath(os.fspath(path))
    parent = os.path.dirname(destination)
    if not os.path.isdir(parent):
        raise _blocked("BLOCKED_COORDINATION_WRITE_DESTINATION_INVALID")
    _assert_existing_components_safe(parent, "BLOCKED_COORDINATION_REPARSE_PATH")
    if os.path.lexists(destination) and _is_link_or_reparse(destination):
        raise _blocked("BLOCKED_COORDINATION_REPARSE_PATH")
    if not isinstance(content, (bytes, bytearray)):
        raise _blocked("BLOCKED_COORDINATION_WRITE_CONTENT_INVALID")
    temp_path = None
    try:
        descriptor, temp_path = tempfile.mkstemp(
            prefix="." + os.path.basename(destination) + "-",
            suffix=".aeh-tmp", dir=parent)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(bytes(content))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, destination)
        temp_path = None
    except OSError:
        raise _blocked("BLOCKED_COORDINATION_ATOMIC_WRITE") from None
    finally:
        if temp_path and os.path.isfile(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


def atomic_write_text(path, content):
    if not isinstance(content, str):
        raise _blocked("BLOCKED_COORDINATION_WRITE_CONTENT_INVALID")
    atomic_write_bytes(path, content.encode("utf-8"))


def atomic_copy_file(source, destination):
    try:
        with open(source, "rb") as stream:
            content = stream.read()
    except OSError:
        raise _blocked("BLOCKED_COORDINATION_COPY_SOURCE_INVALID") from None
    atomic_write_bytes(destination, content)


def _utc_now(now=None):
    value = now if now is not None else datetime.now(timezone.utc)
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise _blocked("BLOCKED_COORDINATION_TIME_INVALID")
    return value.astimezone(timezone.utc)


def _time_text(value):
    return value.astimezone(timezone.utc).isoformat()


def _parse_time(value):
    if not isinstance(value, str) or not value:
        raise _blocked("BLOCKED_COORDINATION_STORE_INVALID")
    try:
        parsed = datetime.fromisoformat(
            value[:-1] + "+00:00" if value.endswith("Z") else value)
    except ValueError:
        raise _blocked("BLOCKED_COORDINATION_STORE_INVALID") from None
    if parsed.tzinfo is None:
        raise _blocked("BLOCKED_COORDINATION_STORE_INVALID")
    return parsed.astimezone(timezone.utc)


def _validate_ttl(ttl_seconds):
    if (isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, int) or
            ttl_seconds < _MIN_TTL_SECONDS or ttl_seconds > _MAX_TTL_SECONDS):
        raise _blocked("BLOCKED_COORDINATION_TTL_INVALID")
    return ttl_seconds


def _load_store_unlocked(paths):
    if not os.path.lexists(paths.store):
        return None
    if not paths.store.is_file() or _is_link_or_reparse(paths.store):
        raise _blocked("BLOCKED_COORDINATION_STORE_UNSAFE")
    try:
        with open(paths.store, "rb") as stream:
            raw = stream.read(_MAX_STORE_BYTES + 1)
        if len(raw) > _MAX_STORE_BYTES:
            raise _blocked("BLOCKED_COORDINATION_STORE_INVALID")
        body = _validate_store(json.loads(raw.decode("utf-8")))
    except CoordinationError:
        raise
    except (OSError, UnicodeError, ValueError):
        raise _blocked("BLOCKED_COORDINATION_STORE_INVALID") from None
    if body["repository_id_sha256"] != paths.repository_id_sha256:
        raise _blocked("BLOCKED_COORDINATION_REPOSITORY_MISMATCH")
    return body


def _write_store_unlocked(paths, body):
    _validate_store(body)
    temp_path = None
    try:
        descriptor, temp_path = tempfile.mkstemp(
            prefix=".store-", suffix=".aeh-tmp", dir=paths.repository_dir)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(_canonical_json(body) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, paths.store)
        temp_path = None
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


def _observe_store(store, observed):
    previous = _parse_time(store["last_observed_at"])
    if observed < previous:
        raise _blocked("BLOCKED_COORDINATION_CLOCK_ROLLBACK")


def _mutate_store(target, callback, repository_id=None, state_root=None,
                  timeout_seconds=5.0, now=None):
    observed = _utc_now(now)
    with repository_lock(
            target, repository_id=repository_id, state_root=state_root,
            shared=False, timeout_seconds=timeout_seconds, create=True) as paths:
        store = _load_store_unlocked(paths)
        if store is None:
            store = new_store(paths.repository_id_sha256, _time_text(observed))
        else:
            _observe_store(store, observed)
        result = callback(store, paths, observed)
        store["revision"] += 1
        store["last_observed_at"] = _time_text(observed)
        if isinstance(result, dict):
            operation_by_status = {
                "CHANGE_ID_RESERVED": "RESERVE",
                "RESERVATION_COMMITTED": "FINALIZE_RESERVATION",
                "RESERVATION_ABANDONED": "FINALIZE_RESERVATION",
                "LEASE_ACQUIRED": "ACQUIRE",
                "LEASE_RENEWED": "RENEW",
                "LEASE_RELEASED": "RELEASE",
                "LEASE_RECOVERED": "RECOVER",
                "MUTATION_BEGUN": "BEGIN_MUTATION",
                "MUTATION_FINALIZED": "FINALIZE_MUTATION",
                "MUTATION_ABORTED": "ABORT_MUTATION",
            }
            receipt_operation = operation_by_status.get(result.get("status"))
            if receipt_operation is not None:
                receipt = build_receipt(
                    receipt_operation, result["status"],
                    paths.repository_id_sha256, paths.workspace_id_sha256,
                    result.get("change_id"),
                    result.get("change_truth_sha256"), store["revision"],
                    _time_text(observed))
                store["last_receipt_digest"] = receipt["digest"]
                result["receipt_digest"] = receipt["digest"]
        _write_store_unlocked(paths, store)
        return result


def _token_destination(target, paths, token_file):
    if not token_file:
        raise _blocked("BLOCKED_LEASE_TOKEN_FILE_REQUIRED")
    raw = os.fspath(token_file)
    if (os.name == "nt" and raw.startswith("\\\\")) or raw.startswith("//"):
        raise _blocked("BLOCKED_COORDINATION_NETWORK_PATH")
    absolute = os.path.realpath(os.path.abspath(raw))
    _assert_existing_components_safe(
        os.path.dirname(absolute), "BLOCKED_COORDINATION_REPARSE_PATH")
    parent = os.path.dirname(absolute)
    if not os.path.isdir(parent):
        raise _blocked("BLOCKED_LEASE_TOKEN_DESTINATION_INVALID")
    governed = os.path.realpath(os.path.abspath(target))
    state = os.path.realpath(os.path.abspath(paths.state_root))
    try:
        inside_target = os.path.commonpath([absolute, governed]) == governed
        inside_state = os.path.commonpath([absolute, state]) == state
    except ValueError:
        inside_target = inside_state = False
    if inside_target or inside_state:
        raise _blocked("BLOCKED_LEASE_TOKEN_DESTINATION_INVALID")
    return absolute


def _create_token_file(target, paths, token_file):
    destination = _token_destination(target, paths, token_file)
    token = secrets.token_hex(32).encode("ascii")
    try:
        descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(token)
            stream.flush()
            os.fsync(stream.fileno())
        if os.name != "nt":
            os.chmod(destination, 0o600)
    except FileExistsError:
        raise _blocked("BLOCKED_LEASE_TOKEN_FILE_EXISTS") from None
    except OSError:
        raise _blocked("BLOCKED_LEASE_TOKEN_FILE_UNAVAILABLE") from None
    return destination, token


def _read_token_file(target, paths, token_file):
    destination = _token_destination(target, paths, token_file)
    if not os.path.isfile(destination) or _is_link_or_reparse(destination):
        raise _blocked("BLOCKED_LEASE_TOKEN_UNAVAILABLE")
    try:
        with open(destination, "rb") as stream:
            token = stream.read(65)
    except OSError:
        raise _blocked("BLOCKED_LEASE_TOKEN_UNAVAILABLE") from None
    if not _TOKEN_PATTERN.fullmatch(token):
        raise _blocked("BLOCKED_LEASE_TOKEN_INVALID")
    return token


def _latest_lease(store, change_id):
    for index in range(len(store["change_leases"]) - 1, -1, -1):
        lease = store["change_leases"][index]
        if lease.get("change_id") == change_id:
            return index, lease
    raise _blocked("BLOCKED_LEASE_NOT_FOUND")


def _require_revision(lease, expected_revision):
    if (isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or
            lease.get("lease_revision") != expected_revision):
        raise _blocked("BLOCKED_STALE_LEASE_REVISION")


def _require_active(lease):
    if lease.get("state") != "ACTIVE":
        raise _blocked("BLOCKED_LEASE_NOT_ACTIVE")


def _require_lease_binding(paths, lease, workspace_ref=None,
                           verify_workspace_ref=False):
    if (lease.get("repository_id_sha256") != paths.repository_id_sha256 or
            lease.get("workspace_id_sha256") != paths.workspace_id_sha256):
        raise _blocked("BLOCKED_LEASE_IDENTITY_MISMATCH")
    expected_ref = lease.get("workspace_ref_sha256")
    if verify_workspace_ref and expected_ref is not None:
        if not isinstance(workspace_ref, str) or not workspace_ref:
            raise _blocked("BLOCKED_WORKSPACE_REF_REQUIRED")
        actual_ref = _sha256(workspace_ref.encode("utf-8"))
        if not secrets.compare_digest(actual_ref, str(expected_ref)):
            raise _blocked("BLOCKED_WORKSPACE_REF_MISMATCH")


def _require_live(lease, observed):
    if observed >= _parse_time(lease.get("expires_at")):
        raise _blocked("BLOCKED_LEASE_EXPIRED")


def _require_token(target, paths, lease, token_file):
    token = _read_token_file(target, paths, token_file)
    if not secrets.compare_digest(_sha256(token), str(lease.get("token_sha256", ""))):
        raise _blocked("BLOCKED_LEASE_TOKEN_INVALID")


def _require_truth(target, change_id, lease, recovery=False):
    current = change_truth(target, change_id)["digest"]
    if current != lease.get("change_truth_sha256"):
        code = "BLOCKED_RECOVERY_TRUTH_DRIFT" if recovery else "BLOCKED_CHANGE_TRUTH_DRIFT"
        raise _blocked(code)
    return current


def _release_binding(store, lease, observed):
    for binding in reversed(store["workspace_bindings"]):
        if (binding.get("state") == "ACTIVE" and
                binding.get("change_id") == lease["change_id"] and
                binding.get("workspace_id_sha256") == lease["workspace_id_sha256"]):
            binding["state"] = "RELEASED"
            binding["released_at"] = _time_text(observed)
            return


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


def _snapshot_provenance(paths, store, lease):
    state = "NOT_ACTIVATED"
    if lease is not None:
        state = lease.get("state")
        if state not in ("ACTIVE", "RELEASED", "RECOVERED"):
            state = "BLOCKED"
    result = {
        "protocol_version": STORE_VERSION,
        "state": state,
        "repository_id_sha256": paths.repository_id_sha256,
        "workspace_id_sha256": paths.workspace_id_sha256,
        "lease_revision": None if lease is None else lease.get("lease_revision"),
        "last_truth_hash": None if lease is None else lease.get("change_truth_sha256"),
        "last_receipt_digest": None if store is None else store.get("last_receipt_digest"),
    }
    if lease is not None and lease.get("workspace_ref_sha256") is not None:
        result["external_workspace_ref_sha256"] = lease["workspace_ref_sha256"]
    return result


def stable_change_snapshot(target, change_id, reader, repository_id=None,
                           state_root=None, timeout_seconds=5.0, now=None):
    """Run a bounded Change reader against one stable, token-free generation.

    The shared repository lock is retained across the callback. A legacy
    Change without a coordination store stays unactivated and is accepted only
    if neither the Change truth nor coordination state appears during the read.
    """
    if not callable(reader):
        raise _blocked("BLOCKED_COORDINATION_READER_INVALID")
    paths = resolve_store_paths(
        target, repository_id=repository_id, state_root=state_root)
    observed = _utc_now(now)
    store_present = os.path.lexists(paths.store)
    if store_present and not paths.lock.is_file():
        # Preserve the store parser's deterministic malformed/version verdict.
        read_store(
            target, repository_id=repository_id, state_root=state_root,
            timeout_seconds=timeout_seconds)
        raise _blocked("BLOCKED_COORDINATION_LOCK_UNAVAILABLE")

    with repository_lock(
            target, repository_id=repository_id, state_root=state_root,
            shared=True, timeout_seconds=timeout_seconds, create=False):
        store = _load_store_unlocked(paths) if store_present else None
        if store is not None:
            _observe_store(store, observed)
        matches = [] if store is None else [
            item for item in store["change_leases"]
            if item.get("change_id") == change_id
        ]
        lease = matches[-1] if matches else None
        if lease is not None:
            _require_lease_binding(paths, lease)
            if lease.get("active_operation") is not None:
                raise _blocked("BLOCKED_ACTIVE_OPERATION")
        before = change_truth(target, change_id)["digest"]
        if lease is not None and before != lease.get("change_truth_sha256"):
            raise _blocked("BLOCKED_CHANGE_TRUTH_DRIFT")
        value = reader()
        after = change_truth(target, change_id)["digest"]
        if after != before:
            raise _blocked("BLOCKED_CHANGE_TRUTH_DRIFT")
        if store is None and (
                os.path.lexists(paths.store) or os.path.lexists(paths.lock)):
            raise _blocked("BLOCKED_CHANGE_TRUTH_DRIFT")
        return {
            "status": "SNAPSHOT_COMPLETE",
            "value": value,
            "coordination": _snapshot_provenance(paths, store, lease),
        }


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


def reserve_change_id(target, year, reservation_ref, repository_id=None,
                      state_root=None, timeout_seconds=5.0, now=None):
    if (isinstance(year, bool) or not isinstance(year, int) or
            year < 1 or year > 9999):
        raise _blocked("BLOCKED_COORDINATION_YEAR_INVALID")
    if (not isinstance(reservation_ref, str) or not reservation_ref or
            len(reservation_ref) > 4096):
        raise _blocked("BLOCKED_COORDINATION_RESERVATION_REF_INVALID")

    def mutate(store, paths, observed):
        sequences = [_RESERVATION_SEQUENCE_FLOOR]
        changes_dir = Path(_safe_directory(target)) / ".aeh" / "changes"
        if changes_dir.is_dir():
            for child in changes_dir.iterdir():
                match = re.fullmatch(r"CHG-%04d-([0-9]{4,})" % year, child.name)
                if match:
                    sequences.append(int(match.group(1)))
        for reservation in store["reservations"]:
            if reservation.get("year") == year:
                sequences.append(int(reservation.get("sequence", 0)))
        sequence = max(sequences) + 1
        change_id = "CHG-%04d-%04d" % (year, sequence)
        record = {
            "contract": "change.reservation",
            "version": 1,
            "change_id": change_id,
            "year": year,
            "sequence": sequence,
            "workspace_id_sha256": paths.workspace_id_sha256,
            "reservation_ref_sha256": _sha256(reservation_ref.encode("utf-8")),
            "reserved_at": _time_text(observed),
            "state": "PENDING",
        }
        store["reservations"].append(record)
        return {
            "status": "CHANGE_ID_RESERVED",
            "change_id": change_id,
            "reservation_state": "PENDING",
            "store_revision": store["revision"] + 1,
        }

    return _mutate_store(
        target, mutate, repository_id=repository_id, state_root=state_root,
        timeout_seconds=timeout_seconds, now=now)


def finalize_reservation(target, change_id, reservation_ref=None,
                         outcome="COMMITTED", repository_id=None,
                         state_root=None, timeout_seconds=5.0, now=None,
                         expected_store_revision=None,
                         required_truth_hash=None):
    if outcome not in ("COMMITTED", "ABANDONED"):
        raise _blocked("BLOCKED_COORDINATION_RESERVATION_OUTCOME_INVALID")
    if reservation_ref is not None and (
            not isinstance(reservation_ref, str) or not reservation_ref or
            len(reservation_ref) > 4096):
        raise _blocked("BLOCKED_COORDINATION_RESERVATION_REF_INVALID")

    def mutate(store, paths, observed):
        if (expected_store_revision is not None and
                store["revision"] != expected_store_revision):
            raise _blocked("BLOCKED_STALE_STORE_REVISION")
        reservation = next(
            (item for item in reversed(store["reservations"])
             if item.get("change_id") == change_id), None)
        if reservation is None:
            raise _blocked("BLOCKED_RESERVATION_NOT_FOUND")
        if reservation.get("state") != "PENDING":
            raise _blocked("BLOCKED_RESERVATION_NOT_PENDING")
        if reservation.get("workspace_id_sha256") != paths.workspace_id_sha256:
            raise _blocked("BLOCKED_RESERVATION_WORKSPACE_MISMATCH")
        if reservation_ref is not None:
            actual = _sha256(str(reservation_ref).encode("utf-8"))
            if not secrets.compare_digest(
                    actual, str(reservation.get("reservation_ref_sha256", ""))):
                raise _blocked("BLOCKED_RESERVATION_REF_INVALID")
        truth = (change_truth(target, change_id)["digest"]
                 if outcome == "COMMITTED" else None)
        if (required_truth_hash is not None and outcome == "COMMITTED" and
                not secrets.compare_digest(truth, required_truth_hash)):
            raise _blocked("BLOCKED_RECOVERY_TRUTH_DRIFT")
        reservation["state"] = outcome
        reservation["finalized_at"] = _time_text(observed)
        if truth is not None:
            reservation["change_truth_sha256"] = truth
        return {
            "status": "RESERVATION_" + outcome,
            "change_id": change_id,
            "reservation_state": outcome,
            "change_truth_sha256": truth,
            "store_revision": store["revision"] + 1,
        }

    return _mutate_store(
        target, mutate, repository_id=repository_id, state_root=state_root,
        timeout_seconds=timeout_seconds, now=now)


def recover_reservation(target, change_id, expected_revision,
                        expected_truth_hash, repository_id=None,
                        state_root=None, timeout_seconds=5.0, now=None):
    if not re.fullmatch(r"[0-9a-f]{64}", expected_truth_hash or ""):
        raise _blocked("BLOCKED_EXPECTED_TRUTH_INVALID")
    try:
        current_truth = change_truth(target, change_id)["digest"]
    except CoordinationError as exc:
        if str(exc) != "BLOCKED_COORDINATION_CHANGE_UNSAFE":
            raise
        current_truth = None
    outcome = ("COMMITTED" if current_truth == expected_truth_hash
               else "ABANDONED")
    return finalize_reservation(
        target, change_id, outcome=outcome, repository_id=repository_id,
        state_root=state_root, timeout_seconds=timeout_seconds, now=now,
        expected_store_revision=expected_revision,
        required_truth_hash=expected_truth_hash)


def acquire_lease(target, change_id, holder_ref, token_file, ttl_seconds=900,
                  repository_id=None, workspace_ref=None, state_root=None,
                  timeout_seconds=5.0, now=None):
    _validate_ttl(ttl_seconds)
    if not isinstance(holder_ref, str) or not holder_ref or len(holder_ref) > 4096:
        raise _blocked("BLOCKED_LEASE_HOLDER_INVALID")
    if workspace_ref is not None and (
            not isinstance(workspace_ref, str) or not workspace_ref or
            len(workspace_ref) > 4096):
        raise _blocked("BLOCKED_WORKSPACE_REF_INVALID")
    created_token = None

    def mutate(store, paths, observed):
        nonlocal created_token
        for lease in store["change_leases"]:
            if lease.get("state") != "ACTIVE":
                continue
            if lease.get("change_id") == change_id:
                raise _blocked("BLOCKED_CHANGE_LEASE_CONFLICT")
            if lease.get("workspace_id_sha256") == paths.workspace_id_sha256:
                raise _blocked("BLOCKED_WORKSPACE_LEASE_CONFLICT")
        truth = change_truth(target, change_id)["digest"]
        created_token, token = _create_token_file(target, paths, token_file)
        previous_revisions = [
            int(item.get("lease_revision", 0))
            for item in store["change_leases"]
            if item.get("change_id") == change_id]
        lease_revision = max(previous_revisions or [0]) + 1
        lease = {
            "contract": "change.lease",
            "version": 1,
            "repository_id_sha256": paths.repository_id_sha256,
            "change_id": change_id,
            "workspace_id_sha256": paths.workspace_id_sha256,
            "workspace_ref_sha256": (
                _sha256(workspace_ref.encode("utf-8"))
                if workspace_ref is not None else None),
            "holder_id_sha256": _sha256(holder_ref.encode("utf-8")),
            "token_sha256": _sha256(token),
            "mode": "WRITE",
            "fencing_token": store["revision"] + 1,
            "lease_revision": lease_revision,
            "acquired_at": _time_text(observed),
            "renewed_at": None,
            "expires_at": _time_text(observed + timedelta(seconds=ttl_seconds)),
            "change_truth_sha256": truth,
            "active_operation": None,
            "state": "ACTIVE",
        }
        store["change_leases"].append(lease)
        store["workspace_bindings"].append({
            "contract": "workspace.binding",
            "version": 1,
            "repository_id_sha256": paths.repository_id_sha256,
            "workspace_id_sha256": paths.workspace_id_sha256,
            "workspace_ref_sha256": lease["workspace_ref_sha256"],
            "change_id": change_id,
            "bound_at": _time_text(observed),
            "state": "ACTIVE",
        })
        return {
            "status": "LEASE_ACQUIRED",
            "change_id": change_id,
            "lease_revision": lease_revision,
            "change_truth_sha256": truth,
            "expires_at": lease["expires_at"],
            "repository_id_sha256": paths.repository_id_sha256,
            "workspace_id_sha256": paths.workspace_id_sha256,
            "store_revision": store["revision"] + 1,
        }

    try:
        return _mutate_store(
            target, mutate, repository_id=repository_id, state_root=state_root,
            timeout_seconds=timeout_seconds, now=now)
    except Exception:
        if created_token and os.path.isfile(created_token):
            try:
                os.remove(created_token)
            except OSError:
                pass
        raise


def renew_lease(target, change_id, token_file, expected_revision,
                ttl_seconds=900, repository_id=None, state_root=None,
                timeout_seconds=5.0, now=None):
    _validate_ttl(ttl_seconds)

    def mutate(store, paths, observed):
        _, lease = _latest_lease(store, change_id)
        _require_revision(lease, expected_revision)
        _require_active(lease)
        _require_lease_binding(paths, lease)
        _require_live(lease, observed)
        _require_token(target, paths, lease, token_file)
        if lease.get("active_operation") is not None:
            raise _blocked("BLOCKED_ACTIVE_OPERATION")
        _require_truth(target, change_id, lease)
        lease["lease_revision"] += 1
        lease["renewed_at"] = _time_text(observed)
        lease["expires_at"] = _time_text(observed + timedelta(seconds=ttl_seconds))
        return {
            "status": "LEASE_RENEWED",
            "change_id": change_id,
            "lease_revision": lease["lease_revision"],
            "change_truth_sha256": lease["change_truth_sha256"],
            "expires_at": lease["expires_at"],
            "store_revision": store["revision"] + 1,
        }

    return _mutate_store(
        target, mutate, repository_id=repository_id, state_root=state_root,
        timeout_seconds=timeout_seconds, now=now)


def release_lease(target, change_id, token_file, expected_revision,
                  repository_id=None, state_root=None,
                  timeout_seconds=5.0, now=None):
    def mutate(store, paths, observed):
        _, lease = _latest_lease(store, change_id)
        _require_revision(lease, expected_revision)
        _require_active(lease)
        _require_lease_binding(paths, lease)
        _require_live(lease, observed)
        _require_token(target, paths, lease, token_file)
        if lease.get("active_operation") is not None:
            raise _blocked("BLOCKED_ACTIVE_OPERATION")
        _require_truth(target, change_id, lease)
        lease["lease_revision"] += 1
        lease["state"] = "RELEASED"
        lease["released_at"] = _time_text(observed)
        _release_binding(store, lease, observed)
        return {
            "status": "LEASE_RELEASED",
            "change_id": change_id,
            "lease_revision": lease["lease_revision"],
            "change_truth_sha256": lease["change_truth_sha256"],
            "store_revision": store["revision"] + 1,
        }

    return _mutate_store(
        target, mutate, repository_id=repository_id, state_root=state_root,
        timeout_seconds=timeout_seconds, now=now)


def recover_lease(target, change_id, expected_revision, expected_truth_hash,
                  repository_id=None, state_root=None,
                  accept_active_operation_truth=False,
                  timeout_seconds=5.0, now=None):
    if not re.fullmatch(r"[0-9a-f]{64}", expected_truth_hash or ""):
        raise _blocked("BLOCKED_EXPECTED_TRUTH_INVALID")

    def mutate(store, paths, observed):
        _, lease = _latest_lease(store, change_id)
        _require_revision(lease, expected_revision)
        _require_active(lease)
        _require_lease_binding(paths, lease)
        if observed < _parse_time(lease["expires_at"]):
            raise _blocked("BLOCKED_LIVE_LEASE")
        active = lease.get("active_operation")
        if active is not None:
            if not accept_active_operation_truth:
                raise _blocked("BLOCKED_RECOVERY_ACTIVE_OPERATION")
            current_truth = change_truth(target, change_id)["digest"]
            if not secrets.compare_digest(expected_truth_hash, current_truth):
                raise _blocked("BLOCKED_RECOVERY_TRUTH_DRIFT")
            lease["change_truth_sha256"] = current_truth
            lease["active_operation"] = None
            recovery_outcome = "ACTIVE_OPERATION_TRUTH_ACCEPTED"
        else:
            if not secrets.compare_digest(
                    expected_truth_hash, str(lease.get("change_truth_sha256", ""))):
                raise _blocked("BLOCKED_RECOVERY_TRUTH_DRIFT")
            _require_truth(target, change_id, lease, recovery=True)
            recovery_outcome = "EXPIRED_LEASE_RELEASED"
        lease["lease_revision"] += 1
        lease["state"] = "RECOVERED"
        lease["recovered_at"] = _time_text(observed)
        _release_binding(store, lease, observed)
        return {
            "status": "LEASE_RECOVERED",
            "change_id": change_id,
            "lease_revision": lease["lease_revision"],
            "change_truth_sha256": lease["change_truth_sha256"],
            "recovery_outcome": recovery_outcome,
            "store_revision": store["revision"] + 1,
        }

    return _mutate_store(
        target, mutate, repository_id=repository_id, state_root=state_root,
        timeout_seconds=timeout_seconds, now=now)


def begin_mutation(target, change_id, operation, token_file,
                   expected_revision, repository_id=None, workspace_ref=None,
                   state_root=None,
                   timeout_seconds=5.0, now=None):
    if (not isinstance(operation, str) or
            not re.fullmatch(r"[A-Z][A-Z0-9_]{1,63}", operation)):
        raise _blocked("BLOCKED_COORDINATION_OPERATION_INVALID")

    def mutate(store, paths, observed):
        _, lease = _latest_lease(store, change_id)
        _require_revision(lease, expected_revision)
        _require_active(lease)
        _require_lease_binding(
            paths, lease, workspace_ref=workspace_ref,
            verify_workspace_ref=True)
        _require_live(lease, observed)
        _require_token(target, paths, lease, token_file)
        if lease.get("active_operation") is not None:
            raise _blocked("BLOCKED_ACTIVE_OPERATION")
        truth = _require_truth(target, change_id, lease)
        operation_id = secrets.token_hex(16)
        lease["active_operation"] = {
            "operation": operation,
            "operation_id_sha256": _sha256(operation_id.encode("ascii")),
            "pre_truth_sha256": truth,
            "begun_at": _time_text(observed),
        }
        lease["lease_revision"] += 1
        return {
            "status": "MUTATION_BEGUN",
            "change_id": change_id,
            "operation": operation,
            "operation_id": operation_id,
            "lease_revision": lease["lease_revision"],
            "change_truth_sha256": truth,
            "store_revision": store["revision"] + 1,
        }

    return _mutate_store(
        target, mutate, repository_id=repository_id, state_root=state_root,
        timeout_seconds=timeout_seconds, now=now)


def _complete_mutation(target, change_id, operation_id, token_file,
                       expected_revision, abort, repository_id=None,
                       state_root=None, timeout_seconds=5.0, now=None):
    if not isinstance(operation_id, str) or not operation_id:
        raise _blocked("BLOCKED_OPERATION_ID_INVALID")

    def mutate(store, paths, observed):
        _, lease = _latest_lease(store, change_id)
        _require_revision(lease, expected_revision)
        _require_active(lease)
        _require_lease_binding(paths, lease)
        _require_live(lease, observed)
        _require_token(target, paths, lease, token_file)
        active = lease.get("active_operation")
        if active is None:
            raise _blocked("BLOCKED_ACTIVE_OPERATION_MISSING")
        supplied = _sha256(operation_id.encode("utf-8"))
        if not secrets.compare_digest(
                supplied, str(active.get("operation_id_sha256", ""))):
            raise _blocked("BLOCKED_OPERATION_ID_INVALID")
        current = change_truth(target, change_id)["digest"]
        if abort and current != active.get("pre_truth_sha256"):
            raise _blocked("BLOCKED_CHANGE_TRUTH_DRIFT")
        lease["active_operation"] = None
        if not abort:
            lease["change_truth_sha256"] = current
        lease["lease_revision"] += 1
        return {
            "status": "MUTATION_ABORTED" if abort else "MUTATION_FINALIZED",
            "change_id": change_id,
            "lease_revision": lease["lease_revision"],
            "change_truth_sha256": lease["change_truth_sha256"],
            "store_revision": store["revision"] + 1,
        }

    return _mutate_store(
        target, mutate, repository_id=repository_id, state_root=state_root,
        timeout_seconds=timeout_seconds, now=now)


def finalize_mutation(target, change_id, operation_id, token_file,
                      expected_revision, repository_id=None, state_root=None,
                      timeout_seconds=5.0, now=None):
    return _complete_mutation(
        target, change_id, operation_id, token_file, expected_revision, False,
        repository_id=repository_id, state_root=state_root,
        timeout_seconds=timeout_seconds, now=now)


def abort_mutation(target, change_id, operation_id, token_file,
                   expected_revision, repository_id=None, state_root=None,
                   timeout_seconds=5.0, now=None):
    return _complete_mutation(
        target, change_id, operation_id, token_file, expected_revision, True,
        repository_id=repository_id, state_root=state_root,
        timeout_seconds=timeout_seconds, now=now)


def _read_store_for_guard(target, repository_id=None, state_root=None,
                          timeout_seconds=5.0, now=None):
    observed = _utc_now(now)
    paths = resolve_store_paths(
        target, repository_id=repository_id, state_root=state_root)
    store = read_store(
        target, repository_id=repository_id, state_root=state_root,
        timeout_seconds=timeout_seconds)
    if store is not None:
        _observe_store(store, observed)
    return paths, store, observed


def assert_workspace_maintenance_allowed(target, repository_id=None,
                                         state_root=None,
                                         timeout_seconds=5.0, now=None):
    paths, store, _ = _read_store_for_guard(
        target, repository_id=repository_id, state_root=state_root,
        timeout_seconds=timeout_seconds, now=now)
    if store is None:
        return {
            "status": "WORKSPACE_MAINTENANCE_ALLOWED",
            "workspace_id_sha256": paths.workspace_id_sha256,
        }
    for lease in store["change_leases"]:
        if (lease.get("workspace_id_sha256") == paths.workspace_id_sha256 and
                lease.get("state") == "ACTIVE"):
            raise _blocked("BLOCKED_WORKSPACE_LEASE_CONFLICT")
    for reservation in store["reservations"]:
        if (reservation.get("workspace_id_sha256") == paths.workspace_id_sha256 and
                reservation.get("state") == "PENDING"):
            raise _blocked("BLOCKED_COORDINATION_RESERVATION_PENDING")
    return {
        "status": "WORKSPACE_MAINTENANCE_ALLOWED",
        "workspace_id_sha256": paths.workspace_id_sha256,
        "store_revision": store["revision"],
    }


def coordination_drain_status(target, repository_id=None, state_root=None,
                              timeout_seconds=5.0, now=None):
    paths, store, _ = _read_store_for_guard(
        target, repository_id=repository_id, state_root=state_root,
        timeout_seconds=timeout_seconds, now=now)
    if store is None:
        return {
            "status": "COORDINATION_DRAINED",
            "repository_id_sha256": paths.repository_id_sha256,
            "store_revision": 0,
        }
    active = [item for item in store["change_leases"]
              if item.get("state") == "ACTIVE"]
    pending = [item for item in store["reservations"]
               if item.get("state") == "PENDING"]
    status = ("BLOCKED_COORDINATION_DRAIN_REQUIRED"
              if active or pending else "COORDINATION_DRAINED")
    return {
        "status": status,
        "repository_id_sha256": paths.repository_id_sha256,
        "store_revision": store["revision"],
        "active_lease_count": len(active),
        "pending_reservation_count": len(pending),
    }


def _context_stack():
    stack = getattr(_MUTATION_CONTEXT, "stack", None)
    if stack is None:
        stack = []
        _MUTATION_CONTEXT.stack = stack
    return stack


def _context_key(target, change_id):
    return os.path.normcase(os.path.realpath(os.path.abspath(target))), change_id


def _active_context(target, change_id):
    key = _context_key(target, change_id)
    for context in reversed(_context_stack()):
        if context["key"] == key:
            return context
    return None


def coordination_activated(target, change_id, repository_id=None,
                           state_root=None, timeout_seconds=5.0):
    store = read_store(
        target, repository_id=repository_id, state_root=state_root,
        timeout_seconds=timeout_seconds)
    return bool(store and any(
        item.get("change_id") == change_id
        for item in store.get("change_leases", [])))


def assert_change_write_allowed(target, change_id, repository_id=None,
                                state_root=None, timeout_seconds=5.0):
    if _active_context(target, change_id) is not None:
        return
    if coordination_activated(
            target, change_id, repository_id=repository_id,
            state_root=state_root, timeout_seconds=timeout_seconds):
        raise _blocked("BLOCKED_WRITE_LEASE_REQUIRED")


def coordinated_change_mutator(operation):
    """Decorate a public Change writer with lazy, nested-safe truth CAS."""
    if not re.fullmatch(r"[A-Z][A-Z0-9_]{1,63}", operation or ""):
        raise ValueError("invalid coordination operation")

    def decorate(function):
        @functools.wraps(function)
        def wrapped(target, change_id, *args, **kwargs):
            token_file = kwargs.pop("lease_token_file", None)
            expected_revision = kwargs.pop("expected_lease_revision", None)
            repository_id = kwargs.pop("repository_id", None)
            workspace_ref = kwargs.pop("workspace_ref", None)
            state_root = kwargs.pop("coordination_state_root", None)
            coordination_now = kwargs.pop("coordination_now", None)
            timeout_seconds = kwargs.pop("coordination_timeout_seconds", 5.0)
            nested = _active_context(target, change_id)
            if nested is not None:
                return function(target, change_id, *args, **kwargs)
            activated = coordination_activated(
                target, change_id, repository_id=repository_id,
                state_root=state_root, timeout_seconds=timeout_seconds)
            if not activated:
                if token_file is not None or expected_revision is not None:
                    raise _blocked("BLOCKED_LEASE_NOT_FOUND")
                return function(target, change_id, *args, **kwargs)
            if token_file is None or expected_revision is None:
                raise _blocked("BLOCKED_WRITE_LEASE_REQUIRED")
            begun = begin_mutation(
                target, change_id, operation, token_file,
                expected_revision, repository_id=repository_id,
                workspace_ref=workspace_ref, state_root=state_root,
                timeout_seconds=timeout_seconds, now=coordination_now)
            context = {
                "key": _context_key(target, change_id),
                "operation": operation,
                "operation_id": begun["operation_id"],
                "lease_revision": begun["lease_revision"],
            }
            stack = _context_stack()
            stack.append(context)
            try:
                result = function(target, change_id, *args, **kwargs)
            except BaseException as original:
                try:
                    abort_mutation(
                        target, change_id, begun["operation_id"], token_file,
                        begun["lease_revision"], repository_id=repository_id,
                        state_root=state_root, timeout_seconds=timeout_seconds,
                        now=coordination_now)
                except CoordinationError as abort_error:
                    raise abort_error from original
                raise
            finally:
                stack.pop()
            finalized = finalize_mutation(
                target, change_id, begun["operation_id"], token_file,
                begun["lease_revision"], repository_id=repository_id,
                state_root=state_root, timeout_seconds=timeout_seconds,
                now=coordination_now)
            if isinstance(result, dict):
                result = dict(result)
                result["coordination"] = {
                    "status": finalized["status"],
                    "lease_revision": finalized["lease_revision"],
                    "change_truth_sha256": finalized["change_truth_sha256"],
                }
            return result
        return wrapped
    return decorate


def coordination_status(target, change_id=None, repository_id=None, state_root=None,
                        timeout_seconds=5.0, all_changes=False):
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
        if store is not None:
            matches = [item for item in store["change_leases"]
                       if item.get("change_id") == change_id]
            if matches:
                lease = matches[-1]
                result["status"] = lease.get("state", "BLOCKED")
                result["lease_revision"] = lease.get("lease_revision")
                result["accepted_change_truth_sha256"] = lease.get(
                    "change_truth_sha256")
                result["active_operation"] = (
                    None if lease.get("active_operation") is None else
                    lease["active_operation"].get("operation"))
    if all_changes and store is not None:
        latest = {}
        for lease in store["change_leases"]:
            latest[lease.get("change_id")] = lease
        result["changes"] = [{
            "change_id": cid,
            "status": lease.get("state"),
            "lease_revision": lease.get("lease_revision"),
            "change_truth_sha256": lease.get("change_truth_sha256"),
            "active_operation": (
                None if lease.get("active_operation") is None else
                lease["active_operation"].get("operation")),
        } for cid, lease in sorted(latest.items())]
        result["reservations"] = [{
            "change_id": item.get("change_id"),
            "state": item.get("state"),
            "sequence": item.get("sequence"),
        } for item in store["reservations"]]
    return result
