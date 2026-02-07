from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping

from yuantus.config.settings import get_settings


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    rule_id: str
    details: Dict[str, Any] | None = None


ROUTING_RELEASE_RULES_DEFAULT: List[str] = [
    "routing.exists",
    "routing.not_already_released",
    "routing.has_operations",
    "routing.has_scope",
    "routing.primary_unique_in_scope",
    "routing.operation_workcenters_valid",
]

MBOM_RELEASE_RULES_DEFAULT: List[str] = [
    "mbom.exists",
    "mbom.not_already_released",
    "mbom.has_non_empty_structure",
    "mbom.has_released_routing",
]

BASELINE_RELEASE_RULES_DEFAULT: List[str] = [
    "baseline.exists",
    "baseline.not_already_released",
    "baseline.members_references_exist",
    "baseline.warnings_for_unreleased_or_changed_members",
]

ECO_APPLY_RULES_DEFAULT: List[str] = [
    "eco.exists",
    "eco.state_approved",
    "eco.required_fields_present",
    "eco.product_exists",
    "eco.target_version_exists",
    "eco.rebase_conflicts_absent",
]


def _without(rule_ids: List[str], removed: str) -> List[str]:
    return [r for r in (rule_ids or []) if r != removed]


ROUTING_RELEASE_RULES_READINESS: List[str] = _without(
    list(ROUTING_RELEASE_RULES_DEFAULT),
    "routing.not_already_released",
)

MBOM_RELEASE_RULES_READINESS: List[str] = _without(
    list(MBOM_RELEASE_RULES_DEFAULT),
    "mbom.not_already_released",
)

BASELINE_RELEASE_RULES_READINESS: List[str] = _without(
    list(BASELINE_RELEASE_RULES_DEFAULT),
    "baseline.not_already_released",
)


_BUILTIN_RULESETS: Mapping[str, Mapping[str, List[str]]] = {
    "routing_release": {
        "default": list(ROUTING_RELEASE_RULES_DEFAULT),
        "readiness": list(ROUTING_RELEASE_RULES_READINESS),
    },
    "mbom_release": {
        "default": list(MBOM_RELEASE_RULES_DEFAULT),
        "readiness": list(MBOM_RELEASE_RULES_READINESS),
    },
    "baseline_release": {
        "default": list(BASELINE_RELEASE_RULES_DEFAULT),
        "readiness": list(BASELINE_RELEASE_RULES_READINESS),
    },
    "eco_apply": {"default": list(ECO_APPLY_RULES_DEFAULT)},
}

_ALLOWED_RULE_IDS: Mapping[str, set[str]] = {
    "routing_release": set(ROUTING_RELEASE_RULES_DEFAULT),
    "mbom_release": set(MBOM_RELEASE_RULES_DEFAULT),
    "baseline_release": set(BASELINE_RELEASE_RULES_DEFAULT),
    "eco_apply": set(ECO_APPLY_RULES_DEFAULT),
}

_EXISTENCE_RULES: Mapping[str, str] = {
    "routing_release": "routing.exists",
    "mbom_release": "mbom.exists",
    "baseline_release": "baseline.exists",
    "eco_apply": "eco.exists",
}


def _parse_rulesets_json(raw: str) -> Dict[str, Any]:
    raw = (raw or "").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Invalid YUANTUS_RELEASE_VALIDATION_RULESETS_JSON: must be valid JSON"
        ) from exc
    if not isinstance(data, dict):
        raise ValueError(
            "Invalid YUANTUS_RELEASE_VALIDATION_RULESETS_JSON: must be a JSON object"
        )
    return data


def _load_configured_rulesets() -> Dict[str, Dict[str, List[str]]]:
    settings = get_settings()
    data = _parse_rulesets_json(getattr(settings, "RELEASE_VALIDATION_RULESETS_JSON", ""))
    configured: Dict[str, Dict[str, List[str]]] = {}
    for kind, rulesets in data.items():
        if not isinstance(kind, str) or not kind.strip():
            raise ValueError(
                "Invalid YUANTUS_RELEASE_VALIDATION_RULESETS_JSON: keys must be non-empty strings"
            )
        if not isinstance(rulesets, dict):
            raise ValueError(
                f"Invalid YUANTUS_RELEASE_VALIDATION_RULESETS_JSON: {kind} must be an object"
            )
        configured[kind] = {}
        for ruleset_id, rule_ids in rulesets.items():
            if not isinstance(ruleset_id, str) or not ruleset_id.strip():
                raise ValueError(
                    f"Invalid YUANTUS_RELEASE_VALIDATION_RULESETS_JSON: {kind} ruleset ids must be non-empty strings"
                )
            if not isinstance(rule_ids, list) or any(not isinstance(v, str) for v in rule_ids):
                raise ValueError(
                    f"Invalid YUANTUS_RELEASE_VALIDATION_RULESETS_JSON: {kind}.{ruleset_id} must be a list of strings"
                )
            normalized = [v.strip() for v in rule_ids if v and v.strip()]
            configured[kind][ruleset_id] = normalized
    return configured


