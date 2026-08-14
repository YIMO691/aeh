"""AEH Phase 9 — Grounding & Evidence Runtime 测试

覆盖 spec 20 项。
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
from aeh.doctor import doctor as doc
from aeh.runtime import change as ch
from aeh.runtime import grounding as gr

FIXTURE_REPO = os.path.join(ROOT, "tests", "fixtures", "grounding-repo")


def answers_path():
    tmp = tempfile.mkdtemp(prefix="aeh-g-answers-")
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


def make_target(src=None):
    target = tempfile.mkdtemp(prefix="aeh-g-target-")
    if src:
        shutil.copytree(src, target, dirs_exist_ok=True)
    # mkdtemp 已创建目录；空仓库分支无需再建
    report = bp.bootstrap(target, answers_path(), dry_run=False)
    assert report["status"] == "BOOTSTRAP_COMPLETE", report
    return target


def snapshot_excluding(root, exclude_rel):
    out = {}
    for dp, _, fns in os.walk(root):
        for fn in fns:
            p = os.path.join(dp, fn)
            rel = os.path.relpath(p, root)
            if rel.startswith(exclude_rel):
                continue
            with open(p, "rb") as fh:
                out[rel] = hashlib.sha256(fh.read()).hexdigest()
    return out


class TestGrounding(unittest.TestCase):
    def test_standard_grounding_success(self):
        target = make_target(FIXTURE_REPO)
        r = ch.change_new(target, "修复奖励领取逻辑", suggested_level="STANDARD")
        self.assertEqual(r["status"], "CHANGE_CREATED")
        cid = r["change_id"]
        rep = gr.change_ground(target, cid)
        self.assertEqual(rep["status"], "GROUNDING_COMPLETE", rep)
        self.assertTrue(os.path.isfile(os.path.join(target, ".aeh", "changes", cid, "evidence.yaml")))
        self.assertTrue(os.path.isfile(os.path.join(target, ".aeh", "changes", cid, "evidence.md")))
        change = ch.load_change(target, cid)
        self.assertEqual(change["gates"].get("grounding"), "PASS")
        self.assertEqual(change["state"]["current"], "GROUND")

    def test_after_grounding_can_enter_spec(self):
        target = make_target(FIXTURE_REPO)
        r = ch.change_new(target, "修复奖励领取逻辑", suggested_level="STANDARD")
        rep = gr.change_ground(target, r["change_id"])
        self.assertEqual(rep["status"], "GROUNDING_COMPLETE")
        tr = ch.change_transition(target, r["change_id"], "SPEC")
        self.assertEqual(tr["status"], "TRANSITION_OK")

    def test_critical_requires_stronger_evidence(self):
        # CRITICAL 需要 CALL_PATH + 风险域证据 + limitations；用无关联命中的小仓库
        tmp_src = tempfile.mkdtemp(prefix="aeh-g-poor-")
        with open(os.path.join(tmp_src, "only.txt"), "w", encoding="utf-8") as f:
            f.write("结算逻辑说明文档\n")
        target = make_target(tmp_src)
        r = ch.change_new(target, "结算逻辑修改", suggested_level="CRITICAL")
        rep = gr.change_ground(target, r["change_id"])
        self.assertEqual(rep["status"], "GROUNDING_INCOMPLETE", rep)
        self.assertIn("call_path", rep["missing"])

    def test_grounding_read_only(self):
        target = make_target(FIXTURE_REPO)
        r = ch.change_new(target, "修复奖励领取逻辑", suggested_level="STANDARD")
        before = snapshot_excluding(target, ".aeh")
        gr.change_ground(target, r["change_id"])
        after = snapshot_excluding(target, ".aeh")
        self.assertEqual(before, after)

    def test_writes_only_inside_change_dir(self):
        target = make_target(FIXTURE_REPO)
        r = ch.change_new(target, "修复奖励领取逻辑", suggested_level="STANDARD")
        cid = r["change_id"]
        before = snapshot_excluding(target, os.path.join(".aeh", "changes", cid))
        gr.change_ground(target, cid)
        after = snapshot_excluding(target, os.path.join(".aeh", "changes", cid))
        self.assertEqual(before, after)

    def test_evidence_schema_pass(self):
        target = make_target(FIXTURE_REPO)
        r = ch.change_new(target, "修复奖励领取逻辑", suggested_level="STANDARD")
        gr.change_ground(target, r["change_id"])
        index = yaml.safe_load(open(os.path.join(target, ".aeh", "changes", r["change_id"], "evidence.yaml"), encoding="utf-8"))
        schema = yaml.safe_load(open(os.path.join(ROOT, "schemas", "evidence-index.schema.json"), encoding="utf-8"))
        jsonschema.validate(index, schema)

    def test_ev_ids_unique_and_hashed(self):
        target = make_target(FIXTURE_REPO)
        r = ch.change_new(target, "修复奖励领取逻辑", suggested_level="STANDARD")
        gr.change_ground(target, r["change_id"])
        index = yaml.safe_load(open(os.path.join(target, ".aeh", "changes", r["change_id"], "evidence.yaml"), encoding="utf-8"))
        ids = [e["id"] for e in index["evidence"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIn("base_commit", index["repository"])
        self.assertIn("dirty", index["repository"])
        hashed = [e for e in index["evidence"] if e.get("source_state", {}).get("file_hash")]
        self.assertGreater(len(hashed), 0)

    def test_no_sensitive_content(self):
        tmp_src = tempfile.mkdtemp(prefix="aeh-g-secret-")
        with open(os.path.join(tmp_src, "code.py"), "w", encoding="utf-8") as f:
            f.write("# 奖励逻辑 SECRET-TOKEN-123\ndef grant(): pass\n")
        target = make_target(tmp_src)
        r = ch.change_new(target, "奖励逻辑", suggested_level="STANDARD")
        gr.change_ground(target, r["change_id"])
        raw = open(os.path.join(target, ".aeh", "changes", r["change_id"], "evidence.yaml"), encoding="utf-8").read()
        self.assertNotIn("SECRET-TOKEN-123", raw)

    def test_test_found_with_evidence(self):
        target = make_target(FIXTURE_REPO)
        r = ch.change_new(target, "修复奖励领取逻辑", suggested_level="STANDARD")
        gr.change_ground(target, r["change_id"])
        index = yaml.safe_load(open(os.path.join(target, ".aeh", "changes", r["change_id"], "evidence.yaml"), encoding="utf-8"))
        tests = [e for e in index["evidence"] if e["type"] == "TEST"]
        self.assertGreater(len(tests), 0)
        self.assertTrue(all(t["test_result"] == "FOUND" for t in tests))

    def test_not_found_has_negative_search(self):
        tmp_src = tempfile.mkdtemp(prefix="aeh-g-notest-")
        with open(os.path.join(tmp_src, "app.txt"), "w", encoding="utf-8") as f:
            f.write("奖励逻辑说明\n")
        target = make_target(tmp_src)
        r = ch.change_new(target, "奖励逻辑", suggested_level="STANDARD")
        rep = gr.change_ground(target, r["change_id"])
        index = yaml.safe_load(open(os.path.join(target, ".aeh", "changes", r["change_id"], "evidence.yaml"), encoding="utf-8"))
        neg = [e for e in index["evidence"] if e["type"] == "NEGATIVE_SEARCH"]
        self.assertGreater(len(neg), 0)
        self.assertEqual(neg[0]["test_result"], "NOT_FOUND")

    def test_resource_limit_records_limitation(self):
        tmp_src = tempfile.mkdtemp(prefix="aeh-g-limit-")
        for i in range(20):
            with open(os.path.join(tmp_src, "f%d.txt" % i), "w", encoding="utf-8") as f:
                f.write("奖励逻辑 %d\n" % i)
        target = make_target(tmp_src)
        r = ch.change_new(target, "奖励逻辑", suggested_level="STANDARD")
        rep = gr.change_ground(target, r["change_id"], limits={"max_walk_files": 5})
        index = yaml.safe_load(open(os.path.join(target, ".aeh", "changes", r["change_id"], "evidence.yaml"), encoding="utf-8"))
        self.assertTrue(any(u["reason"] == "LIMITED_BY_RESOURCE_BOUND" for u in index.get("unknowns", [])))

    def test_insufficient_evidence_gate_not_pass(self):
        target = make_target(None)
        r = ch.change_new(target, "完全无关任务", suggested_level="LIGHTWEIGHT")
        rep = gr.change_ground(target, r["change_id"])
        self.assertEqual(rep["status"], "GROUNDING_INCOMPLETE")
        change = ch.load_change(target, r["change_id"])
        self.assertNotEqual(change["gates"].get("grounding"), "PASS")
        tr = ch.change_transition(target, r["change_id"], "SPEC")
        self.assertNotEqual(tr["status"], "TRANSITION_OK")

    def test_stale_detection(self):
        target = make_target(FIXTURE_REPO)
        r = ch.change_new(target, "修复奖励领取逻辑", suggested_level="STANDARD")
        gr.change_ground(target, r["change_id"])
        self.assertEqual(gr.check_stale(target, r["change_id"])["stale"], [])
        with open(os.path.join(target, "Server", "Mail", "ReceiveReward.cs"), "a", encoding="utf-8") as f:
            f.write("// changed\n")
        stale = gr.check_stale(target, r["change_id"])["stale"]
        self.assertGreater(len(stale), 0)

    def test_classification_escalate_by_repo_evidence(self):
        # 标题无风险词（STANDARD），但仓库含 database/transaction → persistence 域 grounding → 升级
        target = make_target(FIXTURE_REPO)
        r = ch.change_new(target, "结算界面调整", suggested_level="STANDARD")
        self.assertEqual(r["classification"]["level"], "STANDARD")
        rep = gr.change_ground(target, r["change_id"])
        change = ch.load_change(target, r["change_id"])
        self.assertEqual(change["classification"]["level"], "CRITICAL", rep)
        self.assertTrue(change["classification"].get("escalated"))

    def test_no_automatic_downgrade(self):
        # 关键词已升级 CRITICAL；grounding 未找到更多证据 → 保持 CRITICAL
        target = make_target(FIXTURE_REPO)
        r = ch.change_new(target, "修复重复领取奖励", suggested_level="LIGHTWEIGHT")
        self.assertEqual(r["classification"]["level"], "CRITICAL")
        rep = gr.change_ground(target, r["change_id"])
        change = ch.load_change(target, r["change_id"])
        self.assertEqual(change["classification"]["level"], "CRITICAL", rep)

    def test_parallel_changes_isolated(self):
        target = make_target(FIXTURE_REPO)
        r1 = ch.change_new(target, "修复奖励领取逻辑", suggested_level="STANDARD")
        r2 = ch.change_new(target, "结算界面调整", suggested_level="STANDARD")
        gr.change_ground(target, r1["change_id"])
        ev1 = yaml.safe_load(open(os.path.join(target, ".aeh", "changes", r1["change_id"], "evidence.yaml"), encoding="utf-8"))
        self.assertEqual(ev1["change_id"], r1["change_id"])
        self.assertFalse(os.path.exists(os.path.join(target, ".aeh", "changes", r2["change_id"], "evidence.yaml")))

    def test_integrity_blocked_no_grounding(self):
        target = make_target(FIXTURE_REPO)
        r = ch.change_new(target, "修复奖励领取逻辑", suggested_level="STANDARD")
        with open(os.path.join(target, ".aeh", "runtime", "core", "workflow.yaml"), "a", encoding="utf-8") as f:
            f.write("# tampered\n")
        rep = gr.change_ground(target, r["change_id"])
        self.assertEqual(rep["status"], "BLOCKED_DOCTOR")
        self.assertFalse(os.path.exists(os.path.join(target, ".aeh", "changes", r["change_id"], "evidence.yaml")))


    def test_test_evidence_rel_path_root_relative_no_stale(self):
        """release-fix 003：TEST 证据 rel_path 相对仓库根，ground 后立即 spec 不误判 stale。"""
        target = make_target(FIXTURE_REPO)
        r = ch.change_new(target, "修复奖励领取逻辑", suggested_level="STANDARD")
        rep = gr.change_ground(target, r["change_id"])
        self.assertEqual(rep["status"], "GROUNDING_COMPLETE", rep)
        stale = gr.check_stale(target, r["change_id"])["stale"]
        index = yaml.safe_load(open(os.path.join(target, ".aeh", "changes", r["change_id"], "evidence.yaml"), encoding="utf-8"))
        test_evs = [e for e in index["evidence"] if e["type"] == "TEST"]
        self.assertTrue(test_evs)
        for e in test_evs:
            rel = (e.get("source_state") or {}).get("rel_path", "")
            self.assertTrue(os.path.isfile(os.path.join(target, rel)), rel)
        self.assertEqual(stale, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)