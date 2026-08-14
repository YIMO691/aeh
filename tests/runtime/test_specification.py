"""AEH Phase 10 — Specification Runtime 测试

覆盖 spec 24 项（合理合并）。
"""
import hashlib
import os
import shutil
import sys
import tempfile
import unittest

import jsonschema
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))

from aeh.bootstrap import pipeline as bp
from aeh.runtime import change as ch
from aeh.runtime import grounding as gr
from aeh.runtime import specification as sp

FIXTURE_REPO = os.path.join(ROOT, "tests", "fixtures", "grounding-repo")


def answers_path():
    tmp = tempfile.mkdtemp(prefix="aeh-s-answers-")
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


def make_target(src=FIXTURE_REPO):
    target = tempfile.mkdtemp(prefix="aeh-s-target-")
    if src:
        shutil.copytree(src, target, dirs_exist_ok=True)
    report = bp.bootstrap(target, answers_path(), dry_run=False)
    assert report["status"] == "BOOTSTRAP_COMPLETE", report
    return target


def make_change(target, title, level="STANDARD"):
    r = ch.change_new(target, title, suggested_level=level)
    assert r["status"] == "CHANGE_CREATED", r
    g = gr.change_ground(target, r["change_id"])
    assert g["status"] == "GROUNDING_COMPLETE", g
    return r["change_id"]


def write_reqs(tmpdir, body):
    p = os.path.join(tmpdir, "reqs.yaml")
    with open(p, "w", encoding="utf-8") as f:
        yaml.safe_dump(body, f, sort_keys=True, allow_unicode=True)
    return p


def standard_reqs(supported_by=None, scope=None, unknowns=None):
    body = {
        "requirements": [
            {"behavior": "重复请求最多产生一次奖励副作用",
             "acceptance": [{"type": "invariant", "statement": "相同请求执行两次，奖励副作用最多一次"}]},
        ],
    }
    if supported_by:
        body["current_facts"] = [{"behavior": "当前领取逻辑先标记状态再发放奖励",
                                   "supported_by": supported_by,
                                   "acceptance": [{"type": "invariant", "statement": "存在当前行为证据"}]}]
    if scope:
        body["scope"] = scope
    if unknowns:
        body["unknowns"] = unknowns
    return body


def load_spec(target, cid):
    return yaml.safe_load(open(os.path.join(target, ".aeh", "changes", cid, "spec.yaml"), encoding="utf-8"))


