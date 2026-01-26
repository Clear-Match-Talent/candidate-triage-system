"""Candidate evaluation for test runs using role criteria."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from anthropic import Anthropic

logger = logging.getLogger(__name__)

MODEL_NAME = "claude-sonnet-4-5-20250929"

GATING_PARAM_LABELS = {
    "job_hopper": "Job hopper (>3 jobs in 5 years)",
    "bootcamp_only": "Bootcamp-only education (no degree)",
    "location_mismatch": "Location mismatch",
}


def extract_json_object(text: str) -> Dict[str, Any]:
    if not text:
        return {}
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}


def normalize_status(value: Optional[str]) -> str:
    if not value:
        return "Unsure"
    normalized = value.strip().lower()
    if normalized.startswith("pass"):
        return "Pass"
    if normalized.startswith("fail"):
        return "Fail"
    if normalized.startswith("unsure") or normalized.startswith("unknown"):
        return "Unsure"
    return "Unsure"


def build_gating_param_list(gating_params: Any) -> List[str]:
    if not isinstance(gating_params, dict):
        return []
    entries: List[str] = []
    for key, label in GATING_PARAM_LABELS.items():
        if gating_params.get(key):
            entries.append(label)
    custom_rule = (gating_params.get("custom_rule") or "").strip()
    if custom_rule:
        entries.append(custom_rule)
    return entries


def candidate_has_content(candidate: Dict[str, Any]) -> bool:
    def has_value(value: Any) -> bool:
        return isinstance(value, str) and value.strip() != ""

    for key in (
        "first_name",
        "last_name",
        "full_name",
        "linkedin_url",
        "location",
        "current_company",
        "current_title",
    ):
        if has_value(candidate.get(key)):
            return True

    standardized_data = candidate.get("standardized_data")
    if isinstance(standardized_data, dict):
        for value in standardized_data.values():
            if has_value(value):
                return True

    return False


def _normalize_evaluations(
    criteria: List[str], response_items: Any
) -> List[Dict[str, str]]:
    response_map: Dict[str, Dict[str, str]] = {}
    if isinstance(response_items, list):
        for item in response_items:
            if not isinstance(item, dict):
                continue
            criterion = (item.get("criterion") or "").strip()
            if criterion:
                response_map[criterion] = item

    normalized: List[Dict[str, str]] = []
    for criterion in criteria:
        item = response_map.get(criterion, {})
        status = normalize_status(item.get("status"))
        reason = (item.get("reason") or "").strip() or "Insufficient information."
        normalized.append(
            {"criterion": criterion, "status": status, "reason": reason}
        )
    return normalized


def _bucket_from_evaluations(
    must_haves: List[Dict[str, str]],
    gating_params: List[Dict[str, str]],
    nice_to_haves: List[Dict[str, str]],
) -> str:
    all_evals = must_haves + gating_params + nice_to_haves
    if all_evals and all(e.get("status") == "Unsure" for e in all_evals):
        return "Unable to Enrich"

    if any(e.get("status") == "Fail" for e in gating_params):
        return "Dismiss"

    if any(e.get("status") == "Fail" for e in must_haves):
        return "Dismiss"

    if must_haves and all(e.get("status") == "Pass" for e in must_haves):
        return "Proceed"

    if any(e.get("status") == "Unsure" for e in must_haves):
        return "Human Review"

    return "Human Review"


def evaluate_candidate(
    candidate: Dict[str, Any],
    criteria: Dict[str, Any],
    client: Optional[Anthropic] = None,
) -> Dict[str, Any]:
    """Evaluate a candidate using Claude and return structured results."""
    if not candidate_has_content(candidate):
        return {
            "evaluations": {
                "must_haves": [],
                "gating_params": [],
                "nice_to_haves": [],
            },
            "bucket": "Unable to Enrich",
        }

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key and client is None:
        raise ValueError("ANTHROPIC_API_KEY is not set")
    if client is None:
        client = Anthropic(api_key=api_key)

    must_haves = criteria.get("must_haves") or []
    gating_params = build_gating_param_list(criteria.get("gating_params"))
    nice_to_haves = criteria.get("nice_to_haves") or []

    candidate_payload = {
        "first_name": candidate.get("first_name"),
        "last_name": candidate.get("last_name"),
        "full_name": candidate.get("full_name"),
        "linkedin_url": candidate.get("linkedin_url"),
        "location": candidate.get("location"),
        "current_company": candidate.get("current_company"),
        "current_title": candidate.get("current_title"),
        "standardized_data": candidate.get("standardized_data"),
    }

    prompt = (
        "You are evaluating a candidate for a recruiting test run.\n"
        "For each criterion, decide Pass, Fail, or Unsure and provide a single "
        "sentence reason. If data is missing, return Unsure with reason "
        "\"Insufficient information.\".\n\n"
        "Return ONLY JSON in this format:\n"
        "{\n"
        "  \"must_haves\": [{\"criterion\": \"...\", \"status\": \"Pass|Fail|Unsure\", "
        "\"reason\": \"...\"}],\n"
        "  \"gating_params\": [{\"criterion\": \"...\", \"status\": "
        "\"Pass|Fail|Unsure\", \"reason\": \"...\"}],\n"
        "  \"nice_to_haves\": [{\"criterion\": \"...\", \"status\": "
        "\"Pass|Fail|Unsure\", \"reason\": \"...\"}]\n"
        "}\n\n"
        f"Candidate:\n{json.dumps(candidate_payload, ensure_ascii=False)}\n\n"
        f"Must-haves: {json.dumps(must_haves, ensure_ascii=False)}\n"
        f"Gating params: {json.dumps(gating_params, ensure_ascii=False)}\n"
        f"Nice-to-haves: {json.dumps(nice_to_haves, ensure_ascii=False)}\n"
    )

    response = client.messages.create(
        model=MODEL_NAME,
        max_tokens=900,
        messages=[{"role": "user", "content": prompt}],
    )
    text_response = next(
        (block.text for block in response.content if hasattr(block, "text")), ""
    )
    payload = extract_json_object(text_response)

    normalized_must = _normalize_evaluations(must_haves, payload.get("must_haves"))
    normalized_gating = _normalize_evaluations(
        gating_params, payload.get("gating_params")
    )
    normalized_nice = _normalize_evaluations(
        nice_to_haves, payload.get("nice_to_haves")
    )

    bucket = _bucket_from_evaluations(
        normalized_must, normalized_gating, normalized_nice
    )

    return {
        "evaluations": {
            "must_haves": normalized_must,
            "gating_params": normalized_gating,
            "nice_to_haves": normalized_nice,
        },
        "bucket": bucket,
    }
