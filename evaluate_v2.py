#!/usr/bin/env python3
"""
Revised candidate triage evaluation script with simplified experience criterion.
Usage: python evaluate_v2.py <input.csv> <output.csv>
"""

import csv
import json
import os
import re
import sys
from datetime import datetime
from anthropic import Anthropic

# Initialize Anthropic client
client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

def parse_json_response(text):
    """Extract JSON from response, handling markdown code blocks."""
    # Try to parse as-is first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to extract JSON from code blocks
    json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
    match = re.search(json_pattern, text, re.DOTALL)
    if match:
        return json.loads(match.group(1))

    # Try to find JSON object in the text
    json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    match = re.search(json_pattern, text, re.DOTALL)
    if match:
        return json.loads(match.group(0))

    raise ValueError(f"Could not extract JSON from response: {text[:200]}")


def calculate_years_since_graduation(education_text):
    """Try to extract graduation year and calculate years of experience."""
    if not education_text:
        return None

    # Look for 4-digit years
    years = re.findall(r'\b(19\d{2}|20[0-2]\d)\b', education_text)
    if not years:
        return None

    # Take the most recent year (likely graduation)
    graduation_year = max(int(y) for y in years)
    current_year = 2026  # Current year

    years_since_grad = current_year - graduation_year

    # Cap at reasonable max (someone who graduated in 1995 has 30+ YOE)
    return min(years_since_grad, 30)


def evaluate_location(candidate):
    """Evaluate location criterion."""
    location = candidate.get('location', '')

    prompt = f"""You are evaluating whether a candidate meets the location requirement for a role.

CRITERION: Within 50 miles of NYC

CANDIDATE LOCATION: {location}

MET RULES (mark as MET if any apply):
- Location indicates within 50 miles of NYC (Manhattan, Brooklyn, Queens, Bronx, Staten Island, Jersey City, Hoboken, Weehawken, Fort Lee, etc.)
- Location mentions NYC boroughs or immediate suburbs

NOT_MET RULES (mark as NOT_MET if any apply):
- Location explicitly outside NYC metro area (e.g., San Francisco, Boston, Seattle, Austin, Remote-only)
- Location is in a different US city or international

UNKNOWN RULES (mark as UNKNOWN if any apply):
- Location field is missing or empty
- Location is too vague (e.g., "United States", "East Coast", "Flexible")

CRITICAL POLICY:
- Absence of evidence = UNKNOWN (not NOT_MET)
- Only mark NOT_MET if there is clear contradictory evidence

Respond ONLY in this exact JSON format:
{{
  "status": "MET" | "NOT_MET" | "UNKNOWN",
  "reason": "Brief 1-2 sentence explanation",
  "evidence": "Direct quote from location field or 'N/A'"
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=500,
        temperature=0,
        messages=[{"role": "user", "content": prompt}]
    )

    return parse_json_response(response.content[0].text)


def evaluate_experience(candidate):
    """Evaluate experience criterion - REVISED to be simpler."""
    title = candidate.get('title', '')
    education_text = candidate.get('education_text', '')

    # Calculate years since graduation
    years_since_grad = calculate_years_since_graduation(education_text)

    experience_context = f"""
CANDIDATE DATA:
- Current Title: {title}
- Education: {education_text}
- Estimated Years Since Graduation: {years_since_grad if years_since_grad else 'Unknown'}
"""

    prompt = f"""You are evaluating whether a candidate meets the experience requirement for a role.

CRITERION:
1. At least 4 years of professional experience
2. Must be an Individual Contributor (IC) role, NOT a manager/director/VP

{experience_context}

MET RULES (mark as MET if ANY apply):
- Title contains "Staff", "Principal", or "Distinguished" (these roles require 4+ years)
- Title contains "Senior" (typically requires 4+ years)
- Title contains "Lead Engineer" or "Tech Lead" (IC leadership, typically 4+ years)
- Graduated 4+ years ago (estimated years since graduation >= 4)
- Title is "Software Engineer" or similar AND graduated 4+ years ago

