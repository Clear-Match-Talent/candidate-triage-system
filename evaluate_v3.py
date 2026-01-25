#!/usr/bin/env python3
"""
V3: Expanded school list, auto-reject criteria, 3+ years experience
Usage: python evaluate_v3.py <input.csv> <output.csv>
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

# Top ~120 US Universities for CS/Engineering
TOP_SCHOOLS = """
MIT, Stanford, Carnegie Mellon, UC Berkeley, Caltech, Princeton, Harvard, Cornell,
UIUC (University of Illinois Urbana-Champaign), University of Washington, Georgia Tech,
UT Austin (University of Texas at Austin), University of Michigan, Columbia University,
UCLA, UC San Diego, University of Pennsylvania, Yale, Brown, Dartmouth, Duke,
Northwestern, Johns Hopkins, Rice, Vanderbilt, Notre Dame, USC (University of Southern California),
NYU (New York University), Boston University, Tufts, Northeastern, UMass Amherst,
University of Wisconsin-Madison, University of Maryland, Purdue, Ohio State, Penn State,
Rutgers, Stony Brook (SUNY Stony Brook), University of Virginia, UNC Chapel Hill,
UC Santa Barbara, UC Irvine, UC Davis, University of Minnesota, University of Colorado Boulder,
University of Arizona, Arizona State, Texas A&M, Virginia Tech, NC State,
University of Florida, University of Rochester, RPI (Rensselaer Polytechnic Institute),
WPI (Worcester Polytechnic Institute), Case Western Reserve, Lehigh, Syracuse,
RIT (Rochester Institute of Technology), Drexel, Stevens Institute of Technology,
University of Pittsburgh, UCSF, Boston College, Brandeis, Emory, Tulane,
George Washington University, Georgetown, Fordham, Villanova, Wake Forest,
University of Southern California, Pepperdine, Santa Clara University, Harvey Mudd,
Reed College, Occidental, Pomona College, Claremont McKenna, Williams College,
Amherst College, Swarthmore, Bowdoin, Middlebury, Wesleyan, Vassar, Hamilton College,
Colgate, Bates, Oberlin, Grinnell, Carleton, Macalester, Kenyon,
Iowa State, Kansas State, University of Kansas, University of Iowa, University of Nebraska,
University of Delaware, University of Connecticut, University of Tennessee,
University of Alabama, Auburn, Clemson, University of South Carolina, LSU,
University of Kentucky, University of Arkansas, Oklahoma State, University of Oklahoma,
Oregon State, University of Oregon, Washington State, University of Utah, BYU,
Colorado School of Mines, Colorado State, University of New Mexico, New Mexico State,
University of Hawaii, University of Nevada Reno, UNLV, San Diego State, Cal Poly SLO,
San Jose State, Cal State Long Beach, Queen's University (Canada), University of Waterloo (Canada),
University of Toronto (Canada), UBC (University of British Columbia), McGill,
University of Alberta, Ecole Polytechnique, ETH Zurich, EPFL, Oxford, Cambridge,
Imperial College London, UCL, University of Edinburgh, TU Munich, KTH Sweden,
IIT (Indian Institutes of Technology), Tsinghua University, Peking University,
National University of Singapore, Nanyang Technological University, KAIST, Seoul National University
"""

def parse_json_response(text):
    """Extract JSON from response, handling markdown code blocks."""
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

    # Cap at reasonable max
    return min(years_since_grad, 30)


def check_auto_reject(candidate):
    """
    Check auto-reject criteria.
    Returns (is_rejected, reason) tuple.
    """

    # Check 1: Bootcamp-only education
    education = candidate.get('education_text', '').lower()
    bootcamp_keywords = ['bootcamp', 'boot camp', 'hack reactor', 'general assembly',
                         'app academy', 'flatiron', 'coding dojo', 'devmountain',
                         'galvanize', 'thinkful', 'springboard']

    # Check if education mentions bootcamp
    has_bootcamp = any(keyword in education for keyword in bootcamp_keywords)

    # Check if education mentions a degree (Bachelor, Master, PhD, etc.)
    has_degree = bool(re.search(r'\b(bachelor|master|phd|doctorate|bs|ba|ms|ma|mba)\b', education, re.IGNORECASE))

    # If only bootcamp, no degree → REJECT
    if has_bootcamp and not has_degree:
        return (True, "Bootcamp-only education (no degree)")

    # Check 2: Open to work (if field exists)
    # Note: Most CSVs won't have this field, so we'll skip if missing
    open_to_work = candidate.get('open_to_work', '').lower()
    if open_to_work in ['true', 'yes', '1', 'open']:
        return (True, "Open to work badge on profile")

    # Check 3: Job hopping (3+ roles in last 5 years)
    # Note: Would need work history data - not available in current CSV
    # Placeholder for future implementation

    return (False, None)


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
    """Evaluate experience criterion - V3: 3+ years, exclude Front-End roles."""
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
1. At least 3 years of professional experience (LOWERED from 4 years)
2. Must be an Individual Contributor (IC) role, NOT a manager/director/VP
3. Must be a general/full-stack engineering role, NOT specialized front-end/mobile-only

{experience_context}

MET RULES (mark as MET if ANY apply):
- Title contains "Staff", "Principal", or "Distinguished" (these roles require 3+ years)
- Title contains "Senior" (typically requires 3+ years)
- Title contains "Lead Engineer" or "Tech Lead" (IC leadership, typically 3+ years)
- Title is "Software Engineer" or "Member of Technical Staff" AND graduated 3+ years ago
- Graduated 3+ years ago with any standard engineering title (SWE, Engineer, etc.)

NOT_MET RULES (mark as NOT_MET if ANY apply):
- Title contains "Manager", "Director", "VP", "Head of" (not IC roles)
- Title contains "Intern", "Trainee", "Associate" (too junior)
- Title is ONLY "Front-End Engineer", "Frontend Engineer", "Mobile Engineer", "iOS Engineer", "Android Engineer" (too specialized - we need full-stack)
- Title is "QA Engineer", "Support Engineer", "Customer Support", "DevOps Engineer" (not target role)
- Graduated less than 3 years ago AND title doesn't indicate seniority (Senior/Staff/Lead)
- Bootcamp graduate within last 3 years without senior title

UNKNOWN RULES (mark as UNKNOWN if applies):
- Cannot determine years of experience from title or graduation date
- Title is ambiguous without context

CRITICAL POLICY:
- Absence of evidence = UNKNOWN (not NOT_MET)
- Only mark NOT_MET if there is clear contradictory evidence
- Staff/Senior/Principal titles = strong signal of 3+ years (mark MET)
- Manager/Director/VP = automatic NOT_MET (wrong role type)
- Front-End/Mobile ONLY roles = NOT_MET (too specialized)
- "Software Engineer" (general) = GOOD if 3+ years experience

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
    """Evaluate education criterion - V3: Expanded to top ~120 schools."""
    education = candidate.get('education_text', '')
    experience = candidate.get('experience_text', '')
    company = candidate.get('company_name', '')

    prompt = f"""You are evaluating whether a candidate meets the education/signal requirement for a role.

