"""GitHub adapter, configured-policy transaction, and enforcement audit.

The module separates three claims: a workflow was observed, repository rules
require it, or an external organization/enterprise policy governs it.  It never
changes repository settings and it never executes project code.
"""
from base64 import b64decode
import fnmatch
import hashlib
import json
import os
import re
import subprocess
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

import jsonschema
import yaml

from . import ci
from . import paths as aeh_paths
from . import transaction as tx
from .bootstrap import pipeline as bootstrap_pipeline
from .runtime import approval as approval_runtime


SHA40 = re.compile(r"^[0-9a-f]{40}$")
CHANGE_PATH = re.compile(r"^\.aeh/changes/(CHG-[0-9]{4}-[0-9]{4})/change\.yaml$")
TRUST_RANK = {
    "OBSERVED_WORKFLOW": 1,
    "REQUIRED_REPOSITORY_WORKFLOW": 2,
    "EXTERNALLY_GOVERNED_WORKFLOW": 3,
}


class AssuranceFailure(ValueError):
    def __init__(self, check_id, verdict, message):
        super().__init__(message)
        self.check_id = check_id
        self.verdict = verdict
        self.message = message


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _digest(value):
    return hashlib.sha256(value if isinstance(value, bytes) else _canonical(value)).hexdigest()


def _read_document(path):
    with open(path, "r", encoding="utf-8") as stream:
        if path.lower().endswith(".json"):
            return json.load(stream)
        return yaml.safe_load(stream)


def load_policy(path=None, ae_root=None):
    root = ae_root or aeh_paths.ae_root()
    source = path or os.path.join(root, "core", "ci-enforcement-policy.yaml")
    policy = _read_document(source)
    schema = _read_document(os.path.join(root, "schemas", "ci-enforcement-policy.schema.json"))
    jsonschema.validate(policy, schema)
    return policy


def _path(value):
    if not isinstance(value, str) or not value or os.path.isabs(value):
        raise AssuranceFailure("diff.paths", "INVALID", "path is not repository-relative")
    normalized = value.replace("\\", "/")
    if any(part in ("", ".", "..") for part in normalized.split("/")):
        raise AssuranceFailure("diff.paths", "INVALID", "path is not canonical: " + normalized)
    return normalized


def _git(target, *arguments, binary=False, allow_failure=False):
    result = subprocess.run(
        ["git", "-C", target, *arguments], capture_output=True,
        text=not binary, timeout=20, check=False,
        env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
    )
    if result.returncode and not allow_failure:
        raise AssuranceFailure("scm.diff", "INCONCLUSIVE",
                               "Git inspection failed: " + " ".join(arguments))
    return result