NOT_MET RULES (mark as NOT_MET if ANY apply):
- Title contains "Manager", "Director", "VP", "Head of" (not IC roles)
- Title contains "Intern", "Trainee", "Associate" (too junior)
- Title is "QA Engineer", "Support Engineer", "Customer Support" (not target role)
- Graduated less than 4 years ago AND title doesn't indicate seniority (Senior/Staff/Lead)
- Bootcamp graduate within last 4 years without senior title

UNKNOWN RULES (mark as UNKNOWN if applies):
- Cannot determine years of experience from title or graduation date
- Title is ambiguous (e.g., "Member of Technical Staff" varies by company)
- Title is "Engineer II" or "Engineer III" without context

CRITICAL POLICY:
- Absence of evidence = UNKNOWN (not NOT_MET)
- Only mark NOT_MET if there is clear contradictory evidence
- Staff/Senior/Principal titles = strong signal of 4+ years (mark MET)
- Manager/Director/VP = automatic NOT_MET (wrong role type)

Respond ONLY in this exact JSON format:
{{
  "status": "MET" | "NOT_MET" | "UNKNOWN",
  "reason": "Brief 1-2 sentence explanation",
  "evidence": "Key evidence excerpt or 'N/A'"
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=500,
        temperature=0,
        messages=[{"role": "user", "content": prompt}]
    )

    return parse_json_response(response.content[0].text)


def evaluate_education(candidate):
    """Evaluate education criterion."""
    education = candidate.get('education_text', '')
    experience = candidate.get('experience_text', '')
    company = candidate.get('company_name', '')

    prompt = f"""You are evaluating whether a candidate meets the education/signal requirement for a role.

CRITERION: Top-tier CS program OR equivalent compensating signals

CANDIDATE DATA:
- Education: {education}
- Experience: {experience}
- Current Company: {company}

MET RULES (mark as MET if any apply):
- Attended MIT, Stanford, CMU, UC Berkeley, Caltech, Princeton, Harvard, Cornell, UIUC, UWashington for CS/Engineering
- Attended top international CS programs (e.g., Waterloo, ETH Zurich, IIT, Tsinghua, Oxford, Cambridge)
- No degree BUT worked at highly selective companies (e.g., Jane Street, Citadel, OpenAI, DeepMind, Google Brain, Meta FAIR)
- Strong open-source contributions mentioned or competitive programming background (e.g., ICPC finalist, top Kaggle contributor)

NOT_MET RULES (mark as NOT_MET if any apply):
- Education is from non-target school AND no compensating signals (selective company, OSS, competitions)
- Bootcamp background without subsequent work at top-tier company
- Only has experience at non-selective companies with non-target education

UNKNOWN RULES (mark as UNKNOWN if any apply):
- Education field is missing or empty
- School name is present but cannot determine if it's a top-tier program
- Self-taught with insufficient work history to assess
- Cannot verify if company experience is sufficiently selective

CRITICAL POLICY:
- Absence of evidence = UNKNOWN (not NOT_MET)
- Only mark NOT_MET if there is clear evidence of non-target education AND no compensating signals
- Compensating signals (selective companies, OSS, competitions) can substitute for education

Respond ONLY in this exact JSON format:
{{
  "status": "MET" | "NOT_MET" | "UNKNOWN",
  "reason": "Brief 1-2 sentence explanation",
  "evidence": "School name or company name or 'N/A'"
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=500,
        temperature=0,
        messages=[{"role": "user", "content": prompt}]
    )

    return parse_json_response(response.content[0].text)


def calculate_decision(location_result, experience_result, education_result):
    """Calculate overall decision based on criterion results."""
    statuses = [
        location_result['status'],
        experience_result['status'],
        education_result['status']
    ]

    if 'NOT_MET' in statuses:
        decision = 'DISMISS'
        # Find which criterion caused dismiss
        dismiss_reason = ''
        if location_result['status'] == 'NOT_MET':
            dismiss_reason = 'location_nyc'
        elif experience_result['status'] == 'NOT_MET':
            dismiss_reason = 'experience_4plus_years'
        elif education_result['status'] == 'NOT_MET':
            dismiss_reason = 'school_top_tier'
    elif 'UNKNOWN' in statuses:
        decision = 'HUMAN_REVIEW'
        # Find which criteria need review
        review_focus = []
        if location_result['status'] == 'UNKNOWN':
            review_focus.append('location_nyc')
        if experience_result['status'] == 'UNKNOWN':
            review_focus.append('experience_4plus_years')
        if education_result['status'] == 'UNKNOWN':
            review_focus.append('school_top_tier')
        dismiss_reason = '; '.join(review_focus)
    else:
        decision = 'PROCEED'
        dismiss_reason = ''

    return decision, dismiss_reason


def evaluate_candidate(candidate, index, total):
    """Evaluate a single candidate against all criteria."""
    name = f"{candidate.get('first_name', '')} {candidate.get('last_name', '')}"
    print(f"[{index}/{total}] Evaluating {name}...", end=' ', flush=True)

    # Evaluate each criterion
    location_result = evaluate_location(candidate)
    experience_result = evaluate_experience(candidate)
    education_result = evaluate_education(candidate)

    # Calculate overall decision
    decision, dismiss_reason = calculate_decision(
        location_result, experience_result, education_result
    )

    print(decision)

    # Add results to candidate data
    result = candidate.copy()
    result['criterion_location_status'] = location_result['status']
    result['criterion_location_reason'] = location_result['reason']
    result['criterion_location_evidence'] = location_result['evidence']

    result['criterion_experience_status'] = experience_result['status']
    result['criterion_experience_reason'] = experience_result['reason']
    result['criterion_experience_evidence'] = experience_result['evidence']

    result['criterion_education_status'] = education_result['status']
    result['criterion_education_reason'] = education_result['reason']
    result['criterion_education_evidence'] = education_result['evidence']

    result['overall_decision'] = decision
    result['review_focus_or_dismiss_reason'] = dismiss_reason

    return result


def main():
    if len(sys.argv) < 3:
        print("Usage: python evaluate_v2.py <input.csv> <output.csv>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    # Check for API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        print("Set it with: export ANTHROPIC_API_KEY=sk-ant-...")
        sys.exit(1)

    # Read input CSV
    print(f"Reading candidates from {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        candidates = list(reader)

    print(f"Found {len(candidates)} candidates\n")

    # Evaluate each candidate
    results = []
    for i, candidate in enumerate(candidates, 1):
        try:
            result = evaluate_candidate(candidate, i, len(candidates))
            results.append(result)
        except Exception as e:
            print(f"ERROR: {e}")
            # Add candidate with error status
            error_result = candidate.copy()
            error_result['overall_decision'] = 'ERROR'
            error_result['review_focus_or_dismiss_reason'] = str(e)
            results.append(error_result)

    # Write output CSV
    print(f"\nWriting results to {output_file}...")
    if results:
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            fieldnames = list(results[0].keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)

    # Print summary
    print("\n=== SUMMARY ===")
    proceed_count = sum(1 for r in results if r['overall_decision'] == 'PROCEED')
    review_count = sum(1 for r in results if r['overall_decision'] == 'HUMAN_REVIEW')
    dismiss_count = sum(1 for r in results if r['overall_decision'] == 'DISMISS')
    error_count = sum(1 for r in results if r['overall_decision'] == 'ERROR')

    print(f"PROCEED: {proceed_count}")
    print(f"HUMAN_REVIEW: {review_count}")
    print(f"DISMISS: {dismiss_count}")
    if error_count:
        print(f"ERROR: {error_count}")

    print(f"\nResults saved to {output_file}")


if __name__ == "__main__":
    main()
