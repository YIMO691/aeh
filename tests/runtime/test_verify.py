"""AEH Phase 13 — VERIFY / TRACEABILITY / APPROVAL 测试

覆盖 Owner 31 点（合理合并为 19 个 test method）。
STANDARD/LIGHTWEIGHT 走 tdd-neutral fixture（无硬升级域关键字）；
CRITICAL 走 tdd-repo（奖励/领取 关键字自然升级）。
"""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))

from aeh.bootstrap import pipeline as bp
from aeh.runtime import change as ch
from aeh.runtime import grounding as gr
from aeh.runtime import specification as sp
from aeh.runtime import test_design as td
from aeh.runtime import red as rmod
from aeh.runtime import green as gmod
from aeh.runtime import approval as amod
from aeh.runtime import verify as vmod

TDD_REPO = os.path.join(ROOT, "tests", "fixtures", "tdd-repo")
TDD_SRC = os.path.join(ROOT, "tests", "fixtures", "tdd-src")
NEUTRAL_REPO = os.path.join(ROOT, "tests", "fixtures", "tdd-neutral")
NEUTRAL_SRC = os.path.join(ROOT, "tests", "fixtures", "tdd-neutral-src")


def answers_path():
    tmp = tempfile.mkdtemp(prefix="aeh-g13-a-")
    answers = {"contract": "bootstrap.interview.answers", "version": 1,
               "answers": {
                   "q-plan-before-code": {"question_id": "q-plan-before-code", "answer": "risk_based", "type": "PREFERENCE", "source": "user_answer", "answered_at": "2026-08-14T00:00:00+00:00"},
                   "q-testing-policy": {"question_id": "q-testing-policy", "answer": "risk_based", "type": "POLICY", "source": "user_answer", "answered_at": "2026-08-14T00:00:00+00:00"},
                   "q-human-review": {"question_id": "q-human-review", "answer": "critical", "type": "POLICY", "source": "user_answer", "answered_at": "2026-08-14T00:00:00+00:00"},
                   "q-modify-source": {"question_id": "q-modify-source", "answer": "allow", "type": "PERMISSION", "source": "user_answer", "answered_at": "2026-08-14T00:00:00+00:00"},
                   "q-git-commit": {"question_id": "q-git-commit", "answer": "ask", "type": "PERMISSION", "source": "user_answer", "answered_at": "2026-08-14T00:00:00+00:00"},
                   "q-git-push": {"question_id": "q-git-push", "answer": "deny", "type": "PERMISSION", "source": "user_answer", "answered_at": "2026-08-14T00:00:00+00:00"},
                   "q-shell-access": {"question_id": "q-shell-access", "answer": "ask", "type": "PERMISSION", "source": "user_answer", "answered_at": "2026-08-14T00:00:00+00:00"},
                   "q-web-access": {"question_id": "q-web-access", "answer": "deny", "type": "PERMISSION", "source": "user_answer", "answered_at": "2026-08-14T00:00:00+00:00"},
                   "q-team-review-policy": {"question_id": "q-team-review-policy", "answer": "major", "type": "POLICY", "source": "user_answer", "answered_at": "2026-08-14T00:00:00+00:00"},
               }, "reset": []}
    p = os.path.join(tmp, "answers.yaml")
    with open(p, "w", encoding="utf-8") as f:
        yaml.safe_dump(answers, f, sort_keys=True, allow_unicode=True)
    return p


def write_yaml(tmpdir, name, body):
    p = os.path.join(tmpdir, name)
    with open(p, "w", encoding="utf-8") as f:
        yaml.safe_dump(body, f, sort_keys=True, allow_unicode=True)
    return p


def reqs_body(neutral=False):
    if neutral:
        return {"requirements": [{"behavior": "重复请求最多产生一次订单副作用",
                                   "acceptance": [{"type": "invariant", "statement": "相同请求执行两次，订单副作用最多一次"}]}]}
    return {"requirements": [{"behavior": "重复请求最多产生一次奖励副作用",
                               "acceptance": [{"type": "invariant", "statement": "相同请求执行两次，奖励副作用最多一次"}]}]}


