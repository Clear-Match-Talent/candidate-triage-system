"""Context builder for the recruiting data chat assistant."""

from __future__ import annotations

from typing import Any, Dict, List
import re

from webapp.chatbot_knowledge import (
    RECRUITING_FIELD_GLOSSARY,
    COMMON_DATA_QUALITY_ISSUES,
    SUCCESSFUL_TRANSFORMATIONS,
)

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
LINKEDIN_REGEX = re.compile(r"^https?://(www\.)?linkedin\.com/in/", re.IGNORECASE)


def _is_filled(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    return True


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def analyze_data_quality(data: List[dict]) -> List[dict]:
    """Detect common data quality issues in standardized candidate rows."""
    issues: List[dict] = []
    if not data:
        return issues

    fields = list(data[0].keys())
    total_rows = len(data)

    def has_field(field: str) -> bool:
        return field in fields

    critical_fields = [
        field
        for field, meta in RECRUITING_FIELD_GLOSSARY.items()
        if meta.get("importance") == "critical" and has_field(field)
    ]

    for field in critical_fields:
        missing = sum(1 for row in data if not _is_filled(row.get(field)))
        if missing:
            issues.append(
                {
                    "severity": "critical",
                    "issue": f"{missing} candidates missing {field}",
                    "affected_rows": missing,
                    "suggested_fix": f"Enrich or re-scrape data for {field}.",
                }
            )

    if has_field("linkedin_url") and has_field("experience_text"):
        linkedin_no_exp = sum(
            1
            for row in data
            if _is_filled(row.get("linkedin_url"))
            and not _is_filled(row.get("experience_text"))
        )
        if linkedin_no_exp:
            issues.append(
                {
                    "severity": "high",
                    "issue": "LinkedIn URL present but experience_text missing",
                    "affected_rows": linkedin_no_exp,
                    "suggested_fix": "Re-scrape or enrich experience_text for these candidates.",
                }
            )

    if has_field("linkedin_url"):
        invalid_linkedin = sum(
            1
            for row in data
            if _is_filled(row.get("linkedin_url"))
            and not LINKEDIN_REGEX.match(_safe_str(row.get("linkedin_url")))
        )
        if invalid_linkedin:
            issues.append(
                {
                    "severity": "medium",
                    "issue": "Invalid LinkedIn URL format",
                    "affected_rows": invalid_linkedin,
                    "suggested_fix": "Normalize or re-collect LinkedIn URLs.",
                }
            )

    if has_field("email"):
        invalid_email = sum(
            1
            for row in data
            if _is_filled(row.get("email"))
            and not EMAIL_REGEX.match(_safe_str(row.get("email")))
        )
        if invalid_email:
            issues.append(
                {
                    "severity": "high",
                    "issue": "Invalid email format",
                    "affected_rows": invalid_email,
                    "suggested_fix": "Validate emails or remove obvious bad values.",
                }
            )

    contact_fields = [field for field in ["email", "linkedin_url", "phone"] if has_field(field)]
    if contact_fields:
        missing_contact = sum(
            1
            for row in data
            if all(not _is_filled(row.get(field)) for field in contact_fields)
        )
        if missing_contact:
            issues.append(
                {
                    "severity": "high",
                    "issue": "Missing contact info (email/LinkedIn/phone)",
                    "affected_rows": missing_contact,
                    "suggested_fix": "Prioritize enrichment of contact fields.",
                }
            )

    def _duplicate_counts(field: str) -> int:
        seen: Dict[str, int] = {}
        for row in data:
            val = _safe_str(row.get(field))
            if not val:
                continue
            seen[val] = seen.get(val, 0) + 1
        return sum(count for count in seen.values() if count > 1)

    if has_field("linkedin_url"):
        dup_linkedin = _duplicate_counts("linkedin_url")
        if dup_linkedin:
            issues.append(
                {
                    "severity": "medium",
                    "issue": "Duplicate LinkedIn URLs detected",
                    "affected_rows": dup_linkedin,
                    "suggested_fix": "Deduplicate candidates by linkedin_url.",
                }
            )

    if has_field("email"):
        dup_email = _duplicate_counts("email")
        if dup_email:
            issues.append(
                {
                    "severity": "medium",
                    "issue": "Duplicate emails detected",
                    "affected_rows": dup_email,
                    "suggested_fix": "Deduplicate candidates by email.",
                }
            )

    if has_field("full_name") and total_rows:
        missing_full_name = sum(1 for row in data if not _is_filled(row.get("full_name")))
        if missing_full_name:
            issues.append(
                {
                    "severity": "medium",
                    "issue": "Missing full_name values",
                    "affected_rows": missing_full_name,
                    "suggested_fix": "Backfill full_name from first_name/last_name when available.",
                }
            )

    return issues


def _compute_field_stats(data: List[dict], fields: List[str]) -> Dict[str, dict]:
    total_rows = len(data)
    stats: Dict[str, dict] = {}
    for field in fields:
        values = [row.get(field) for row in data]
        filled = sum(1 for value in values if _is_filled(value))
        empty = total_rows - filled
        unique = len({ _safe_str(value) for value in values if _is_filled(value) })
        filled_pct = round((filled / total_rows) * 100, 1) if total_rows else 0.0
        stats[field] = {
            "filled": filled,
            "empty": empty,
            "unique": unique,
            "filled_pct": filled_pct,
            "total": total_rows,
        }
    return stats


def format_field_stats(field_stats: Dict[str, dict]) -> str:
    """Format field stats for human-readable system prompt."""
    lines = []
    for field, stats in field_stats.items():
        lines.append(
            f"- {field}: filled {stats['filled']}/{stats['total']} "
            f"({stats['filled_pct']}%), unique {stats['unique']}"
        )
    return "\n".join(lines) if lines else "No field stats available."


def format_quality_issues(issues: List[dict]) -> str:
    """Format quality issues for human-readable system prompt."""
    if not issues:
        return "No major issues detected."
    lines = []
    for issue in issues:
        severity = issue.get("severity", "info")
        affected = issue.get("affected_rows", 0)
        detail = issue.get("issue", "Issue")
        suggestion = issue.get("suggested_fix")
        line = f"- [{severity}] {detail} (affected: {affected})"
        if suggestion:
            line += f" | Suggested fix: {suggestion}"
        lines.append(line)
    return "\n".join(lines)


def build_agent_context(st: Any) -> dict:
    """Build structured context for the agent from RunStatus."""
    if not st.standardized_data:
        return {"error": "No data loaded"}

    fields = list(st.standardized_data[0].keys())
    total_rows = len(st.standardized_data)

    quality_issues = analyze_data_quality(st.standardized_data)
    field_stats = _compute_field_stats(st.standardized_data, fields)

    field_definitions = {
        field: RECRUITING_FIELD_GLOSSARY.get(
            field,
            {"description": "Unknown field", "common_issues": [], "importance": "low"},
        )
        for field in fields
    }

    return {
        "dataset_info": {
            "total_candidates": total_rows,
            "fields": fields,
            "role": st.role_label,
        },
        "field_definitions": field_definitions,
        "field_stats": field_stats,
        "quality_issues": quality_issues,
        "sample_rows": st.standardized_data[:3],
        "common_issues": COMMON_DATA_QUALITY_ISSUES,
        "example_transformations": SUCCESSFUL_TRANSFORMATIONS[:6],
    }