CRITERION: Top ~120 US/International Universities OR equivalent compensating signals

CANDIDATE DATA:
- Education: {education}
- Experience: {experience}
- Current Company: {company}

TOP SCHOOLS LIST (COMPREHENSIVE):
{TOP_SCHOOLS}

MET RULES (mark as MET if any apply):
- Attended any of the schools listed above for CS/Engineering/STEM degree
- No degree BUT worked at highly selective companies (Jane Street, Citadel, OpenAI, DeepMind, Google Brain, Meta FAIR, Stripe early, Databricks early)
- Strong open-source contributions mentioned or competitive programming (ICPC, Kaggle top)

NOT_MET RULES (mark as NOT_MET if any apply):
- ONLY education is a coding bootcamp (Hack Reactor, General Assembly, App Academy, etc.) with NO university degree
- Education is from non-listed school AND no compensating signals (selective company, OSS, competitions)

UNKNOWN RULES (mark as UNKNOWN if any apply):
- Education field is missing or empty
- School name is present but cannot determine if it's on the list
- Self-taught with insufficient work history to assess
- Cannot verify if company experience is sufficiently selective

CRITICAL POLICY:
- The school list is VERY comprehensive - most reputable US universities are included
- Absence of evidence = UNKNOWN (not NOT_MET)
- Only mark NOT_MET if bootcamp-only OR clear non-listed school with no signals
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
            dismiss_reason = 'experience_3plus_years'
        elif education_result['status'] == 'NOT_MET':
            dismiss_reason = 'school_top_120'
    elif 'UNKNOWN' in statuses:
        decision = 'HUMAN_REVIEW'
        # Find which criteria need review
        review_focus = []
        if location_result['status'] == 'UNKNOWN':
            review_focus.append('location_nyc')
        if experience_result['status'] == 'UNKNOWN':
            review_focus.append('experience_3plus_years')
        if education_result['status'] == 'UNKNOWN':
            review_focus.append('school_top_120')
        dismiss_reason = '; '.join(review_focus)
    else:
        decision = 'PROCEED'
        dismiss_reason = ''

    return decision, dismiss_reason