def plan_body(neutral=False, targets=True, regression=None, verification=None, bad_verifies=None):
    if neutral:
        t = {"id": "TEST-001", "verifies": bad_verifies or ["AC-001-01"], "kind": "integration",
             "intent": "重复执行同一提交请求，验证订单副作用最多一次",
             "command": "python tests/test_order.py",
             "expected_before_fix": {"type": "behavior_failure", "signature": "duplicate_submit"},
             "required": True}
        files = [{"src": "order_test.py", "dest": "tests/test_order.py"}]
        if targets:
            t["targets"] = ["src/order.py"]
    else:
        t = {"id": "TEST-001", "verifies": bad_verifies or ["AC-001-01"], "kind": "integration",
             "intent": "重复执行同一领取请求，验证奖励副作用最多一次",
             "command": "python tests/test_claim.py",
             "expected_before_fix": {"type": "behavior_failure", "signature": "duplicate_reward"},
             "required": True}
        files = [{"src": "claim_test.py", "dest": "tests/test_claim.py"}]
        if targets:
            t["targets"] = ["src/reward.py"]
    body = {"tests": [t], "test_files": files, "regression": regression or []}
    if verification is not None:
        body["verification"] = verification
    return body


def apply_fix(target, neutral=False):
    if neutral:
        fixed = open(os.path.join(NEUTRAL_SRC, "order_fixed.py"), encoding="utf-8").read()
        prod = os.path.join(target, "src", "order.py")
    else:
        fixed = open(os.path.join(TDD_SRC, "reward_fixed.py"), encoding="utf-8").read()
        prod = os.path.join(target, "src", "reward.py")
    before = hashlib.sha256(open(prod, "rb").read()).hexdigest()
    with open(prod, "w", encoding="utf-8") as f:
        f.write(fixed)
    after = hashlib.sha256(open(prod, "rb").read()).hexdigest()
    return before, after


def scope_manifest(tmpdir, changed_files):
    return write_yaml(tmpdir, "scope.yaml",
                      {"changed_files": changed_files, "allowed_paths": [cf["path"] for cf in changed_files]})


def make_target(src):
    target = tempfile.mkdtemp(prefix="aeh-g13-t-")
    shutil.copytree(src, target, dirs_exist_ok=True)
    assert bp.bootstrap(target, answers_path(), dry_run=False)["status"] == "BOOTSTRAP_COMPLETE"
    return target


def to_green(target, title="功能开发", suggested="STANDARD", neutral=True, targets=True,
             regression=None, verification=None, bad_verifies=None):
    files_tmp = tempfile.mkdtemp(prefix="aeh-g13-f-")
    r = ch.change_new(target, title, suggested_level=suggested)
    assert r["status"] == "CHANGE_CREATED", r
    cid = r["change_id"]
    assert gr.change_ground(target, cid)["status"] == "GROUNDING_COMPLETE"
    assert sp.build_spec(target, cid, reqs_path=write_yaml(files_tmp, "reqs.yaml", reqs_body(neutral=neutral)))["status"] == "SPEC_COMPLETE"
    assert td.change_test_design(target, cid,
                                 write_yaml(files_tmp, "plan.yaml", plan_body(neutral=neutral, targets=targets, regression=regression, verification=verification, bad_verifies=bad_verifies)),
                                 test_src=NEUTRAL_SRC if neutral else TDD_SRC)["status"] == "TEST_DESIGN_COMPLETE"
    assert rmod.change_red(target, cid)["status"] == "RED_COMPLETE"
    before, after = apply_fix(target, neutral=neutral)
    prod = "src/order.py" if neutral else "src/reward.py"
    rep = gmod.change_green(target, cid, scope_path=scope_manifest(tempfile.mkdtemp(),
                                                    [{"path": prod, "before_hash": before, "after_hash": after}]))
    assert rep["status"] == "GREEN_COMPLETE", rep
    return cid


