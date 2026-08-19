"""AEH Change Classification Engine（Phase 8 最小版）

- 分级：DIRECT / LIGHTWEIGHT / STANDARD / CRITICAL / EXPLORE。
- Hard Escalation：命中 8 个高风险域任一 → CRITICAL，机器覆盖 Agent 建议，不可降级。
- 结果保存 reasons/evidence，不只保存最终 level。
- 关键词提示来自 core/classifications.yaml（数据驱动，零公司硬编码）。
"""
import os

import yaml

from .. import paths as aeh_paths


class ClassifyError(ValueError):
    pass


def load_classification_contract(path=None):
    with open(path or aeh_paths.join("core", "classifications.yaml"), "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def detect_hits(title, contract=None):
    contract = contract or load_classification_contract()
    hints = contract.get("keyword_hints", {})
    hits = []
    low = (title or "").lower()
    for domain, keywords in hints.items():
        for kw in keywords:
            if kw.lower() in low:
                hits.append(domain)
                break
    return sorted(hits)


def classify(title, suggested_level=None, hits=None, contract=None):
    contract = contract or load_classification_contract()
    levels = contract["levels"]
    hard_domains = contract["hard_escalation"]["domains"]
    hits = sorted(set(hits or []))
    unknown = [h for h in hits if h not in hard_domains]
    if unknown:
        raise ClassifyError("unknown hard-escalation domain: " + ", ".join(unknown))
    suggested = suggested_level or "STANDARD"
    if suggested not in levels:
        raise ClassifyError("invalid suggested level: " + str(suggested))
    if hits:
        level = contract["hard_escalation"]["to"]
        reasons = ["hard_escalation: " + h for h in hits]
        escalated = True
    else:
        level = suggested
        reasons = ["suggested_level: " + suggested]
        escalated = False
    evidence = ["hits=" + ",".join(hits)] if hits else ["no_hard_domain_hits"]
    return {"level": level, "reasons": reasons, "evidence": evidence,
            "suggested_level": suggested, "escalated": escalated}
