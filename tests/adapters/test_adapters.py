"""AEH Phase 5 — Agent Adapters 测试

覆盖 spec 16 项：双平台渲染、语义等价、BLOCKED 拒绝、deny 不放松、
required 不降级、unsupported 记录、私有零泄漏、薄入口、merge 保留/幂等/malformed 阻断、
确定性、时间无关、输入不被修改。
"""
import copy
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))

from aeh.adapters import render as ar  # noqa: E402

PY_DISC_ROOT = os.path.join(ROOT, "tests", "fixtures", "repos", "minimal-py")


def base_profile(**overrides):
    p = {
        "profile_version": "1.0",
        "project": {"name": "demo", "languages": []},
        "workflow": {"default_level": "STANDARD"},
        "permissions": {
            "modify_source": {"value": "allow", "source": {"type": "user_answer", "ref": "q-modify-source"}, "confidence": "USER_CONFIRMED"},
            "git_commit": {"value": "ask", "source": {"type": "user_answer", "ref": "q-git-commit"}, "confidence": "USER_CONFIRMED"},
            "git_push": {"value": "deny", "source": {"type": "user_answer", "ref": "q-git-push"}, "confidence": "USER_CONFIRMED"},
            "shell": {"value": "ask", "source": {"type": "user_answer", "ref": "q-shell"}, "confidence": "USER_CONFIRMED"},
            "web_access": {"value": "deny", "source": {"type": "user_answer", "ref": "q-web"}, "confidence": "USER_CONFIRMED"},
        },
        "review": {"human_required_for": [{"value": "critical", "source": {"type": "user_answer", "ref": "q-human-review"}, "confidence": "USER_CONFIRMED"}]},
        "status": "COMPILED",
        "conflicts": [],
    }
    p.update(overrides)
    return p


def base_workflow():
    return {
        "workflow_version": "1",
        "default_level": "STANDARD",
        "source": {"core_revision": "core.workflow:v1", "profile_ref": ".aeh/profile.yaml"},
        "levels": {"STANDARD": {"phases": ["GROUND", "SPEC", "RED", "LOCK_TEST", "GREEN"]}},
    }


class TestRender(unittest.TestCase):
    def test_codex_render_pass(self):
        out = ar.render("codex", base_profile(), base_workflow())
        self.assertEqual(out["status"], "RENDERED")
        self.assertIn(".aeh/profile.yaml", out["managed_section"])
        self.assertIn("- git_push: deny", out["managed_section"])
        codex_map = {m["field"]: m for m in out["permission_mapping"]}
        self.assertIn("DENY", codex_map["permissions.git_push"]["expression"]["instruction"])
        self.assertGreater(len(out["permission_mapping"]), 0)

    def test_claude_render_pass(self):
        out = ar.render("claude", base_profile(), base_workflow())
        self.assertEqual(out["status"], "RENDERED")
        self.assertIn(".aeh/effective-workflow.yaml", out["managed_section"])
        mapping = {m["field"]: m for m in out["permission_mapping"]}
        self.assertIn("Bash(git push:*)", mapping["permissions.git_push"]["expression"]["deny"])

    def test_semantic_equivalence_across_adapters(self):
        p = base_profile()
        codex_out = ar.render("codex", p, base_workflow())
        claude_out = ar.render("claude", p, base_workflow())
        self.assertEqual(codex_out["semantics"], claude_out["semantics"])
        for key, value in codex_out["semantics"]["permissions"].items():
            self.assertIn(str(value), claude_out["managed_section"])

    def test_blocked_profile_rejected(self):
        p = base_profile(status="BLOCKED")
        for agent in ("codex", "claude"):
            with self.assertRaises(ar.AdapterError) as ctx:
                ar.render(agent, p, base_workflow())
            self.assertIn("BLOCKED_PROFILE_CONFLICT", str(ctx.exception))

    def test_push_deny_not_relaxed(self):
        for agent in ("codex", "claude"):
            out = ar.render(agent, base_profile(), base_workflow())
            mapping = {m["field"]: m for m in out["permission_mapping"]}
            self.assertEqual(mapping["permissions.git_push"]["value"], "deny")
            text = json.dumps(out)
            self.assertNotIn('"value": "ask", "field": "permissions.git_push"', text.replace(" ", ""))
        claude_out = ar.render("claude", base_profile(), base_workflow())
        c_map = {m["field"]: m for m in claude_out["permission_mapping"]}
        self.assertIn("Bash(git push:*)", c_map["permissions.git_push"]["expression"]["deny"])
        self.assertNotIn("Bash(git push:*)", c_map["permissions.git_push"]["expression"]["allow"])

    def test_human_review_required_not_degraded(self):
        for agent in ("codex", "claude"):
            out = ar.render(agent, base_profile(), base_workflow())
            self.assertIn("review.human_required_for: critical", out["managed_section"])
            self.assertNotIn("optional", out["managed_section"].lower())

    def test_unsupported_capability_recorded(self):
        codex_out = ar.render("codex", base_profile(), base_workflow())
        codex_unsup = {(u["field"], u["status"]) for u in codex_out["diagnostics"]["unsupported_capabilities"]}
        self.assertIn(("permissions.git_push", "GUIDANCE_ONLY"), codex_unsup)
        claude_out = ar.render("claude", base_profile(), base_workflow())
        claude_unsup = {(u["field"], u["status"]) for u in claude_out["diagnostics"]["unsupported_capabilities"]}
        self.assertIn(("permissions.web_access", "GUIDANCE_ONLY"), claude_unsup)
        self.assertIn(("review.human_required_for", "GUIDANCE_ONLY"), claude_unsup)

    def test_private_policy_zero_leak(self):
        p = base_profile()
        p["sources"] = {"private_note": "SECRET-TOKEN-123", "internal_path": "C:\SECRET-SERVER"}
        for agent in ("codex", "claude"):
            out = ar.render(agent, p, base_workflow())
            serialized = json.dumps(out, default=str)
            self.assertNotIn("SECRET-TOKEN-123", serialized)
            self.assertNotIn("SECRET-SERVER", serialized)

    def test_managed_section_is_thin(self):
        for agent in ("codex", "claude"):
            out = ar.render(agent, base_profile(), base_workflow())
            section = out["managed_section"]
            self.assertLess(len(section), 3000)
            for banned in ["INVALID_RED", "evidence_kinds", "BLOCKED_POLICY_CONFLICT", "transitions:"]:
                self.assertNotIn(banned, section)