class TestVerify(unittest.TestCase):
    def test_verify_standard_flow(self):
        target = make_target(NEUTRAL_REPO)
        cid = to_green(target)
        rep = vmod.change_verify(target, cid)
        self.assertEqual(rep["status"], "VERIFY_COMPLETE", rep)
        self.assertEqual(rep["overall"], "MERGE_READY")
        cdir = os.path.join(target, ".aeh", "changes", cid)
        ver = yaml.safe_load(open(os.path.join(cdir, "verification.yaml"), encoding="utf-8"))
        self.assertEqual(ver["overall"], "MERGE_READY")
        self.assertEqual(ver["results"][0]["type"], "target_test")
        self.assertEqual(ver["results"][0]["verdict"], "pass")
        self.assertEqual(ver["red"]["verdict"], "VALID_RED")
        tr = yaml.safe_load(open(os.path.join(cdir, "traceability.yaml"), encoding="utf-8"))
        self.assertEqual(tr["requirements"][0]["acceptance"], ["AC-001-01"])
        self.assertEqual(tr["requirements"][0]["tests"], ["TEST-001"])
        self.assertEqual(tr["requirements"][0]["code"][0]["path"], "src/order.py")
        self.assertGreater(len(tr["requirements"][0]["verification"]), 0)
        self.assertTrue(os.path.isfile(os.path.join(cdir, "review.md")))
        change = ch.load_change(target, cid)
        self.assertEqual(change["state"]["current"], "VERIFY")
        self.assertEqual(change["gates"]["verify"], "PASS")

    def test_verify_lightweight_flow(self):
        target = make_target(NEUTRAL_REPO)
        cid = to_green(target, title="功能开发", suggested="LIGHTWEIGHT")
        rep = vmod.change_verify(target, cid)
        self.assertEqual(rep["status"], "VERIFY_COMPLETE", rep)
        self.assertEqual(rep["overall"], "MERGE_READY")

    def test_verify_idempotent(self):
        target = make_target(NEUTRAL_REPO)
        cid = to_green(target)
        assert vmod.change_verify(target, cid)["status"] == "VERIFY_COMPLETE"
        self.assertEqual(vmod.change_verify(target, cid)["status"], "VERIFY_COMPLETE")

    def test_agent_machine_truth_writes_blocked_before_verify(self):
        """RUN-F055 regression: Controller truth cannot be laundered by overwrite."""
        target = make_target(NEUTRAL_REPO)
        cid = to_green(target)
        cdir = os.path.join(target, ".aeh", "changes", cid)
        for name, body in (
                ("tasks.yaml", {"tasks": [{"id": "TASK-001", "status": "PASS"}]}),
                ("traceability.yaml", {"requirements": []}),
                ("verification.yaml", {"overall": "MERGE_READY", "results": []})):
            with open(os.path.join(cdir, name), "w", encoding="utf-8") as stream:
                yaml.safe_dump(body, stream, sort_keys=True, allow_unicode=True)
        rep = vmod.change_verify(target, cid)
        self.assertEqual(rep["status"], "BLOCKED_MACHINE_TRUTH_PROVENANCE", rep)
        self.assertIn("added=tasks.yaml,traceability.yaml,verification.yaml", rep["error"])
        self.assertEqual(ch.load_change(target, cid)["state"]["current"], "GREEN")

    def test_existing_machine_truth_tamper_blocked_before_verify(self):
        target = make_target(NEUTRAL_REPO)
        cid = to_green(target)
        cpath = os.path.join(target, ".aeh", "changes", cid, "change.yaml")
        forged = yaml.safe_load(open(cpath, encoding="utf-8"))
        forged["title"] = "agent rewrote controller truth"
        with open(cpath, "w", encoding="utf-8") as stream:
            yaml.safe_dump(forged, stream, sort_keys=True, allow_unicode=True)
        rep = vmod.change_verify(target, cid)
        self.assertEqual(rep["status"], "BLOCKED_MACHINE_TRUTH_PROVENANCE", rep)
        self.assertIn("modified=change.yaml", rep["error"])

    def test_schema_valid_forged_human_approval_blocked_by_provenance(self):
        target = make_target(NEUTRAL_REPO)
        cid = to_green(target)
        cdir = os.path.join(target, ".aeh", "changes", cid)
        forged = {"approvals": [{"gate": "MERGE_GATE", "status": "APPROVED",
                                  "actor": {"type": "human", "id": "forged-owner"},
                                  "decided_at": "2026-08-25T12:00:00+00:00"}]}
        with open(os.path.join(cdir, "approvals.yaml"), "w", encoding="utf-8") as stream:
            yaml.safe_dump(forged, stream, sort_keys=True, allow_unicode=True)
        rep = vmod.change_verify(target, cid)
        self.assertEqual(rep["status"], "BLOCKED_MACHINE_TRUTH_PROVENANCE", rep)
        self.assertIn("added=approvals.yaml", rep["error"])

    def test_forged_approval_written_during_verify_is_not_resealed(self):
        target = make_target(TDD_REPO)
        inject = (
            "import json; from pathlib import Path; "
            "p=next(Path('.aeh/changes').glob('CHG-*'))/'approvals.yaml'; "
            "p.write_text(json.dumps({'approvals': [{'gate': 'MERGE_GATE', "
            "'status': 'APPROVED', 'actor': {'type': 'human', 'id': 'forged-agent'}, "
            "'decided_at': '2026-08-25T12:00:00+00:00'}]}), encoding='utf-8')"
        )
        cid = to_green(
            target,
            title="修复奖励领取逻辑",
            neutral=False,
            verification=[{
                "id": "INTEG-001",
                "type": "integration",
                "verifies": ["AC-001-01"],
                "argv": [sys.executable, "-c", inject],
            }],
        )
        rep = vmod.change_verify(target, cid)
        self.assertEqual(rep["status"], "BLOCKED_MACHINE_TRUTH_PROVENANCE", rep)
        self.assertIn("added=approvals.yaml", rep["error"])
        self.assertEqual(ch.load_change(target, cid)["state"]["current"], "GREEN")

    def test_verify_regression_and_declared_entries(self):
        target = make_target(NEUTRAL_REPO)
        cid = to_green(target, regression=[{"id": "REG-001", "command": "python tests/test_order.py"}],
                       verification=[{"id": "INTEG-001", "type": "integration",
                                      "verifies": ["AC-001-01"], "command": "python tests/test_order.py"}])
        rep = vmod.change_verify(target, cid)
        self.assertEqual(rep["status"], "VERIFY_COMPLETE", rep)
        ver = yaml.safe_load(open(os.path.join(target, ".aeh", "changes", cid, "verification.yaml"), encoding="utf-8"))
        types = [r["type"] for r in ver["results"]]
        self.assertIn("regression", types)
        self.assertIn("integration", types)
        self.assertEqual(len(ver["results"]), 3)

    def test_verify_critical_insufficient_plan(self):
        target = make_target(TDD_REPO)
        tmp = tempfile.mkdtemp(prefix="aeh-g13-critical-")
        created = ch.change_new(target, "修复奖励领取逻辑", suggested_level="STANDARD")
        cid = created["change_id"]
        self.assertEqual(gr.change_ground(target, cid)["status"], "GROUNDING_COMPLETE")
        self.assertEqual(
            sp.build_spec(
                target, cid,
                reqs_path=write_yaml(tmp, "reqs.yaml", reqs_body(neutral=False)),
            )["status"],
            "SPEC_COMPLETE",
        )
        rep = td.change_test_design(
            target, cid,
            write_yaml(tmp, "plan.yaml", plan_body(neutral=False)),
            test_src=TDD_SRC,
        )
        self.assertEqual(rep["status"], "BLOCKED_VERIFICATION_PLAN_INSUFFICIENT")

    def test_verify_critical_requires_merge_approval(self):
        target = make_target(TDD_REPO)
        cid = to_green(target, title="修复奖励领取逻辑", neutral=False,
                       verification=[{"id": "INTEG-001", "type": "integration",
                                      "verifies": ["AC-001-01"], "command": "python tests/test_claim.py"}])
        rep = vmod.change_verify(target, cid)
        self.assertEqual(rep["status"], "BLOCKED_HUMAN_APPROVAL_REQUIRED")

    def test_controller_approval_after_blocked_verify_reseals_and_retries(self):
        target = make_target(TDD_REPO)
        cid = to_green(target, title="修复奖励领取逻辑", neutral=False,
                       verification=[{"id": "INTEG-001", "type": "integration",
                                      "verifies": ["AC-001-01"], "command": "python tests/test_claim.py"}])
        self.assertEqual(vmod.change_verify(target, cid)["status"],
                         "BLOCKED_HUMAN_APPROVAL_REQUIRED")
        approved = amod.record_approval(target, cid, "MERGE_GATE", "APPROVED", "owner")
        self.assertEqual(approved["status"], "APPROVAL_RECORDED", approved)
        self.assertEqual(vmod.change_verify(target, cid)["status"], "VERIFY_COMPLETE")

    def test_verify_critical_with_approval_ready(self):
        target = make_target(TDD_REPO)
        cid = to_green(target, title="修复奖励领取逻辑", neutral=False,
                       verification=[{"id": "INTEG-001", "type": "integration",
                                      "verifies": ["AC-001-01"], "command": "python tests/test_claim.py"}])
        apr = amod.record_approval(target, cid, "MERGE_GATE", "APPROVED", "owner")
        self.assertEqual(apr["status"], "APPROVAL_RECORDED", apr)
        rep = vmod.change_verify(target, cid)
        self.assertEqual(rep["status"], "VERIFY_COMPLETE", rep)
        self.assertEqual(rep["overall"], "READY_WITH_WARNINGS")

    def test_approval_cannot_override_technical_failure(self):
        target = make_target(NEUTRAL_REPO)
        cid = to_green(target, verification=[{"id": "BROKEN-001", "type": "integration",
                                              "verifies": ["AC-001-01"],
                                              "command": "python tests/does_not_exist_verify.py"}])
        apr = amod.record_approval(target, cid, "MERGE_GATE", "APPROVED", "owner")
        self.assertEqual(apr["status"], "APPROVAL_RECORDED")
        rep = vmod.change_verify(target, cid)
        self.assertEqual(rep["status"], "BLOCKED_VERIFICATION_FAILED", rep)

    def test_merge_rejected_blocks_any_level(self):
        target = make_target(NEUTRAL_REPO)
        cid = to_green(target)
        amod.record_approval(target, cid, "MERGE_GATE", "REJECTED", "owner")
        rep = vmod.change_verify(target, cid)
        self.assertEqual(rep["status"], "BLOCKED_HUMAN_MERGE_REJECTED")

    def test_manual_pending_blocks(self):
        target = make_target(NEUTRAL_REPO)
        cid = to_green(target, verification=[{"id": "MANUAL-001", "type": "manual",
                                              "verifies": ["AC-001-01"]}])
        rep = vmod.change_verify(target, cid)
        self.assertEqual(rep["status"], "BLOCKED_WAITING_MANUAL")

    def test_manual_pending_not_overridden_by_approval(self):
        # MERGE_GATE 与 VERIFY_MANUAL 是不同权力；合并批准不能替代手工验证证明。
        target = make_target(NEUTRAL_REPO)
        cid = to_green(target, verification=[{"id": "MANUAL-001", "type": "manual",
                                              "verifies": ["AC-001-01"]}])
        amod.record_approval(target, cid, "MERGE_GATE", "APPROVED", "owner")
        rep = vmod.change_verify(target, cid)
        self.assertEqual(rep["status"], "BLOCKED_WAITING_MANUAL")
        ver = yaml.safe_load(open(os.path.join(target, ".aeh", "changes", cid, "verification.yaml"), encoding="utf-8"))
        self.assertEqual(ver["overall"], "BLOCKED")
        self.assertIn("blocked_reason", ver)

    def test_manual_verification_gate_is_a_human_gate(self):
        target = make_target(NEUTRAL_REPO)
        cid = to_green(target)
        self.assertEqual(
            amod.record_approval(
                target, cid, "VERIFY_MANUAL", "APPROVED", "owner", ttl_seconds=3600
            )["status"],
            "APPROVAL_RECORDED",
        )

    def test_lock_tamper_blocked(self):
        target = make_target(NEUTRAL_REPO)
        cid = to_green(target)
        with open(os.path.join(target, "tests", "test_order.py"), "a", encoding="utf-8") as f:
            f.write("# tampered\n")
        rep = vmod.change_verify(target, cid)
        self.assertEqual(rep["status"], "BLOCKED_TEST_CHANGED")

    def test_stale_context_blocked(self):
        target = make_target(NEUTRAL_REPO)
        cid = to_green(target)
        with open(os.path.join(target, "src", "mail.py"), "a", encoding="utf-8") as f:
            f.write("# external\n")
        rep = vmod.change_verify(target, cid)
        self.assertEqual(rep["status"], "BLOCKED_RUNTIME_CONTEXT_STALE")

    def test_runtime_tamper_blocked(self):
        target = make_target(NEUTRAL_REPO)
        cid = to_green(target)
        with open(os.path.join(target, ".aeh", "runtime", "core", "workflow.yaml"), "a", encoding="utf-8") as f:
            f.write("# t\n")
        rep = vmod.change_verify(target, cid)
        self.assertEqual(rep["status"], "BLOCKED_DOCTOR")

    def test_traceability_orphan_code_blocked(self):
        target = make_target(NEUTRAL_REPO)
        cid = to_green(target, targets=False)
        rep = vmod.change_verify(target, cid)
        self.assertEqual(rep["status"], "BLOCKED_TRACEABILITY_INCOMPLETE", rep)
        self.assertTrue(any("orphan code" in i for i in rep.get("issues", [])))

    def test_test_plan_tamper_blocked_before_traceability(self):
        target = make_target(NEUTRAL_REPO)
        cid = to_green(target)
        plan_path = os.path.join(target, ".aeh", "changes", cid, "test-plan.yaml")
        plan = yaml.safe_load(open(plan_path, encoding="utf-8"))
        plan["tests"][0]["verifies"] = ["AC-999-99"]
        with open(plan_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(plan, f, sort_keys=True, allow_unicode=True)
        rep = vmod.change_verify(target, cid)
        self.assertEqual(rep["status"], "BLOCKED_MACHINE_TRUTH_PROVENANCE", rep)
        self.assertIn("modified=test-plan.yaml", rep["error"])

    def test_system_fabricated_approval_blocked(self):
        target = make_target(NEUTRAL_REPO)
        cid = to_green(target)
        cdir = os.path.join(target, ".aeh", "changes", cid)
        forged = {"approvals": [{"gate": "MERGE_GATE", "status": "APPROVED",
                                 "actor": {"type": "system", "id": "agent-1"},
                                 "decided_at": "2026-08-14T12:00:00+08:00"}]}
        with open(os.path.join(cdir, "approvals.yaml"), "w", encoding="utf-8") as f:
            yaml.safe_dump(forged, f, sort_keys=True, allow_unicode=True)
        rep = vmod.change_verify(target, cid)
        self.assertEqual(rep["status"], "BLOCKED_MACHINE_TRUTH_PROVENANCE")
        self.assertIn("added=approvals.yaml", rep["error"])

    def test_approval_input_validation(self):
        target = make_target(NEUTRAL_REPO)
        cid = to_green(target)
        self.assertEqual(amod.record_approval(target, cid, "NOT_A_GATE", "APPROVED", "owner")["status"], "BLOCKED_UNKNOWN_GATE")
        self.assertEqual(amod.record_approval(target, cid, "MERGE_GATE", "APPROVED", "")["status"], "BLOCKED_MISSING_ACTOR")
        ok = amod.record_approval(target, cid, "MERGE_GATE", "APPROVED", "owner")
        self.assertEqual(ok["status"], "APPROVAL_RECORDED")
        body = yaml.safe_load(open(os.path.join(target, ".aeh", "changes", cid, "approvals.yaml"), encoding="utf-8"))
        self.assertEqual(body["approvals"][0]["actor"]["type"], "human")
        self.assertIn("decided_at", body["approvals"][0])

    def test_review_projection(self):
        target = make_target(NEUTRAL_REPO)
        cid = to_green(target)
        pre = vmod.change_review(target, cid)
        self.assertEqual(pre["status"], "BLOCKED_REVIEW_PRECONDITION")
        assert vmod.change_verify(target, cid)["status"] == "VERIFY_COMPLETE"
        rep = vmod.change_review(target, cid)
        self.assertEqual(rep["status"], "REVIEW_READY")

    def test_parallel_changes_isolated(self):
        target = make_target(NEUTRAL_REPO)
        cid1 = to_green(target)
        r2 = ch.change_new(target, "普通注释任务", suggested_level="DIRECT")
        assert vmod.change_verify(target, cid1)["status"] == "VERIFY_COMPLETE"
        self.assertFalse(os.path.exists(os.path.join(target, ".aeh", "changes", r2["change_id"], "verification.yaml")))

    def test_cli_verify_approve(self):
        target = make_target(TDD_REPO)
        cid = to_green(target, title="修复奖励领取逻辑", neutral=False,
                       verification=[{"id": "INTEG-001", "type": "integration",
                                      "verifies": ["AC-001-01"], "command": "python tests/test_claim.py"}])
        env = dict(os.environ)
        env["PYTHONPATH"] = os.path.join(ROOT, "src")
        ap = subprocess.run([sys.executable, "-m", "aeh.cli", "change", "approve", cid,
                             "--gate", "MERGE_GATE", "--status", "APPROVED", "--actor", "owner",
                             "--workdir", target], capture_output=True, text=True, env=env, cwd=ROOT)
        self.assertEqual(ap.returncode, 0, ap.stdout + ap.stderr)
        vf = subprocess.run([sys.executable, "-m", "aeh.cli", "change", "verify", cid,
                             "--workdir", target], capture_output=True, text=True, env=env, cwd=ROOT)
        self.assertEqual(vf.returncode, 0, vf.stdout + vf.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
