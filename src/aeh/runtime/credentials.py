"""Credential signing and verification for AEH approval decisions."""
import hashlib
import hmac
import json
import os
import re


SCHEME = "hmac-sha256-v1"
_KEY_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_HEX_64 = re.compile(r"^[0-9a-f]{64}$")
MIN_KEY_BYTES = 32
MAX_KEY_BYTES = 4096


class CredentialError(ValueError):
    pass


def _key_path(target, key_id, explicit=None):
    if not isinstance(key_id, str) or not _KEY_ID.fullmatch(key_id):
        raise CredentialError("BLOCKED_BAD_KEY_ID: use 1..64 safe identifier characters")
    if explicit:
        return os.path.abspath(explicit)
    return os.path.join(target, ".aeh", "private", "approval-keys", key_id + ".key")


def _read_key(target, key_id, explicit=None):
    path = _key_path(target, key_id, explicit)
    try:
        with open(path, "rb") as stream:
            key = stream.read(MAX_KEY_BYTES + 1).strip()
    except OSError as exc:
        raise CredentialError("BLOCKED_CREDENTIAL_UNAVAILABLE: " + key_id) from exc
    if len(key) < MIN_KEY_BYTES or len(key) > MAX_KEY_BYTES:
        raise CredentialError(
            "BLOCKED_WEAK_CREDENTIAL: key must contain 32..4096 non-whitespace bytes")
    return key


def _canonical(payload):
    return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def decision_payload(entry, change_id, decision):
    if decision in ("APPROVED", "REJECTED"):
        payload = {
            "contract": "approval.credential",
            "version": 1,
            "change_id": change_id,
            "gate": entry.get("gate"),
            "decision": decision,
            "actor": entry.get("actor"),
            "decided_at": entry.get("decided_at"),
        }
        for field in ("expires_at", "evidence_ref"):
            if entry.get(field) is not None:
                payload[field] = entry[field]
        return payload
    if decision == "REVOKED":
        payload = {
            "contract": "approval.revocation-credential",
            "version": 1,
            "change_id": change_id,
            "gate": entry.get("gate"),
            "decision": "REVOKED",
            "revoked_by": entry.get("revoked_by"),
            "revoked_at": entry.get("revoked_at"),
        }
        if entry.get("revocation_evidence_ref") is not None:
            payload["revocation_evidence_ref"] = entry["revocation_evidence_ref"]
        original = entry.get("credential") or {}
        payload["original_payload_hash"] = original.get("payload_hash")
        return payload
    raise CredentialError("BLOCKED_BAD_STATUS: unsupported credential decision")


def sign(target, key_id, entry, change_id, decision, key_file=None):
    key = _read_key(target, key_id, key_file)
    payload_bytes = _canonical(decision_payload(entry, change_id, decision))
    payload_hash = hashlib.sha256(payload_bytes).hexdigest()
    return {
        "scheme": SCHEME,
        "key_id": key_id,
        "key_fingerprint": hashlib.sha256(key).hexdigest(),
        "payload_hash": payload_hash,
        "signature": hmac.new(key, payload_bytes, hashlib.sha256).hexdigest(),
    }


def verify(target, credential, entry, change_id, decision, key_files=None):
    if not isinstance(credential, dict) or credential.get("scheme") != SCHEME:
        return False, "unsupported or missing credential scheme"
    key_id = credential.get("key_id")
    explicit = (key_files or {}).get(key_id)
    try:
        key = _read_key(target, key_id, explicit)
    except CredentialError as exc:
        return False, str(exc)
    fingerprint = hashlib.sha256(key).hexdigest()
    if not hmac.compare_digest(str(credential.get("key_fingerprint", "")), fingerprint):
        return False, "credential key fingerprint mismatch"
    payload_bytes = _canonical(decision_payload(entry, change_id, decision))
    payload_hash = hashlib.sha256(payload_bytes).hexdigest()
    signature = hmac.new(key, payload_bytes, hashlib.sha256).hexdigest()
    if not _HEX_64.fullmatch(str(credential.get("payload_hash", ""))) or not \
            hmac.compare_digest(str(credential.get("payload_hash", "")), payload_hash):
        return False, "approval credential payload hash mismatch"
    if not _HEX_64.fullmatch(str(credential.get("signature", ""))) or not \
            hmac.compare_digest(str(credential.get("signature", "")), signature):
        return False, "approval credential signature mismatch"
    return True, "verified credential key_id=" + str(key_id)