class TestManagedMerge(unittest.TestCase):
    def setUp(self):
        self.generated = "GENERATED-SECTION-BODY"
        self.user_text = "# My project rules\n\nUser rule one.\nUser rule two.\n"

    def test_user_content_preserved(self):
        merged = ar.merge_managed_section(self.user_text, self.generated)
        self.assertIn("User rule one.", merged)
        self.assertIn("User rule two.", merged)
        self.assertIn(self.generated, merged)
        self.assertEqual(merged.count("AEH:BEGIN MANAGED"), 1)
        self.assertEqual(merged.count("AEH:END MANAGED"), 1)

    def test_second_merge_idempotent(self):
        once = ar.merge_managed_section(self.user_text, self.generated)
        twice = ar.merge_managed_section(once, self.generated)
        self.assertEqual(once, twice)

    def test_malformed_markers_blocked(self):
        bads = [
            "# x\n<!-- AEH:BEGIN MANAGED -->\nno end\n",
            "# x\n<!-- AEH:END MANAGED -->\nno begin\n",
            "# x\n<!-- AEH:END MANAGED -->\n<!-- AEH:BEGIN MANAGED -->\n",
            "# x\n<!-- AEH:BEGIN MANAGED -->\n<!-- AEH:BEGIN MANAGED -->\n",
        ]
        for bad in bads:
            with self.assertRaises(ar.AdapterError):
                ar.merge_managed_section(bad, self.generated)


class TestDeterminism(unittest.TestCase):
    def test_deterministic_output(self):
        for agent in ("codex", "claude"):
            a = ar.render(agent, base_profile(), base_workflow())
            b = ar.render(agent, base_profile(), base_workflow())
            self.assertEqual(json.dumps(a, sort_keys=True, default=str), json.dumps(b, sort_keys=True, default=str))

    def test_timestamps_irrelevant(self):
        p1 = base_profile()
        p1["scanned_at"] = "2026-01-01T00:00:00+00:00"
        p1["answered_at"] = "2026-01-01T00:00:00+00:00"
        p2 = base_profile()
        p2["scanned_at"] = "2030-01-01T00:00:00+00:00"
        p2["answered_at"] = "2030-01-01T00:00:00+00:00"
        for agent in ("codex", "claude"):
            o1 = ar.render(agent, p1, base_workflow())
            o2 = ar.render(agent, p2, base_workflow())
            self.assertEqual(json.dumps(o1, sort_keys=True, default=str), json.dumps(o2, sort_keys=True, default=str))

    def test_inputs_not_modified(self):
        for agent in ("codex", "claude"):
            p = base_profile()
            wf = base_workflow()
            p_before = copy.deepcopy(p)
            wf_before = copy.deepcopy(wf)
            ar.render(agent, p, wf)
            self.assertEqual(p, p_before)
            self.assertEqual(wf, wf_before)


    def test_no_unclosed_template_file_handles(self):
        """release-fix 004：模板读取必须关闭句柄（dogfood 发现并修复的真实 bug）。"""
        import gc
        import warnings as wmod
        from aeh.adapters import render as rmod
        with wmod.catch_warnings(record=True) as caught:
            wmod.simplefilter("always", ResourceWarning)
            rmod.render("codex", {}, {}, adapter_root=os.path.join(ROOT, "adapters", "codex"))
            rmod.render("claude", {}, {}, adapter_root=os.path.join(ROOT, "adapters", "claude"))
        gc.collect()
        leaked = [w for w in caught if issubclass(w.category, ResourceWarning) and "template" in str(w.message)]
        self.assertEqual(leaked, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)