class TestSpec(unittest.TestCase):
    def test_blocked_without_grounding_gate(self):
        target = make_target()
        r = ch.change_new(target, "修复奖励领取逻辑", suggested_level="STANDARD")
        rep = sp.build_spec(target, r["change_id"], reqs_path=write_reqs(tempfile.mkdtemp(), standard_reqs()))
        self.assertIn(rep["status"], ("BLOCKED_CHANGE_STATE", "BLOCKED_GROUNDING_GATE"))

    def test_stale_evidence_blocked(self):
        target = make_target()
        cid = make_change(target, "修复奖励领取逻辑")
        with open(os.path.join(target, "Server", "Mail", "ReceiveReward.cs"), "a", encoding="utf-8") as f:
            f.write("// changed\n")
        rep = sp.build_spec(target, cid, reqs_path=write_reqs(tempfile.mkdtemp(), standard_reqs()))
        self.assertEqual(rep["status"], "BLOCKED_STALE_EVIDENCE")

    def test_standard_spec_success(self):
        target = make_target()
        cid = make_change(target, "修复奖励领取逻辑")
        ev = yaml.safe_load(open(os.path.join(target, ".aeh", "changes", cid, "evidence.yaml"), encoding="utf-8"))
        ev_ids = [e["id"] for e in ev["evidence"]][:2]
        rep = sp.build_spec(target, cid, reqs_path=write_reqs(tempfile.mkdtemp(), standard_reqs(supported_by=ev_ids)))
        self.assertEqual(rep["status"], "SPEC_COMPLETE", rep)
        change = ch.load_change(target, cid)
        self.assertEqual(change["gates"].get("spec"), "PASS")
        self.assertEqual(change["state"]["current"], "SPEC")
        spec = load_spec(target, cid)
        schema = yaml.safe_load(open(os.path.join(ROOT, "schemas", "spec.schema.json"), encoding="utf-8"))
        jsonschema.validate(spec, schema)
        ids = [r["id"] for r in spec["requirements"]]
        self.assertEqual(len(ids), len(set(ids)))
        for r in spec["requirements"]:
            self.assertGreaterEqual(len(r["acceptance"]), 1)
            aids = [a["id"] for a in r["acceptance"]]
            self.assertEqual(len(aids), len(set(aids)))

    def test_evidence_derived_needs_support(self):
        target = make_target()
        cid = make_change(target, "修复奖励领取逻辑")
        body = {"current_facts": [{"behavior": "当前行为X", "acceptance": [{"type": "automated", "statement": "s"}]}]}
        rep = sp.build_spec(target, cid, reqs_path=write_reqs(tempfile.mkdtemp(), body))
        self.assertEqual(rep["status"], "BLOCKED_UNSUPPORTED_REQUIREMENT")

    def test_invalid_ev_reference_blocked(self):
        target = make_target()
        cid = make_change(target, "修复奖励领取逻辑")
        rep = sp.build_spec(target, cid, reqs_path=write_reqs(tempfile.mkdtemp(), standard_reqs(supported_by=["EV-999"])))
        self.assertEqual(rep["status"], "BLOCKED_INVALID_EVIDENCE_REFERENCE")

    def test_user_requirement_without_ev_ok(self):
        target = make_target()
        cid = make_change(target, "修复奖励领取逻辑")
        rep = sp.build_spec(target, cid, reqs_path=write_reqs(tempfile.mkdtemp(), standard_reqs()))
        self.assertEqual(rep["status"], "SPEC_COMPLETE", rep)

    def test_current_vs_desired_not_confused(self):
        target = make_target()
        cid = make_change(target, "修复奖励领取逻辑")
        ev = yaml.safe_load(open(os.path.join(target, ".aeh", "changes", cid, "evidence.yaml"), encoding="utf-8"))
        ev_id = ev["evidence"][0]["id"]
        rep = sp.build_spec(target, cid, reqs_path=write_reqs(tempfile.mkdtemp(), standard_reqs(supported_by=[ev_id])))
        self.assertEqual(rep["status"], "SPEC_COMPLETE")
        spec = load_spec(target, cid)
        cur = [r for r in spec["requirements"] if r["kind"] == "CURRENT"]
        des = [r for r in spec["requirements"] if r["kind"] == "DESIRED"]
        self.assertEqual(len(cur), 1)
        self.assertEqual(len(des), 1)
        self.assertEqual(cur[0]["source"]["type"], "EVIDENCE_DERIVED")
        self.assertEqual(des[0]["source"]["type"], "USER_REQUIREMENT")
        self.assertNotIn("重复请求", cur[0]["behavior"])

    def test_policy_constraint_ref_only(self):
        target = make_target()
        cid = make_change(target, "修复奖励领取逻辑")
        body = standard_reqs()
        body["constraints"] = [{"behavior": "禁止直连生产数据库", "refs": ["ORG-SEC-001"],
                                 "acceptance": [{"type": "invariant", "statement": "合规审查通过"}]}]
        rep = sp.build_spec(target, cid, reqs_path=write_reqs(tempfile.mkdtemp(), body))
        self.assertEqual(rep["status"], "SPEC_COMPLETE", rep)
        raw = open(os.path.join(target, ".aeh", "changes", cid, "spec.yaml"), encoding="utf-8").read()
        self.assertNotIn("SECRET-BODY", raw)
        self.assertIn("ORG-SEC-001", raw)

    def test_critical_requires_invariant_or_failure(self):
        target = make_target()
        cid = make_change(target, "修复重复领取奖励")
        body = {"requirements": [{"behavior": "X", "acceptance": [{"type": "automated", "statement": "s"}]}]}
        rep = sp.build_spec(target, cid, reqs_path=write_reqs(tempfile.mkdtemp(), body))
        self.assertEqual(rep["status"], "SPEC_INCOMPLETE")
        self.assertIn("invariant", rep["missing"][0])

    def test_critical_unknown_blocks(self):
        target = make_target()
        cid = make_change(target, "修复重复领取奖励")
        body = standard_reqs(unknowns=[{"field": "经济回滚语义", "reason": "未确认", "critical": True}])
        rep = sp.build_spec(target, cid, reqs_path=write_reqs(tempfile.mkdtemp(), body))
        self.assertEqual(rep["status"], "SPEC_INCOMPLETE")

    def test_out_of_scope_blocked(self):
        target = make_target()
        cid = make_change(target, "修复奖励领取逻辑")
        body = {"requirements": [{"behavior": "越界需求", "scope_tags": ["billing"],
                                   "acceptance": [{"type": "manual", "statement": "s"}]}],
                "scope": {"in": ["reward"], "out": ["billing"]}}
        rep = sp.build_spec(target, cid, reqs_path=write_reqs(tempfile.mkdtemp(), body))
        self.assertEqual(rep["status"], "UNSCOPED_REQUIREMENT")

    def test_deterministic_and_stable_ids(self):
        target = make_target()
        cid = make_change(target, "修复奖励领取逻辑")
        ev = yaml.safe_load(open(os.path.join(target, ".aeh", "changes", cid, "evidence.yaml"), encoding="utf-8"))
        ev_id = ev["evidence"][0]["id"]
        body = standard_reqs(supported_by=[ev_id])
        r1 = sp.build_spec(target, cid, reqs_path=write_reqs(tempfile.mkdtemp(), body))
        self.assertEqual(r1["status"], "SPEC_COMPLETE")
        s1 = load_spec(target, cid)
        r2 = sp.build_spec(target, cid, reqs_path=write_reqs(tempfile.mkdtemp(), body))
        self.assertEqual(r2["status"], "SPEC_COMPLETE")
        s2 = load_spec(target, cid)
        ids1 = [r["id"] for r in s1["requirements"]]
        ids2 = [r["id"] for r in s2["requirements"]]
        self.assertEqual(ids1, ids2)
        sem1 = {k: v for k, v in s1.items() if k != "generated_at"}
        sem2 = {k: v for k, v in s2.items() if k != "generated_at"}
        self.assertEqual(sem1, sem2)

    def test_gate_pass_allows_test_design(self):
        target = make_target()
        cid = make_change(target, "修复奖励领取逻辑")
        rep = sp.build_spec(target, cid, reqs_path=write_reqs(tempfile.mkdtemp(), standard_reqs()))
        self.assertEqual(rep["status"], "SPEC_COMPLETE")
        tr = ch.change_transition(target, cid, "TEST_DESIGN")
        self.assertEqual(tr["status"], "TRANSITION_OK")

    def test_gate_not_pass_rejects_test_design(self):
        target = make_target()
        cid = make_change(target, "修复奖励领取逻辑")
        rep = sp.build_spec(target, cid, reqs_path=write_reqs(tempfile.mkdtemp(), standard_reqs()))
        self.assertEqual(rep["status"], "SPEC_COMPLETE")
        change = ch.load_change(target, cid)
        change["gates"].pop("spec", None)
        ch.save_change(target, change)
        tr = ch.change_transition(target, cid, "TEST_DESIGN")
        self.assertEqual(tr["status"], "BLOCKED_GATE_UNSATISFIED")

    def test_parallel_specs_isolated(self):
        target = make_target()
        cid1 = make_change(target, "修复奖励领取逻辑")
        cid2 = make_change(target, "奖励领取流程优化")
        rep = sp.build_spec(target, cid1, reqs_path=write_reqs(tempfile.mkdtemp(), standard_reqs()))
        self.assertEqual(rep["status"], "SPEC_COMPLETE")
        self.assertFalse(os.path.exists(os.path.join(target, ".aeh", "changes", cid2, "spec.yaml")))

    def test_writes_only_change_dir(self):
        target = make_target()
        cid = make_change(target, "修复奖励领取逻辑")
        before = {}
        for dp, _, fns in os.walk(target):
            for fn in fns:
                p = os.path.join(dp, fn)
                rel = os.path.relpath(p, target)
                if not rel.startswith(os.path.join(".aeh", "changes", cid)):
                    with open(p, "rb") as fh:
                        before[rel] = hashlib.sha256(fh.read()).hexdigest()
        sp.build_spec(target, cid, reqs_path=write_reqs(tempfile.mkdtemp(), standard_reqs()))
        for rel, h in before.items():
            p = os.path.join(target, rel)
            if os.path.isfile(p):
                with open(p, "rb") as fh:
                    self.assertEqual(hashlib.sha256(fh.read()).hexdigest(), h, rel)


if __name__ == "__main__":
    unittest.main(verbosity=2)