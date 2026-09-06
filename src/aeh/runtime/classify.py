"""AEH Change Classification Engine.

- 分级：DIRECT / LIGHTWEIGHT / STANDARD / CRITICAL / EXPLORE。
- 无 scoped facts 的旧调用保持 fail-safe：关键词命中高风险域即升级。
- 有 scoped facts 时，关键词只是提示；显式敏感影响或不可逆事实才硬升级。
- 结果保存 reasons/evidence，不只保存最终 level。
- 关键词提示来自 core/classifications.yaml（数据驱动，零公司硬编码）。
"""
import os

import yaml

from .. import paths as aeh_paths


class ClassifyError(ValueError):
    pass


LEVEL_RANK = {
    "EXPLORE": 0,
    "DIRECT": 1,
    "LIGHTWEIGHT": 2,
    "STANDARD": 3,
    "CRITICAL": 4,
}


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


def load_facts(path):
    if not path or not os.path.isfile(path):
        raise ClassifyError("classification facts file not found: " + str(path))
    with open(path, "r", encoding="utf-8") as stream:
        value = yaml.safe_load(stream)
    return value or {}


def _normalize_facts(facts, hard_domains):
    if not isinstance(facts, dict):
        raise ClassifyError("classification facts must be a mapping")
    allowed = {"paths", "sensitive_domains", "reversible", "evidence"}
    unknown_fields = sorted(set(facts) - allowed)
    if unknown_fields:
        raise ClassifyError("unknown classification fact fields: " + ", ".join(unknown_fields))
    evidence = facts.get("evidence")
    if not isinstance(evidence, list) or not evidence or not all(
            isinstance(item, str) and item.strip() for item in evidence):
        raise ClassifyError("classification facts require non-empty evidence")
    paths = facts.get("paths") or []
    if not isinstance(paths, list) or not all(
            isinstance(path, str) and path.strip() and not os.path.isabs(path) and
            ".." not in path.replace("\\", "/").split("/") for path in paths):
        raise ClassifyError("classification fact paths must be repository-relative")
    domains = facts.get("sensitive_domains") or []
    if not isinstance(domains, list):
        raise ClassifyError("sensitive_domains must be a list")
    invalid_domains = sorted(set(domains) - set(hard_domains))
    if invalid_domains:
        raise ClassifyError("unknown hard-escalation domain: " + ", ".join(invalid_domains))
    reversible = facts.get("reversible")
    if reversible is not None and not isinstance(reversible, bool):
        raise ClassifyError("reversible must be true, false, or omitted")
    return {
        "paths": sorted(set(path.strip().replace("\\", "/") for path in paths)),
        "sensitive_domains": sorted(set(domains)),
        "reversible": reversible,
        "evidence": [item.strip() for item in evidence],
    }


def classify(title, suggested_level=None, hits=None, contract=None, facts=None):
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
    scoped_facts = _normalize_facts(facts, hard_domains) if facts is not None else None
    actual_domains = scoped_facts["sensitive_domains"] if scoped_facts else hits
    irreversible = scoped_facts is not None and scoped_facts.get("reversible") is False
    if actual_domains or irreversible:
        level = contract["hard_escalation"]["to"]
        reasons = ["hard_escalation: " + h for h in actual_domains]
        if irreversible:
            reasons.append("hard_escalation: explicitly_not_reversible")
        escalated = suggested != level
    else:
        level = suggested
        reasons = ["suggested_level: " + suggested]
        escalated = False
    if scoped_facts is None:
        evidence = ["hits=" + ",".join(hits)] if hits else ["no_hard_domain_hits"]
        return {"level": level, "reasons": reasons, "evidence": evidence,
                "suggested_level": suggested, "escalated": escalated}
    evidence = [
        {"kind": "keyword_hint", "domain": domain, "confidence": "heuristic"}
        for domain in hits
    ]
    evidence.extend(
        {"kind": "user_hint", "domain": domain, "confidence": "direct"}
        for domain in actual_domains
    )
    evidence.extend("fact_evidence: " + item for item in scoped_facts["evidence"])
    if not actual_domains:
        reasons.append("scoped_facts: no_sensitive_domain_declared")
    return {
        "level": level,
        "reasons": reasons,
        "evidence": evidence,
        "suggested_level": suggested,
        "escalated": escalated,
        "keyword_hints": hits,
        "facts": scoped_facts,
    }


def reassess(current, title, suggested_level=None, hits=None, contract=None, facts=None):
    """Re-evaluate with fresh facts while preventing a silent risk downgrade."""
    current_level = current.get("level") if isinstance(current, dict) else current
    if current_level not in LEVEL_RANK:
        raise ClassifyError("invalid current level: " + str(current_level))
    result = classify(
        title,
        suggested_level=suggested_level or current_level,
        hits=hits,
        contract=contract,
        facts=facts,
    )
    result["downgrade_blocked"] = False
    if LEVEL_RANK[result["level"]] < LEVEL_RANK[current_level]:
        result["level"] = current_level
        result["reasons"] = list(result["reasons"]) + [
            "downgrade_blocked: retain " + current_level
        ]
        result["downgrade_blocked"] = True
    return result
