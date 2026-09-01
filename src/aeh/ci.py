"""Provider-neutral, read-only replay of AEH Change Assurance evidence."""
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import subprocess
import tempfile

import jsonschema
import yaml

from . import paths as aeh_paths
from .bootstrap import pipeline as bootstrap
from .doctor import doctor
from .runtime import approval
from .runtime import green


_SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")


class ReplayFailure(ValueError):
    def __init__(self, check_id, verdict, message):
        super().__init__(message)
        self.check_id = check_id
        self.verdict = verdict
        self.message = message


def _change_state_replay_ready(change, required_state):
    """Accept VERIFY or a later declared workflow phase after VERIFY passed."""
    current = (change.get("state") or {}).get("current")
    if current == required_state:
        return True
    if (change.get("gates") or {}).get("verify") != "PASS":
        return False
    phases = ((change.get("workflow") or {}).get("phases") or [])
    if current not in phases:
        return False
    if required_state in phases:
        anchor = phases.index(required_state)
    elif "REVIEW" in phases:
        # CRITICAL verifies from REGRESSION directly into REVIEW; VERIFY is a
        # gate result, not a phase in that workflow.
        anchor = phases.index("REVIEW")
    else:
        return False
    return phases.index(current) >= anchor


def _load_yaml(path):
    with open(path, "r", encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def _sha256_bytes(content):
    return hashlib.sha256(content).hexdigest()


def _sha256_file(path):
    with open(path, "rb") as stream:
        return _sha256_bytes(stream.read())


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _parse_observed_at(value):
    try:
        normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
        parsed = datetime.fromisoformat(normalized)
    except (AttributeError, ValueError) as exc:
        raise ReplayFailure("input.observed_at", "INVALID",
                            "observed_at must be an RFC3339 timestamp") from exc
    if parsed.tzinfo is None:
        raise ReplayFailure("input.observed_at", "INVALID",
                            "observed_at must include a timezone")
    return parsed.astimezone(timezone.utc)


def _git(target, *args):
    environment = dict(os.environ)
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    try:
        result = subprocess.run(
            ["git", "-C", target, *args], capture_output=True, text=True,
            timeout=15, check=False, env=environment,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ReplayFailure("scm.checkout", "INCONCLUSIVE",
                            "Git metadata could not be inspected") from exc
    if result.returncode != 0:
        raise ReplayFailure("scm.checkout", "INCONCLUSIVE",
                            "Git metadata command failed: " + " ".join(args))
    return result.stdout.strip()


def _git_blob(target, revision, relative):
    """Return raw revision bytes without invoking checkout filters."""
    environment = dict(os.environ)
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    result = subprocess.run(
        ["git", "-C", target, "show", revision + ":" + relative],
        capture_output=True, timeout=15, check=False, env=environment,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def _portable_content_hashes(content):
    """Return safe byte hashes for Git's ordinary LF/CRLF materializations."""
    variants = {content}
    if b"\x00" not in content:
        canonical = content.replace(b"\r\n", b"\n")
        variants.add(canonical)
        variants.add(canonical.replace(b"\n", b"\r\n"))
    return {_sha256_bytes(item) for item in variants}


def _remote_repository_id(remote):
    """Canonicalize an origin URL without contacting it."""
    value = remote.strip().replace("\\", "/")
    if "://" in value:
        from urllib.parse import urlsplit
        parsed = urlsplit(value)
        host = (parsed.hostname or "").lower()
        path = parsed.path.strip("/")
    elif ":" in value and "@" in value.split(":", 1)[0]:
        authority, path = value.split(":", 1)
        host = authority.rsplit("@", 1)[-1].lower()
        path = path.strip("/")
    else:
        return ""
    if path.endswith(".git"):
        path = path[:-4]
    return (host + "/" + path).lower() if host and path else ""


def _is_scm_metadata(relative):
    normalized = str(relative or "").replace("\\", "/").strip("/")
    return normalized == ".git" or normalized.startswith(".git/")


def _safe_target_file(target, relative):
    if not isinstance(relative, str) or not relative or os.path.isabs(relative):
        raise ReplayFailure("artifacts.paths", "INVALID", "artifact path is not repository-relative")
    normalized = relative.replace("\\", "/")
    if any(part in ("", ".", "..") for part in normalized.split("/")):
        raise ReplayFailure("artifacts.paths", "INVALID", "artifact path is not canonical: " + normalized)
    root = os.path.realpath(target)
    path = os.path.realpath(os.path.join(root, *normalized.split("/")))
    try:
        if os.path.commonpath([root, path]) != root:
            raise ReplayFailure("artifacts.paths", "INVALID", "artifact path escapes repository: " + normalized)
    except ValueError as exc:
        raise ReplayFailure("artifacts.paths", "INVALID", "artifact path escapes repository: " + normalized) from exc
    if not os.path.isfile(path):
        raise ReplayFailure("artifacts.present", "INVALID", "required file is missing: " + normalized)
    return path, normalized


class _Inputs:
    def __init__(self, target):
        self.target = os.path.realpath(target)
        self.values = {}

    def add(self, relative):
        path, normalized = _safe_target_file(self.target, relative)
        self.values[normalized] = _sha256_file(path)
        return path

    def items(self):
        return [{"path": path, "sha256": self.values[path]}
                for path in sorted(self.values)]


def _schema_validate(value, schema_path, label):
    try:
        jsonschema.validate(value, _load_yaml(schema_path))
    except (jsonschema.ValidationError, jsonschema.SchemaError, OSError, yaml.YAMLError) as exc:
        raise ReplayFailure("artifacts.schema", "INVALID",
                            label + " failed schema validation") from exc


def _level_of(change):
    classification = change.get("classification")
    if isinstance(classification, dict):
        return str(classification.get("level") or "").upper()
    return str(classification or "").upper()


def _verify_hash_reference(target, inputs, record, label):
    relative = record.get("output_ref")
    expected = str(record.get("output_hash") or "").lower()
    if not relative or not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise ReplayFailure("evidence.hashes", "INVALID", label + " has no valid output binding")
    path = inputs.add(relative)
    if _sha256_file(path) != expected:
        raise ReplayFailure("evidence.hashes", "INVALID", label + " output hash mismatch")


def _expected_traceability(spec, plan, implementation, verification):
    ac_to_tests = {}
    test_targets = {}
    for test in plan.get("tests", []):
        for ac_id in test.get("verifies", []):
            ac_to_tests.setdefault(ac_id, []).append(test["id"])
        test_targets[test["id"]] = list(test.get("targets", []))
    non_auto = {item["ac_id"]: item.get("reason", "")
                for item in plan.get("non_automatable", [])}
    changed_files = implementation.get("changed_files", [])
    verification_by_id = {item["id"]: item for item in verification.get("results", [])}
    requirements = []
    issues = []
    covered_code = set()
    used_tests = set()
    used_verification = set()
    for requirement in spec.get("requirements", []):
        acceptance = [item["id"] for item in requirement.get("acceptance", [])]
        tests = sorted({test_id for ac_id in acceptance
                        for test_id in ac_to_tests.get(ac_id, [])})
        used_tests.update(tests)
        for item in requirement.get("acceptance", []):
            if item.get("type") in ("automated", "invariant") and item["id"] not in ac_to_tests:
                if not non_auto.get(item["id"]):
                    issues.append("uncovered acceptance: " + item["id"])
        targets = {path.replace("\\", "/") for test_id in tests
                   for path in test_targets.get(test_id, [])}
        code = []
        for changed in changed_files:
            path = changed["path"].replace("\\", "/")
            if path in targets:
                entry = {"path": path}
                if changed.get("code_id"):
                    entry["code_id"] = changed["code_id"]
                code.append(entry)
                covered_code.add(path)
        verification_ids = []
        for verification_id, result in verification_by_id.items():
            if set(result.get("verifies", [])) & set(acceptance):
                verification_ids.append(verification_id)
                used_verification.add(verification_id)
            elif result.get("type") == "regression" and not result.get("verifies"):
                verification_ids.append(verification_id)
                used_verification.add(verification_id)
        requirements.append({"id": requirement["id"], "acceptance": acceptance,
                             "tests": tests, "code": code,
                             "verification": sorted(verification_ids)})
    known_acceptance = {item["id"] for requirement in spec.get("requirements", [])
                        for item in requirement.get("acceptance", [])}
    for test in plan.get("tests", []):
        if test["id"] not in used_tests:
            unknown = [item for item in test.get("verifies", []) if item not in known_acceptance]
            issues.append("orphan test: " + test["id"] + ":" + ",".join(unknown or ["none"]))
    for changed in changed_files:
        if changed["path"].replace("\\", "/") not in covered_code:
            issues.append("orphan code: " + changed["path"])
    for verification_id, result in verification_by_id.items():
        if verification_id not in used_verification and not (
                result.get("type") == "regression" and not result.get("verifies")):
            issues.append("orphan verification: " + verification_id)
    return {"requirements": requirements}, issues


def _check_tracked(target, relative):
    result = subprocess.run(
        ["git", "-C", target, "ls-files", "--error-unmatch", "--", relative],
        capture_output=True, text=True, timeout=15, check=False,
        env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
    )
    if result.returncode != 0:
        raise ReplayFailure("scm.tracked_inputs", "INVALID",
                            "consumed repository input is not tracked: " + relative)


def _build_report(repository_id, change_id, base_sha, head_sha, observed_at,
                  harness, policy_digest, verdict, checks, inputs):
    report = {
        "contract": "ci.replay-report", "version": 1,
        "repository_id": repository_id, "change_id": change_id,
        "base_sha": base_sha.lower(), "head_sha": head_sha.lower(),
        "observed_at": observed_at.isoformat(), "harness": harness,
        "policy_digest": policy_digest, "verdict": verdict,
        "checks": checks, "inputs": inputs,
        "safety": {"read_only_target": True, "project_code_executed": False,
                   "network_used": False},
    }
    report["canonical_digest"] = _sha256_bytes(_canonical(report))
    return report


def verify(target, change_id, repository_id, base_sha, head_sha, observed_at,
           credential_files=None, ae_root=None, accepted_approval_trust_modes=None,
           scm_authenticated_merge=False):
    """Replay committed assurance evidence without writing to the target."""
    ae_root = ae_root or aeh_paths.ae_root()
    target = os.path.realpath(target)
    accepted_trust_modes = set(accepted_approval_trust_modes or ())
    if scm_authenticated_merge:
        accepted_trust_modes.add(approval.SCM_AUTHENTICATED_MERGE)
    inputs = _Inputs(target)
    checks = []
    harness = {"version": "unknown", "source_revision": "unknown",
               "runtime_digest": "0" * 64}
    policy_digest = "0" * 64
    try:
        if not repository_id or not str(repository_id).strip():
            raise ReplayFailure("input.repository_id", "INVALID", "repository_id is required")
        if not _SHA_RE.fullmatch(str(base_sha)) or not _SHA_RE.fullmatch(str(head_sha)):
            raise ReplayFailure("input.revisions", "INVALID", "base_sha and head_sha must be full 40-hex Git IDs")
        observed = _parse_observed_at(observed_at)
        checks.append({"id": "input.contract", "status": "PASS", "message": "replay inputs are canonical"})

        actual_head = _git(target, "rev-parse", "HEAD").lower()
        if actual_head != head_sha.lower():
            raise ReplayFailure("scm.head", "INVALID", "checkout HEAD does not equal requested head_sha")
        dirty = _git(target, "status", "--porcelain=v1", "--untracked-files=all")
        if dirty:
            raise ReplayFailure("scm.clean", "INVALID", "checkout contains tracked or untracked changes")
        ancestor = subprocess.run(
            ["git", "-C", target, "merge-base", "--is-ancestor", base_sha, head_sha],
            capture_output=True, text=True, timeout=15, check=False,
            env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
        )
        if ancestor.returncode == 1:
            raise ReplayFailure("scm.base_head", "INVALID", "base_sha is not an ancestor of head_sha")
        if ancestor.returncode != 0:
            raise ReplayFailure("scm.base_head", "INCONCLUSIVE", "base/head ancestry could not be evaluated")
        remote_id = _remote_repository_id(_git(target, "config", "--get", "remote.origin.url"))
        if not remote_id:
            raise ReplayFailure("scm.repository", "INCONCLUSIVE", "remote.origin.url cannot establish repository identity")
        if remote_id != str(repository_id).strip().lower().removesuffix(".git").strip("/"):
            raise ReplayFailure("scm.repository", "INVALID", "repository_id does not match remote.origin.url")
        checks.append({"id": "scm.binding", "status": "PASS", "message": "clean exact base/head checkout"})

        manifest_path = inputs.add(".aeh/manifest.yaml")
        manifest = _load_yaml(manifest_path)
        runtime_digest = bootstrap.runtime_digest_at(target)
        expected_runtime = str(manifest.get("source_hashes", {}).get("runtime") or "").lower()
        if not runtime_digest or runtime_digest != expected_runtime:
            raise ReplayFailure("runtime.integrity", "INVALID", "installed runtime digest does not match manifest")
        harness_meta = manifest.get("harness", {})
        harness = {"version": str(harness_meta.get("version") or "unknown"),
                   "source_revision": str(harness_meta.get("source_revision") or "unknown"),
                   "runtime_digest": runtime_digest}
        for folder, suffix in (("core", ".yaml"), ("schemas", ".json")):
            runtime_folder = os.path.join(target, ".aeh", "runtime", folder)
            for name in sorted(os.listdir(runtime_folder)):
                if name.endswith(suffix):
                    inputs.add(".aeh/runtime/" + folder + "/" + name)
        for relative in (".aeh/profile.yaml", ".aeh/effective-workflow.yaml"):
            inputs.add(relative)
        health = doctor.run_doctor(target, ae_root)
        if health.get("overall") == "BLOCKED":
            raise ReplayFailure("runtime.doctor", "BLOCKED", "installed AEH doctor is BLOCKED")
        checks.append({"id": "runtime.integrity", "status": "PASS", "message": "installed runtime and project contracts are healthy"})

        policy_path = os.path.join(target, ".aeh", "runtime", "core", "ci-policy.yaml")
        policy = _load_yaml(policy_path)
        policy_schema = os.path.join(target, ".aeh", "runtime", "schemas", "ci-policy.schema.json")
        _schema_validate(policy, policy_schema, "ci-policy.yaml")
        policy_digest = _sha256_file(policy_path)

        change_prefix = ".aeh/changes/" + change_id + "/"
        documents = {}
        for name, schema_name in sorted(policy["required_artifacts"].items()):
            path = inputs.add(change_prefix + name)
            try:
                value = _load_yaml(path)
            except (OSError, yaml.YAMLError) as exc:
                raise ReplayFailure("artifacts.parse", "INVALID", name + " is not valid YAML") from exc
            schema_path = os.path.join(target, ".aeh", "runtime", "schemas", schema_name)
            _schema_validate(value, schema_path, name)
            documents[name] = value
        implementation_name = (
            "refactor.yaml"
            if os.path.isfile(os.path.join(target, change_prefix, "refactor.yaml"))
            else "green.yaml")
        implementation_path = inputs.add(change_prefix + implementation_name)
        implementation = _load_yaml(implementation_path)
        _schema_validate(implementation,
                         os.path.join(target, ".aeh", "runtime", "schemas", "green.schema.json"),
                         implementation_name)
        documents[implementation_name] = implementation
        approvals_path = os.path.join(target, change_prefix, "approvals.yaml")
        approvals_doc = None
        if os.path.isfile(approvals_path):
            inputs.add(change_prefix + "approvals.yaml")
            approvals_doc = _load_yaml(approvals_path)
            _schema_validate(approvals_doc,
                             os.path.join(target, ".aeh", "runtime", "schemas", "approvals.schema.json"),
                             "approvals.yaml")
        checks.append({"id": "artifacts.contracts", "status": "PASS", "message": "required machine artifacts satisfy installed schemas"})

        change = documents["change.yaml"]
        if change.get("change_id") != change_id:
            raise ReplayFailure("change.identity", "INVALID", "change.yaml does not bind requested change_id")
        if not _change_state_replay_ready(change, policy["required_change_state"]):
            raise ReplayFailure(
                "change.state", "BLOCKED",
                "Change has not reached required VERIFY or a later verified workflow state")
        missing_gates = [gate for gate in policy["required_gates"]
                         if change.get("gates", {}).get(gate) != "PASS"]
        if missing_gates:
            raise ReplayFailure("change.gates", "BLOCKED", "required Change gates are not PASS: " + ",".join(missing_gates))
        for artifact_name in ("evidence.yaml", "red.yaml", "test-lock.yaml", implementation_name):
            if documents[artifact_name].get("change_id") != change_id:
                raise ReplayFailure("change.identity", "INVALID", artifact_name + " does not bind requested change_id")
        checks.append({"id": "change.gates", "status": "PASS", "message": "Change state and required gates are complete"})

        plan = documents["test-plan.yaml"]
        lock_document = documents["test-lock.yaml"]
        for item in plan.get("test_files", []):
            inputs.add(item["dest"])
        for item in lock_document.get("files", []):
            inputs.add(item["path"])
        for protected_path in (lock_document.get("protected") or {}):
            if os.path.isfile(os.path.join(target, protected_path)):
                inputs.add(protected_path)
            else:
                inputs.add(change_prefix + protected_path)
        for evidence_item in documents["evidence.yaml"].get("evidence", []):
            source_path = (evidence_item.get("source_state") or {}).get("rel_path")
            if source_path and not _is_scm_metadata(source_path):
                inputs.add(source_path)
        try:
            lock, lock_hash = green._verify_lock(target, change_id, plan)
        except (green.GreenError, OSError, KeyError, TypeError) as exc:
            raise ReplayFailure("test.lock", "INVALID", "test/protected-file lock replay failed") from exc
        if implementation.get("test_lock_hash") != lock_hash:
            raise ReplayFailure("test.lock", "INVALID", implementation_name + " does not bind the current test lock")
        changed_paths = []
        for changed in implementation.get("changed_files", []):
            path = inputs.add(changed["path"])
            head_content = _git_blob(target, head_sha, changed["path"])
            if head_content is None or changed["after_hash"].lower() not in _portable_content_hashes(head_content):
                raise ReplayFailure("implementation.hashes", "INVALID", "production after_hash mismatch: " + changed["path"])
            base_content = _git_blob(target, base_sha, changed["path"])
            if base_content is not None and changed["before_hash"].lower() not in _portable_content_hashes(base_content):
                raise ReplayFailure("implementation.hashes", "INVALID", "production before_hash does not match base_sha: " + changed["path"])
            changed_paths.append(changed["path"])
        before_parts = sorted(item["before_hash"].lower() + "\0" + item["path"]
                              for item in implementation.get("changed_files", []))
        after_parts = sorted(item["after_hash"].lower() + "\0" + item["path"]
                             for item in implementation.get("changed_files", []))
        expected_before = _sha256_bytes("\n".join(before_parts).encode("utf-8"))
        expected_after = _sha256_bytes("\n".join(after_parts).encode("utf-8"))
        if implementation.get("production_before_hash", "").lower() != expected_before:
            raise ReplayFailure("implementation.hashes", "INVALID", "production_before_hash aggregate mismatch")
        if implementation.get("production_after_hash", "").lower() != expected_after:
            raise ReplayFailure("implementation.hashes", "INVALID", "production_after_hash aggregate mismatch")
        stale = green._stale_excluding(target, change_id, changed_paths)
        if stale:
            raise ReplayFailure("grounding.freshness", "BLOCKED", "grounding evidence is stale: " + ",".join(stale))
        checks.append({"id": "integrity.locks", "status": "PASS", "message": "test lock, protected context and production hashes replayed"})

        red = documents["red.yaml"]
        valid_red = [item for item in red.get("tests", []) if item.get("verdict") == "VALID_RED"]
        if not valid_red:
            raise ReplayFailure("evidence.red", "BLOCKED", "no VALID_RED evidence is present")
        for item in red.get("tests", []):
            _verify_hash_reference(target, inputs, item, "RED " + item.get("test_id", "?"))
            if item.get("base_commit") and str(item["base_commit"]).lower() != base_sha.lower():
                raise ReplayFailure("evidence.base", "INVALID", "RED evidence is bound to a different base")
        if implementation.get("base_commit") and str(implementation["base_commit"]).lower() != base_sha.lower():
            raise ReplayFailure("evidence.base", "INVALID", implementation_name + " is bound to a different base")
        for item in implementation.get("tests", []):
            if item.get("verdict") != "PASS":
                raise ReplayFailure("evidence.green", "BLOCKED", "implementation test evidence is not PASS")
            _verify_hash_reference(target, inputs, item, "implementation " + item.get("test_id", "?"))
        verification = documents["verification.yaml"]
        if verification.get("overall") not in policy["accepted_verification_overall"]:
            raise ReplayFailure("verification.overall", "BLOCKED", "verification overall is not merge-ready")
        for item in verification.get("results", []):
            if item.get("verdict") in ("fail", "pending", "rejected"):
                raise ReplayFailure("verification.results", "BLOCKED", "verification result is not accepted: " + item["id"])
            if item.get("output_ref") or item.get("output_hash"):
                _verify_hash_reference(target, inputs, item, "verification " + item["id"])
        checks.append({"id": "evidence.hashes", "status": "PASS", "message": "RED, implementation and verification evidence hashes replayed"})

        expected_trace, trace_issues = _expected_traceability(
            documents["spec.yaml"], plan, implementation, verification)
        if trace_issues or expected_trace != documents["traceability.yaml"]:
            raise ReplayFailure("traceability.complete", "INVALID", "traceability is incomplete or not the canonical projection")
        checks.append({"id": "traceability.complete", "status": "PASS", "message": "REQ/AC/TEST/CODE/VER links replayed bidirectionally"})

        approval_entries = approvals_doc.get("approvals", []) if approvals_doc else []
        if len({entry.get("gate") for entry in approval_entries}) != len(approval_entries):
            raise ReplayFailure("approvals.unique", "INVALID", "approval gates must be unique")
        approvals = {entry["gate"]: entry for entry in approval_entries}
        for entry in approval_entries:
            if entry.get("status") == "REJECTED":
                raise ReplayFailure("approvals.decision", "BLOCKED", "approval gate is REJECTED: " + entry["gate"])
            if entry.get("status") == "REVOKED":
                raise ReplayFailure("approvals.decision", "BLOCKED", "approval gate is REVOKED: " + entry["gate"])
            require_credential = entry["gate"] in policy["protected_approval_gates"]
            credential = entry.get("credential") or entry.get("revocation_credential") or {}
            key_id = credential.get("key_id")
            key_path = (credential_files or {}).get(key_id)
            if require_credential:
                trust_mode = entry.get("trust_mode")
                delegated = trust_mode in accepted_trust_modes
                if (scm_authenticated_merge and entry.get("gate") == "MERGE_GATE" and
                        trust_mode == approval.SCM_AUTHENTICATED_MERGE):
                    delegated = True
                if not key_path and not delegated:
                    raise ReplayFailure("approvals.credentials", "BLOCKED", "external approval credential is unavailable: " + entry["gate"])
                if key_path:
                    try:
                        key_inside_target = os.path.commonpath(
                            [target, os.path.realpath(key_path)]) == target
                    except ValueError:
                        key_inside_target = False
                    if key_inside_target:
                        raise ReplayFailure("approvals.credentials", "BLOCKED", "approval credential must be held outside the target repository: " + entry["gate"])
            assessment_entry = entry
            if not require_credential and credential and not key_path:
                # The repository may retain a locally verified signature for
                # an informational gate without exposing its HMAC key to CI.
                # Only policy-protected gates require remote credential proof.
                assessment_entry = dict(entry)
                assessment_entry.pop("credential", None)
            state, _warnings = approval.assess_approval(
                assessment_entry, now=observed, target=target, change_id=change_id,
                credential_files=credential_files, require_credential=require_credential,
                accepted_trust_modes=accepted_trust_modes)
            if state in ("INVALID", "UNVERIFIED"):
                raise ReplayFailure("approvals.credentials", "BLOCKED", "approval credential is unavailable or invalid: " + entry["gate"])
            if state == "EXPIRED":
                raise ReplayFailure("approvals.expiry", "BLOCKED", "approval is expired: " + entry["gate"])
        manual_required = any(item.get("type") == "manual" for item in verification.get("results", []))
        level = _level_of(change)
        required = []
        if manual_required:
            required.append(policy["manual_verification_gate"])
        if level == "CRITICAL":
            required.append(policy["critical_merge_gate"])
        for gate in sorted(set(required)):
            state, _warnings = approval.assess_approval(
                approvals.get(gate), now=observed, target=target, change_id=change_id,
                credential_files=credential_files, require_credential=True,
                accepted_trust_modes=accepted_trust_modes)
            if state != "APPROVED":
                raise ReplayFailure("approvals.required", "BLOCKED", "required approval is not effectively APPROVED: " + gate)
        checks.append({"id": "approvals.effective", "status": "PASS", "message": "required approvals are effective at observed_at"})

        for relative in sorted(inputs.values):
            _check_tracked(target, relative)
        checks.append({"id": "scm.tracked_inputs", "status": "PASS", "message": "all consumed repository inputs are committed at head_sha"})
        verdict = "PASS"
    except ReplayFailure as exc:
        observed = locals().get("observed")
        if observed is None:
            observed = datetime(1970, 1, 1, tzinfo=timezone.utc)
        checks.append({"id": exc.check_id, "status": exc.verdict, "message": exc.message})
        verdict = exc.verdict
    except (OSError, KeyError, TypeError, ValueError, yaml.YAMLError) as exc:
        observed = locals().get("observed") or datetime(1970, 1, 1, tzinfo=timezone.utc)
        checks.append({"id": "replay.internal", "status": "INCONCLUSIVE",
                       "message": "replay could not complete: " + exc.__class__.__name__})
        verdict = "INCONCLUSIVE"
    report = _build_report(str(repository_id or ""), str(change_id), str(base_sha),
                           str(head_sha), observed, harness, policy_digest,
                           verdict, checks, inputs.items())
    if verdict == "PASS":
        _schema_validate(report, os.path.join(ae_root, "schemas", "ci-report.schema.json"),
                         "CI replay report")
    return report


def write_report(report, path, target):
    """Atomically write a report only when its destination is outside target."""
    destination = os.path.realpath(path)
    root = os.path.realpath(target)
    try:
        inside_target = os.path.commonpath([root, destination]) == root
    except ValueError:
        inside_target = False
    if inside_target:
        raise ReplayFailure("output.boundary", "INVALID",
                            "report path must resolve outside the target repository")
    parent = os.path.dirname(destination) or os.getcwd()
    os.makedirs(parent, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".aeh-ci-", suffix=".tmp", dir=parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(report, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
        os.replace(temporary, destination)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