def _head_yaml(target, head_sha, relative):
    result = _git(target, "show", head_sha + ":" + relative, binary=True)
    try:
        return yaml.safe_load(result.stdout.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise AssuranceFailure("diff.documents", "INVALID",
                               relative + " is not valid UTF-8 YAML") from exc


def discover_change(target, base_sha, head_sha, policy):
    """Select one newly introduced Change and prove the complete diff is declared."""
    if not SHA40.fullmatch(str(base_sha).lower()) or not SHA40.fullmatch(str(head_sha).lower()):
        raise AssuranceFailure("diff.revisions", "INVALID", "base/head must be full Git object IDs")
    ancestry = _git(target, "merge-base", "--is-ancestor", base_sha, head_sha,
                    allow_failure=True)
    if ancestry.returncode == 1:
        raise AssuranceFailure("diff.ancestry", "INVALID", "base is not an ancestor of head")
    if ancestry.returncode:
        raise AssuranceFailure("diff.ancestry", "INCONCLUSIVE", "base/head ancestry is unavailable")
    raw = _git(target, "diff", "--name-only", "-z", base_sha + ".." + head_sha,
               binary=True).stdout
    changed = sorted({_path(item.decode("utf-8")) for item in raw.split(b"\0") if item})
    candidates = [(CHANGE_PATH.fullmatch(item).group(1), item) for item in changed
                  if CHANGE_PATH.fullmatch(item)]
    if len(candidates) != 1:
        raise AssuranceFailure("diff.change_count", "INVALID",
                               "diff must introduce exactly one Change change.yaml; found " + str(len(candidates)))
    change_id, change_path = candidates[0]
    existed = _git(target, "cat-file", "-e", base_sha + ":" + change_path,
                   allow_failure=True)
    if existed.returncode == 0:
        raise AssuranceFailure("diff.change_freshness", "INVALID",
                               "selected Change already existed at base")
    if existed.returncode not in (0, 128):
        raise AssuranceFailure("diff.change_freshness", "INCONCLUSIVE",
                               "Change freshness could not be established")

    prefix = ".aeh/changes/" + change_id + "/"
    allowed = {item for item in changed if item.startswith(prefix)}
    implementation = None
    for name in ("green.yaml", "refactor.yaml"):
        result = _git(target, "cat-file", "-e", head_sha + ":" + prefix + name,
                      allow_failure=True)
        if result.returncode == 0:
            implementation = _head_yaml(target, head_sha, prefix + name)
            break
    if not implementation:
        raise AssuranceFailure("diff.declarations", "INVALID",
                               "selected Change has no green.yaml or refactor.yaml")
    for item in implementation.get("changed_files", []):
        allowed.add(_path(item.get("path")))
    for name, field in (("test-plan.yaml", "test_files"), ("test-lock.yaml", "files")):
        document = _head_yaml(target, head_sha, prefix + name)
        key = "dest" if name == "test-plan.yaml" else "path"
        for item in document.get(field, []):
            allowed.add(_path(item.get(key)))
    metadata = policy.get("governed_metadata", {})
    allowed.update(_path(item) for item in metadata.get("exact", []))
    prefixes = [_path(item).rstrip("/") + "/" for item in metadata.get("prefixes", [])]
    undeclared = [item for item in changed
                  if item not in allowed and not any(item.startswith(prefix) for prefix in prefixes)]
    if undeclared:
        raise AssuranceFailure("diff.closure", "INVALID",
                               "diff contains undeclared paths: " + ",".join(undeclared))
    return {
        "change_id": change_id,
        "changed_paths": changed,
        "allowed_paths": sorted(allowed),
        "diff_digest": _digest(changed),
    }


def normalize_event(payload, event_type):
    if event_type == "pull_request":
        source = payload.get("pull_request") or {}
        base_sha = (source.get("base") or {}).get("sha")
        head_sha = (source.get("head") or {}).get("sha")
        number = payload.get("number")
    elif event_type == "merge_group":
        source = payload.get("merge_group") or {}
        base_sha, head_sha, number = source.get("base_sha"), source.get("head_sha"), None
    else:
        raise AssuranceFailure("event.type", "INVALID", "unsupported GitHub event: " + str(event_type))
    repository = payload.get("repository") or {}
    normalized = {
        "contract": "ci.provider-event", "version": 1, "provider": "github",
        "event_type": event_type,
        "repository": {"id": repository.get("id"), "full_name": repository.get("full_name")},
        "base_sha": str(base_sha or "").lower(), "head_sha": str(head_sha or "").lower(),
        "pull_request_number": number,
    }
    schema = _read_document(os.path.join(aeh_paths.ae_root(), "schemas", "ci-provider-event.schema.json"))
    try:
        jsonschema.validate(normalized, schema)
    except jsonschema.ValidationError as exc:
        raise AssuranceFailure("event.contract", "INVALID", "GitHub event binding is incomplete") from exc
    return normalized


def _provider_report(binding, run, closure, replay, checks, verdict):
    report = {
        "contract": "ci.provider-assurance-report", "version": 1, "provider": "github",
        "event": binding, "run": {
            "id": run.get("id"), "attempt": run.get("run_attempt"),
            "check_suite_id": (run.get("check_suite") or {}).get("id"),
            "app_id": ((run.get("check_suite") or {}).get("app") or {}).get("id"),
            "workflow_path": (run.get("workflow") or {}).get("path"),
            "workflow_sha256": (run.get("workflow") or {}).get("sha256"),
        },
        "observed_at": run.get("updated_at") or run.get("created_at"),
        "change": closure, "replay": replay, "verdict": verdict, "checks": checks,
        "inputs": {"event_digest": _digest(binding), "run_snapshot_digest": _digest(run)},
        "safety": {"read_only_target": True, "project_code_executed": False,
                   "protected_credentials_available": False,
                   "merge_approval_channel": "SCM_AUTHENTICATED_MERGE"
                   if any(item.get("id") == "approval.channel" and
                          "delegated" in item.get("message", "") for item in checks)
                   else "HMAC_CREDENTIAL"},
    }
    report["canonical_digest"] = _digest(report)
    return report


def verify_event(target, event_payload, event_type, run_snapshot, policy=None):
    """Bind an authenticated GitHub run to one exact diff and invoke M6.1 replay."""
    policy = policy or load_policy()
    checks = []
    try:
        accepted_trust_modes = set()
        merge_channel = policy["approval"]["merge_gate"]
        if merge_channel == approval_runtime.SCM_AUTHENTICATED_MERGE:
            accepted_trust_modes.add(approval_runtime.SCM_AUTHENTICATED_MERGE)
            channel_message = (
                "MERGE_GATE is delegated to the authenticated SCM merge action; "
                "no HMAC identity claim is made"
            )
        else:
            channel_message = "MERGE_GATE requires an external HMAC credential"
        checks.append({"id": "approval.channel", "status": "PASS",
                       "message": channel_message})
        binding = normalize_event(event_payload, event_type)
        expected = policy["required_check"]
        workflow = run_snapshot.get("workflow") or {}
        suite = run_snapshot.get("check_suite") or {}
        if run_snapshot.get("event") != event_type:
            raise AssuranceFailure("run.event", "INVALID", "run event does not match event payload")
        if str(run_snapshot.get("head_sha") or "").lower() != binding["head_sha"]:
            raise AssuranceFailure("run.head", "INVALID", "authenticated run is not bound to event head")
        run_repo = run_snapshot.get("repository") or {}
        if run_repo.get("id") != binding["repository"]["id"] or run_repo.get("full_name") != binding["repository"]["full_name"]:
            raise AssuranceFailure("run.repository", "INVALID", "authenticated run repository differs from event")
        if ((suite.get("app") or {}).get("id")) != expected["app_id"]:
            raise AssuranceFailure("run.app", "INVALID", "check suite app does not match policy")
        check_run = run_snapshot.get("check_run") or {}
        if (check_run.get("name") != expected["name"] or
                check_run.get("head_sha") != binding["head_sha"] or
                ((check_run.get("app") or {}).get("id")) != expected["app_id"]):
            raise AssuranceFailure("run.check", "INVALID",
                                   "authenticated check run name, head, or app does not match policy")
        if workflow.get("path") != policy["workflow"]["path"]:
            raise AssuranceFailure("run.workflow", "INVALID", "workflow path does not match policy")
        expected_digest = policy["workflow"].get("expected_sha256")
        if not expected_digest:
            raise AssuranceFailure("run.workflow_digest", "BLOCKED", "workflow digest is not configured")
        if workflow.get("sha256") != expected_digest:
            raise AssuranceFailure("run.workflow_digest", "INVALID", "workflow digest does not match policy")
        observed_at = run_snapshot.get("updated_at") or run_snapshot.get("created_at")
        ci._parse_observed_at(observed_at)
        checks.append({"id": "provider.binding", "status": "PASS",
                       "message": "authenticated run binds repository, event, head, app, and workflow"})
        closure = discover_change(target, binding["base_sha"], binding["head_sha"], policy)
        checks.append({"id": "diff.closure", "status": "PASS",
                       "message": "exactly one fresh Change declares the complete diff"})
        replay = ci.verify(
            target, closure["change_id"], "github.com/" + binding["repository"]["full_name"],
            binding["base_sha"], binding["head_sha"], observed_at, credential_files={},
            accepted_approval_trust_modes=accepted_trust_modes,
        )
        if replay["verdict"] != "PASS":
            last = replay["checks"][-1]
            if last["id"] in ("approvals.credentials", "approvals.required"):
                raise AssuranceFailure("credentials.channel", "BLOCKED",
                                       "TRUSTED_CREDENTIAL_CHANNEL_REQUIRED")
            raise AssuranceFailure("replay.verdict", replay["verdict"],
                                   "M6.1 replay did not pass")
        checks.append({"id": "replay.verdict", "status": "PASS",
                       "message": "provider-neutral M6.1 replay passed"})
        return _provider_report(binding, run_snapshot, closure, replay, checks, "PASS")
    except (AssuranceFailure, ci.ReplayFailure) as exc:
        binding = locals().get("binding") or {
            "contract": "ci.provider-event", "version": 1, "provider": "github",
            "event_type": str(event_type), "repository": {"id": 0, "full_name": "unknown/unknown"},
            "base_sha": "0" * 40, "head_sha": "0" * 40, "pull_request_number": None,
        }
        closure = locals().get("closure") or {"change_id": None, "changed_paths": [],
                                               "allowed_paths": [], "diff_digest": _digest([])}
        replay = locals().get("replay")
        checks.append({"id": exc.check_id, "status": exc.verdict, "message": exc.message})
        return _provider_report(binding, run_snapshot, closure, replay, checks, exc.verdict)


def render_workflow(policy=None):
    """Render deterministic GitHub YAML; refuse mutable or absent AEH artifacts."""
    policy = policy or load_policy()
    artifact = policy["workflow"].get("artifact")
    if not artifact:
        raise AssuranceFailure("workflow.artifact", "BLOCKED", "IMMUTABLE_ARTIFACT_REQUIRED")
    checkout = policy["workflow"]["actions"]["checkout"]
    setup = policy["workflow"]["actions"]["setup_python"]
    content = f"""# Generated by AEH; edit the policy, not this file.
name: AEH assurance
on:
  pull_request:
  merge_group:
permissions:
  contents: read
  actions: read
  checks: read
jobs:
  verify:
    name: AEH assurance / verify
    runs-on: ubuntu-latest
    steps:
      - name: Checkout exact event head
        uses: actions/checkout@{checkout}
        with:
          ref: ${{{{ github.event.pull_request.head.sha || github.event.merge_group.head_sha }}}}
          fetch-depth: 0
          persist-credentials: false
          submodules: false
          lfs: false
      - name: Set up Python
        uses: actions/setup-python@{setup}
        with:
          python-version: '3.12'
      - name: Install immutable AEH wheel
        env:
          AEH_WHEEL_URL: {json.dumps(artifact['url'])}
          AEH_WHEEL_FILENAME: {artifact['filename']}
          AEH_WHEEL_SHA256: {artifact['sha256']}
        run: |
          python -c "import hashlib,os,urllib.request;p=os.path.join(os.environ['RUNNER_TEMP'],os.environ['AEH_WHEEL_FILENAME']);urllib.request.urlretrieve(os.environ['AEH_WHEEL_URL'],p);assert hashlib.sha256(open(p,'rb').read()).hexdigest()==os.environ['AEH_WHEEL_SHA256']"
          python -m pip install "$RUNNER_TEMP/$AEH_WHEEL_FILENAME"
      - name: Capture authenticated run metadata
        env:
          GH_TOKEN: ${{{{ github.token }}}}
        run: aeh ci github snapshot-run --policy core/ci-enforcement-policy.yaml --output "$RUNNER_TEMP/aeh-run.json"
      - name: Verify AEH assurance
        env:
          GITHUB_EVENT_NAME: ${{{{ github.event_name }}}}
        run: aeh ci github verify-event --event "$GITHUB_EVENT_PATH" --run-snapshot "$RUNNER_TEMP/aeh-run.json" --workdir . --policy core/ci-enforcement-policy.yaml --report "$RUNNER_TEMP/aeh-report.json"
"""
    result = {"contract": "ci.workflow-template", "version": 1, "provider": "github",
              "path": policy["workflow"]["path"], "sha256": _digest(content.encode("utf-8")),
              "content": content}
    schema = _read_document(os.path.join(aeh_paths.ae_root(), "schemas", "ci-workflow-template.schema.json"))
    jsonschema.validate(result, schema)
    return result


def _runtime_digest_with_policy(target, policy_content):
    """Compute the installed runtime digest with one staged policy override."""
    parts = []
    for folder in ("core", "schemas"):
        directory = os.path.join(target, ".aeh", "runtime", folder)
        if not os.path.isdir(directory):
            continue
        for name in sorted(os.listdir(directory)):
            path = os.path.join(directory, name)
            if not os.path.isfile(path):
                continue
            relative = folder + "/" + name
            if relative == "core/ci-enforcement-policy.yaml":
                content = policy_content
            else:
                with open(path, "rb") as stream:
                    content = stream.read()
            parts.append(relative + "\0" + _digest(content))
    return _digest(("\n".join(sorted(parts))).encode("utf-8"))


def configure_repository(target, artifact_url, artifact_filename, artifact_sha256):
    """Atomically configure policy, workflow, runtime snapshot, and manifest.

    This is the trusted post-build path that avoids embedding a wheel's own
    digest inside that wheel. It refuses to layer configuration on a runtime
    whose current manifest binding is already invalid.
    """
    target = os.path.abspath(target)
    parsed = urlsplit(str(artifact_url))
    digest = str(artifact_sha256).strip().lower()
    filename = str(artifact_filename).strip()
    if parsed.scheme != "https" or not parsed.netloc:
        raise AssuranceFailure("configure.artifact_url", "INVALID", "artifact URL must be absolute HTTPS")
    if not filename or os.path.basename(filename) != filename:
        raise AssuranceFailure("configure.artifact_filename", "INVALID", "artifact filename must be a basename")
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise AssuranceFailure("configure.artifact_sha256", "INVALID", "artifact SHA-256 must be 64 lowercase hex characters")

    actual_runtime, expected_runtime = bootstrap_pipeline.validate_runtime_integrity(target)
    if actual_runtime != expected_runtime:
        raise AssuranceFailure("configure.runtime", "BLOCKED", "installed runtime does not match manifest before configuration")

    source_policy_path = os.path.join(target, "core", "ci-enforcement-policy.yaml")
    policy = load_policy(source_policy_path)
    policy["workflow"]["artifact"] = {
        "url": str(artifact_url), "filename": filename, "sha256": digest,
    }
    rendered = render_workflow(policy)
    policy["workflow"]["expected_sha256"] = rendered["sha256"]
    rendered = render_workflow(policy)
    policy_content = yaml.safe_dump(policy, sort_keys=False, allow_unicode=True).encode("utf-8")
    runtime_digest = _runtime_digest_with_policy(target, policy_content)

    manifest_path = os.path.join(target, ".aeh", "manifest.yaml")
    manifest = _read_document(manifest_path)
    manifest.setdefault("source_hashes", {})["runtime"] = runtime_digest
    manifest_content = yaml.safe_dump(manifest, sort_keys=True, allow_unicode=True).encode("utf-8")
    workflow_content = rendered["content"].encode("utf-8")
    mutations = [
        {"action": "CONFIGURE_POLICY", "path": "core/ci-enforcement-policy.yaml",
         "kind": "file", "content": policy_content, "reason": "bind immutable assurance artifact"},
        {"action": "CONFIGURE_RUNTIME_POLICY", "path": ".aeh/runtime/core/ci-enforcement-policy.yaml",
         "kind": "file", "content": policy_content, "reason": "install configured policy snapshot"},
        {"action": "RENDER_ASSURANCE_WORKFLOW", "path": ".github/workflows/aeh-assurance.yml",
         "kind": "file", "content": workflow_content, "reason": "render deterministic assurance workflow"},
        {"action": "BIND_RUNTIME_DIGEST", "path": ".aeh/manifest.yaml",
         "kind": "file", "content": manifest_content, "reason": "bind configured runtime snapshot"},
    ]
    plan = {
        "contract": "ci.github-configuration-plan", "version": 1,
        "target": target, "artifact": policy["workflow"]["artifact"],
        "workflow_sha256": rendered["sha256"], "runtime_digest": runtime_digest,
        "paths": [item["path"] for item in mutations],
    }
    try:
        journal = tx.apply_mutations(target, "repair", "RPR", mutations, plan)
        bootstrap_pipeline.post_validate(target)
    except Exception as exc:
        if "journal" in locals() and journal:
            tx.rollback_transaction(target, journal["transaction_id"])
        raise AssuranceFailure("configure.transaction", "BLOCKED", str(exc)) from exc
    return {
        "verdict": "PASS", "status": "GITHUB_CONFIGURATION_APPLIED",
        "transaction_id": journal["transaction_id"] if journal else None,
        "workflow_sha256": rendered["sha256"], "runtime_digest": runtime_digest,
        "artifact": policy["workflow"]["artifact"],
    }


def _check(status, check_id, good, passed, failed):
    status.append({"id": check_id, "status": "PASS" if good else "BLOCKED",
                   "message": passed if good else failed})
    return good


def _applicable_rulesets(snapshot):
    branch_ref = "refs/heads/" + str(snapshot.get("branch") or "")
    result = []
    for ruleset in snapshot.get("rulesets", []):
        if ruleset.get("enforcement") != "active" or ruleset.get("target", "branch") != "branch":
            continue
        ref = (ruleset.get("conditions") or {}).get("ref_name") or {}
        includes = ref.get("include") or ["refs/heads/*"]
        excludes = ref.get("exclude") or []
        def matches(pattern):
            if pattern == "~DEFAULT_BRANCH":
                default_branch = (snapshot.get("repository") or {}).get("default_branch")
                return bool(default_branch) and branch_ref == "refs/heads/" + default_branch
            return fnmatch.fnmatchcase(branch_ref, pattern)
        if any(matches(item) for item in includes) and not any(matches(item) for item in excludes):
            result.append(ruleset)
    return result


def audit_enforcement(policy, snapshot):
    """Evaluate an authenticated provider snapshot without mutating GitHub."""
    snapshot_schema = _read_document(os.path.join(
        aeh_paths.ae_root(), "schemas", "ci-provider-snapshot.schema.json"))
    jsonschema.validate(snapshot, snapshot_schema)
    checks = []
    errors = snapshot.get("api_errors") or []
    protection = snapshot.get("branch_protection") or {}
    required = (protection.get("required_status_checks") or {})
    expected = policy["required_check"]
    contexts = required.get("checks") or []
    branch_exact_check = any(item.get("context") == expected["name"] and
                             item.get("app_id") == expected["app_id"] for item in contexts)
    rulesets = _applicable_rulesets(snapshot)
    rules = [rule for ruleset in rulesets for rule in ruleset.get("rules", [])]
    status_rules = [rule for rule in rules if rule.get("type") == "required_status_checks"]
    ruleset_exact_check = any(
        item.get("context") == expected["name"] and
        item.get("integration_id") == expected["app_id"]
        for rule in status_rules
        for item in (rule.get("parameters") or {}).get("required_status_checks", []))
    exact_check = branch_exact_check or ruleset_exact_check
    strict = required.get("strict") is True or any(
        (rule.get("parameters") or {}).get("strict_required_status_checks_policy") is True
        for rule in status_rules)
    force_disabled = ((protection.get("allow_force_pushes") or {}).get("enabled") is False or
                      any(rule.get("type") == "non_fast_forward" for rule in rules))
    delete_disabled = ((protection.get("allow_deletions") or {}).get("enabled") is False or
                       any(rule.get("type") == "deletion" for rule in rules))
    requirements = [
        _check(checks, "rules.required_check_app", exact_check,
               "required check is bound to the expected GitHub App", "exact required check/App binding is absent"),
        _check(checks, "rules.strict", strict,
               "strict up-to-date checks are required", "strict required checks are not enabled"),
        _check(checks, "rules.force_push", force_disabled,
               "force pushes are disabled", "force pushes are not proven disabled"),
        _check(checks, "rules.deletion", delete_disabled,
               "branch deletion is disabled", "branch deletion is not proven disabled"),
        _check(checks, "rules.admins", ((protection.get("enforce_admins") or {}).get("enabled") is True or bool(rulesets)),
               "branch protection includes administrators", "administrator enforcement is not enabled"),
    ]
    review_bypass = (protection.get("required_pull_request_reviews") or {}).get(
        "bypass_pull_request_allowances") or {}
    branch_bypass = any(review_bypass.get(kind) for kind in ("users", "teams", "apps"))
    ruleset_bypass = any(ruleset.get("bypass_actors") for ruleset in rulesets)
    requirements.append(_check(
        checks, "rules.bypass", not branch_bypass and not ruleset_bypass,
        "no explicit branch or active-ruleset bypass actor was observed",
        "explicit bypass actors are configured"))
    workflow = snapshot.get("workflow") or {}
    workflow_ok = bool(policy["workflow"].get("expected_sha256")) and (
        workflow.get("path") == policy["workflow"]["path"] and
        workflow.get("sha256") == policy["workflow"]["expected_sha256"] and
        set(policy["required_events"]).issubset(set(workflow.get("events") or [])))
    requirements.append(_check(checks, "workflow.identity", workflow_ok,
                               "workflow path, digest, and events match policy",
                               "workflow identity/events are unconfigured or mismatched"))
    current_check = any(item.get("name") == expected["name"] and
                        ((item.get("app") or {}).get("id")) == expected["app_id"] and
                        item.get("head_sha") == snapshot.get("head_sha") and
                        item.get("conclusion") == "success" for item in snapshot.get("check_runs", []))
    requirements.append(_check(checks, "head.required_check", current_check,
                               "latest branch head has the exact successful check",
                               "latest branch head lacks the exact successful check"))
    external = snapshot.get("external_governance") or {}
    external_ok = bool(
        external.get("required_workflow") is True and
        external.get("immutable_policy_ref") and
        external.get("workflow_path") == policy["workflow"]["path"] and
        external.get("workflow_sha256") == policy["workflow"].get("expected_sha256") and
        external.get("check_name") == expected["name"] and
        external.get("app_id") == expected["app_id"] and
        workflow_ok and current_check)
    achieved = ("EXTERNALLY_GOVERNED_WORKFLOW" if external_ok else
                "REQUIRED_REPOSITORY_WORKFLOW" if all(requirements) else
                "OBSERVED_WORKFLOW")
    required_level = policy["required_trust_level"]
    if errors:
        checks.append({"id": "provider.api", "status": "INCONCLUSIVE",
                       "message": "provider metadata incomplete: " + ";".join(errors)})
        verdict = "INCONCLUSIVE"
    else:
        verdict = "PASS" if TRUST_RANK[achieved] >= TRUST_RANK[required_level] else "BLOCKED"
    residual = [
        "Repository and organization administrators may retain rule-edit authority.",
        "Configured bypass actors may merge without the required check.",
        "GitHub and installed GitHub Apps remain external trust authorities.",
    ]
    if branch_bypass or ruleset_bypass:
        residual.append("Branch or ruleset policy declares explicit bypass actors.")
    report = {
        "contract": "ci.enforcement-report", "version": 1, "provider": "github",
        "repository_id": str((snapshot.get("repository") or {}).get("id") or "unknown"),
        "branch": str(snapshot.get("branch") or "unknown"),
        "head_sha": str(snapshot.get("head_sha") or "0" * 40).lower(),
        "required_trust_level": required_level, "achieved_trust_level": achieved,
        "verdict": verdict, "checks": checks, "residual_authorities": residual,
        "snapshot_digest": _digest(snapshot),
    }
    report["canonical_digest"] = _digest(report)
    schema = _read_document(os.path.join(aeh_paths.ae_root(), "schemas", "ci-enforcement-report.schema.json"))
    jsonschema.validate(report, schema)
    return report


def _api(repository, path, token, api_url="https://api.github.com"):
    request = Request(api_url.rstrip("/") + "/repos/" + repository + path,
                      headers={"Accept": "application/vnd.github+json",
                               "Authorization": "Bearer " + token,
                               "X-GitHub-Api-Version": "2022-11-28",
                               "User-Agent": "AEH-M6.2"})
    with urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_enforcement_snapshot(repository, branch, token, policy, api_url="https://api.github.com"):
    """Read current GitHub enforcement metadata. HTTP failures become audit evidence."""
    errors = []
    values = {}
    endpoints = {
        "repository": "", "branch_data": "/branches/" + quote(branch, safe=""),
        "branch_protection": "/branches/" + quote(branch, safe="") + "/protection",
        "rulesets": "/rulesets", "workflow_file": "/contents/" + quote(policy["workflow"]["path"], safe="/"),
    }
    for key, endpoint in endpoints.items():
        try:
            values[key] = _api(repository, endpoint, token, api_url)
        except (HTTPError, URLError, OSError, ValueError) as exc:
            values[key] = None if key != "rulesets" else []
            errors.append(key + ":" + exc.__class__.__name__)
    detailed_rulesets = []
    for item in values.get("rulesets") or []:
        ruleset_id = item.get("id")
        if not ruleset_id:
            errors.append("ruleset_detail:missing_id")
            continue
        try:
            detailed_rulesets.append(_api(
                repository, "/rulesets/" + str(ruleset_id), token, api_url))
        except (HTTPError, URLError, OSError, ValueError) as exc:
            errors.append("ruleset_" + str(ruleset_id) + ":" + exc.__class__.__name__)
    head = (((values.get("branch_data") or {}).get("commit") or {}).get("sha") or "0" * 40)
    try:
        checks = _api(repository, "/commits/" + head + "/check-runs", token, api_url).get("check_runs", [])
    except (HTTPError, URLError, OSError, ValueError) as exc:
        checks = []
        errors.append("check_runs:" + exc.__class__.__name__)
    workflow = None
    encoded = (values.get("workflow_file") or {}).get("content")
    if encoded:
        content = b64decode(encoded).decode("utf-8")
        events = [event for event in ("pull_request", "merge_group")
                  if re.search(r"(?m)^\s*" + event + r"\s*:", content)]
        workflow = {"path": policy["workflow"]["path"],
                    "sha256": _digest(content.encode("utf-8")), "events": events}
    return {
        "contract": "ci.provider-snapshot", "version": 1,
        "repository": {"id": (values.get("repository") or {}).get("id"),
                       "full_name": (values.get("repository") or {}).get("full_name") or repository,
                       "default_branch": (values.get("repository") or {}).get("default_branch")},
        "branch": branch, "head_sha": head, "branch_protection": values.get("branch_protection"),
        "rulesets": detailed_rulesets, "workflow": workflow, "check_runs": checks,
        "external_governance": {}, "api_errors": errors,
    }


def fetch_run_snapshot(repository, run_id, token, policy, api_url="https://api.github.com"):
    workflow_path = policy["workflow"]["path"]
    run = _api(repository, "/actions/runs/" + str(run_id), token, api_url)
    suite_id = run.get("check_suite_id")
    if not suite_id:
        raise AssuranceFailure("run.check_suite", "INCONCLUSIVE",
                               "workflow run has no check_suite_id")
    suite = _api(repository, "/check-suites/" + str(suite_id), token, api_url)
    check_runs = _api(repository, "/check-suites/" + str(suite_id) + "/check-runs",
                      token, api_url).get("check_runs", [])
    workflow = _api(repository, "/contents/" + quote(workflow_path, safe="/") +
                    "?ref=" + quote(run["head_sha"], safe=""), token, api_url)
    content = b64decode(workflow["content"])
    expected_name = policy["required_check"]["name"]
    exact_runs = [item for item in check_runs if item.get("name") == expected_name]
    if len(exact_runs) != 1:
        raise AssuranceFailure("run.check", "INCONCLUSIVE",
                               "exactly one expected check run was not found")
    return {
        "id": run["id"], "run_attempt": run.get("run_attempt", 1), "event": run["event"],
        "head_sha": run["head_sha"], "created_at": run["created_at"], "updated_at": run["updated_at"],
        "repository": {"id": run["repository"]["id"], "full_name": run["repository"]["full_name"]},
        "check_suite": {"id": suite.get("id"), "app": suite.get("app") or {}},
        "check_run": {"id": exact_runs[0].get("id"), "name": exact_runs[0].get("name"),
                      "head_sha": exact_runs[0].get("head_sha"),
                      "app": exact_runs[0].get("app") or {}},
        "workflow": {"path": workflow_path, "sha256": _digest(content)},
    }


def write_json(value, path):
    parent = os.path.dirname(os.path.realpath(path)) or os.getcwd()
    os.makedirs(parent, exist_ok=True)
    temporary = os.path.join(parent, ".aeh-github-" + str(os.getpid()) + ".tmp")
    try:
        with open(temporary, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
