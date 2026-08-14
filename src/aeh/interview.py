"""AEH Progressive Interview — 最小机制（Phase 3 Minimal）

规则数据驱动：问题全部来自 bootstrap/interview/*.yaml，本模块不硬编码任何问题逻辑。
过滤顺序（spec 冻结）：
  1. Discovery 已 DETECTED 的对应事实 → SKIP（discovery_detected）
  2. 非必要问题（required=false）→ SKIP（optional）
  3. 已有有效回答（且未被 reset）→ SKIP（already_answered）
  4. 其余（required=true 且无可靠答案）→ ASK（required_unknown）

语义约束：
- Discovery 的 scanned_at 属 non-semantic provenance：plan() 只读 facts/unknowns，时间变化
  不会改变决策，也不会导致重复询问。
- 只读、无网络；问题规则经 Schema 校验后加载，非法规则拒绝。

不实现：Conflict Resolver / Profile Compiler / Adapter / 完整 Bootstrap / 多轮决策树。
"""
import hashlib
import os
from datetime import datetime, timezone

import jsonschema
import yaml

CONTRACT = "bootstrap.interview"
CONTRACT_VERSION = 1
QUESTION_TYPES = ["FACT", "PREFERENCE", "POLICY", "PERMISSION"]
SCOPES = ["core", "developer", "team", "organization", "ai_permissions"]
SOURCES = ["user_answer", "repository_fact", "default_applied", "organization_policy"]

DECISION_ASK = "ASK"
DECISION_SKIP = "SKIP"


class InterviewError(ValueError):
    pass


def _default_schema_path():
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "schemas", "interview.schema.json")


def load_questions(rules_root, schema_path=None):
    """加载并校验全部问题规则；非法规则拒绝（InterviewError）。返回 (questions, digest)。"""
    if not os.path.isdir(rules_root):
        raise InterviewError("interview rules root does not exist: " + rules_root)
    schema_path = schema_path or _default_schema_path()
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = yaml.safe_load(f)
    questions = []
    digest_parts = []
    for fname in sorted(os.listdir(rules_root)):
        if not fname.endswith(".yaml"):
            continue
        path = os.path.join(rules_root, fname)
        with open(path, "rb") as f:
            raw = f.read()
        digest_parts.append(fname + "\0" + hashlib.sha256(raw).hexdigest())
        try:
            rule = yaml.safe_load(raw)
        except yaml.YAMLError as e:
            raise InterviewError("invalid interview rule yaml " + fname + ": " + str(e))
        try:
            jsonschema.validate(rule, schema)
        except jsonschema.ValidationError as e:
            raise InterviewError("invalid interview rule " + fname + ": " + e.message)
        for q in rule.get("questions", []):
            q = dict(q)
            q["scope"] = rule["scope"]
            questions.append(q)
    digest = hashlib.sha256(("\n".join(sorted(digest_parts))).encode("utf-8")).hexdigest()
    return questions, digest


def _fact_map(discovery):
    return {(f["domain"], f["field"]): f for f in (discovery or {}).get("facts", [])}


def _discovery_detected(question, fact_map):
    conds = ((question.get("ask_when") or {}).get("discovery_detected")) or []
    if not conds:
        return False
    for c in conds:
        fact = fact_map.get((c["domain"], c["field"]))
        if fact is None or fact.get("confidence") != "DETECTED":
            return False
        if c.get("value") is not None and fact.get("value") != c["value"]:
            return False
    return True


def plan(questions, discovery, answers):
    """确定性过滤：返回决策列表。不读 scanned_at，不含时间戳。"""
    fact_map = _fact_map(discovery)
    answered = set((answers or {}).get("answers", {}).keys()) - set((answers or {}).get("reset", []))
    decisions = []
    for q in questions:
        base = {
            "question_id": q["question_id"],
            "scope": q.get("scope"),
            "type": q["type"],
            "field": q["field"],
            "question": q["question"],
        }
        if _discovery_detected(q, fact_map):
            decisions.append({**base, "decision": DECISION_SKIP, "reason": "discovery_detected"})
        elif q.get("required") is False:
            decisions.append({**base, "decision": DECISION_SKIP, "reason": "optional"})
        elif q["question_id"] in answered:
            decisions.append({**base, "decision": DECISION_SKIP, "reason": "already_answered"})
        else:
            decisions.append({**base, "decision": DECISION_ASK, "reason": "required_unknown"})
    return decisions


def record_answer(answers, question, answer, source="user_answer", confidence=None, answered_at=None):
    """不可变记录：返回新 answers 结构（含 answered_at 时间戳）。"""
    if source not in SOURCES:
        raise InterviewError("unknown answer source: " + source)
    new_answers = {"contract": "bootstrap.interview.answers",
                   "version": CONTRACT_VERSION,
                   "answers": dict((answers or {}).get("answers", {})),
                   "reset": list((answers or {}).get("reset", []))}
    qid = question["question_id"]
    new_answers["answers"][qid] = {
        "question_id": qid,
        "answer": answer,
        "type": question["type"],
        "source": source,
        "answered_at": answered_at or datetime.now(timezone.utc).isoformat(),
        "scope": question.get("scope"),
    }
    if confidence is not None:
        new_answers["answers"][qid]["confidence"] = confidence
    if qid in new_answers["reset"]:
        new_answers["reset"].remove(qid)
    return new_answers


def reset_answer(answers, question_id):
    """显式要求重新回答某问题：加入 reset 列表（幂等）。"""
    new_answers = {"contract": "bootstrap.interview.answers",
                   "version": CONTRACT_VERSION,
                   "answers": dict((answers or {}).get("answers", {})),
                   "reset": list((answers or {}).get("reset", []))}
    if question_id not in new_answers["reset"]:
        new_answers["reset"].append(question_id)
    return new_answers