def get_release_ruleset(kind: str, ruleset_id: str) -> List[str]:
    """
    Resolve release validation rules for a given kind/ruleset_id.

    - Built-in rulesets always exist for each supported kind ("default").
    - Additional rulesets can be provided via `YUANTUS_RELEASE_VALIDATION_RULESETS_JSON`.
    - Unknown rule ids in configured rulesets are rejected to fail fast.
    - Existence rules are always enforced as the first rule to keep evaluation safe.
    """

    effective: Dict[str, Dict[str, List[str]]] = {
        kind: {k: list(v) for k, v in rulesets.items()}
        for kind, rulesets in _BUILTIN_RULESETS.items()
    }

    configured = _load_configured_rulesets()
    for cfg_kind, rulesets in configured.items():
        effective.setdefault(cfg_kind, {})
        for cfg_ruleset_id, rule_ids in rulesets.items():
            allowed = _ALLOWED_RULE_IDS.get(cfg_kind)
            if allowed is not None:
                unknown = [rule_id for rule_id in rule_ids if rule_id not in allowed]
                if unknown:
                    raise ValueError(
                        f"Invalid YUANTUS_RELEASE_VALIDATION_RULESETS_JSON: {cfg_kind}.{cfg_ruleset_id} "
                        f"contains unknown rule ids: {', '.join(sorted(set(unknown)))}"
                    )
            effective[cfg_kind][cfg_ruleset_id] = list(rule_ids)

    rulesets_for_kind = effective.get(kind) or {}
    rules = rulesets_for_kind.get(ruleset_id)
    if rules is None:
        known = ", ".join(sorted(rulesets_for_kind.keys())) or "<none>"
        raise ValueError(f"Unknown release ruleset: kind={kind}, ruleset_id={ruleset_id}, known={known}")

    # Always enforce existence checks first (cannot be bypassed by configuration).
    existence_rule = _EXISTENCE_RULES.get(kind)
    if existence_rule:
        if existence_rule not in rules:
            rules = [existence_rule] + list(rules)
        else:
            rules = [existence_rule] + [r for r in rules if r != existence_rule]

    return rules


def get_release_validation_directory() -> Dict[str, Any]:
    """
    Directory/introspection endpoint helper.

    Returns built-in + configured rulesets and their resolved rule lists (existence rule first).
    """
    configured = _load_configured_rulesets()

    effective: Dict[str, Dict[str, List[str]]] = {
        kind: {ruleset_id: list(rule_ids) for ruleset_id, rule_ids in rulesets.items()}
        for kind, rulesets in _BUILTIN_RULESETS.items()
    }
    sources: Dict[str, Dict[str, str]] = {
        kind: {ruleset_id: "builtin" for ruleset_id in rulesets.keys()}
        for kind, rulesets in _BUILTIN_RULESETS.items()
    }

    for cfg_kind, rulesets in configured.items():
        effective.setdefault(cfg_kind, {})
        sources.setdefault(cfg_kind, {})
        for cfg_ruleset_id, rule_ids in rulesets.items():
            allowed = _ALLOWED_RULE_IDS.get(cfg_kind)
            if allowed is not None:
                unknown = [rule_id for rule_id in rule_ids if rule_id not in allowed]
                if unknown:
                    raise ValueError(
                        f"Invalid YUANTUS_RELEASE_VALIDATION_RULESETS_JSON: {cfg_kind}.{cfg_ruleset_id} "
                        f"contains unknown rule ids: {', '.join(sorted(set(unknown)))}"
                    )
            effective[cfg_kind][cfg_ruleset_id] = list(rule_ids)
            sources[cfg_kind][cfg_ruleset_id] = "configured"

    kinds: List[Dict[str, Any]] = []
    for kind in sorted(effective.keys()):
        rulesets_payload: List[Dict[str, Any]] = []
        existence_rule = _EXISTENCE_RULES.get(kind)
        for ruleset_id in sorted(effective[kind].keys()):
            rules = list(effective[kind][ruleset_id])
            if existence_rule:
                if existence_rule not in rules:
                    rules = [existence_rule] + list(rules)
                else:
                    rules = [existence_rule] + [r for r in rules if r != existence_rule]
            rulesets_payload.append(
                {
                    "ruleset_id": ruleset_id,
                    "source": sources.get(kind, {}).get(ruleset_id, "configured"),
                    "rule_ids": rules,
                }
            )

        allowed_set = _ALLOWED_RULE_IDS.get(kind)
        kinds.append(
            {
                "kind": kind,
                "existence_rule_id": existence_rule,
                "allowed_rule_ids": sorted(allowed_set) if allowed_set is not None else None,
                "rulesets": rulesets_payload,
            }
        )

    return {"kinds": kinds}