def evaluate_candidate(candidate, index, total):
    """Evaluate a single candidate against all criteria."""
    name = f"{candidate.get('first_name', '')} {candidate.get('last_name', '')}"
    print(f"[{index}/{total}] Evaluating {name}...", end=' ', flush=True)

    # Check auto-reject criteria FIRST
    is_rejected, reject_reason = check_auto_reject(candidate)
    if is_rejected:
        print(f"DISMISS (Auto-reject: {reject_reason})")

        result = candidate.copy()
        result['criterion_location_status'] = 'N/A'
        result['criterion_location_reason'] = 'Skipped due to auto-reject'
        result['criterion_location_evidence'] = 'N/A'
        result['criterion_experience_status'] = 'N/A'
        result['criterion_experience_reason'] = 'Skipped due to auto-reject'
        result['criterion_experience_evidence'] = 'N/A'
        result['criterion_education_status'] = 'N/A'
        result['criterion_education_reason'] = 'Skipped due to auto-reject'
        result['criterion_education_evidence'] = 'N/A'
        result['overall_decision'] = 'DISMISS'
        result['review_focus_or_dismiss_reason'] = f'AUTO_REJECT: {reject_reason}'

        return result

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
        print("Usage: python evaluate_v3.py <input.csv> <output.csv>")
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
        # Build fieldnames from union of keys (preserve first-seen order).
        # This prevents crashes when the first row is an ERROR row (which may not
        # include criterion_* fields) but later rows do.
        fieldnames: list[str] = []
        seen = set()
        for row in results:
            for k in row.keys():
                if k not in seen:
                    fieldnames.append(k)
                    seen.add(k)

        from pathlib import Path
        out_path = Path(output_file)
        if out_path.parent and str(out_path.parent) not in (".", ""):
            out_path.parent.mkdir(parents=True, exist_ok=True)

        with open(out_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(results)

    # Print summary
    print("\n=== SUMMARY ===")
    proceed_count = sum(1 for r in results if r['overall_decision'] == 'PROCEED')
    review_count = sum(1 for r in results if r['overall_decision'] == 'HUMAN_REVIEW')
    dismiss_count = sum(1 for r in results if r['overall_decision'] == 'DISMISS')
    error_count = sum(1 for r in results if r['overall_decision'] == 'ERROR')

    # Count auto-rejects
    auto_reject_count = sum(1 for r in results if 'AUTO_REJECT' in r.get('review_focus_or_dismiss_reason', ''))

    print(f"PROCEED: {proceed_count}")
    print(f"HUMAN_REVIEW: {review_count}")
    print(f"DISMISS: {dismiss_count}")
    if auto_reject_count:
        print(f"  └─ Auto-rejected: {auto_reject_count}")
    if error_count:
        print(f"ERROR: {error_count}")

    print(f"\nResults saved to {output_file}")


if __name__ == "__main__":
    main()
