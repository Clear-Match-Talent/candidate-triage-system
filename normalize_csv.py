#!/usr/bin/env python3
"""
Normalize CSV columns to match expected format.
"""

import csv
import sys

def normalize_csv(input_file, output_file):
    """Convert RecruitCRM-style CSV to evaluation format."""

    with open(input_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    normalized = []
    for row in rows:
        # Build education_text from multiple columns
        education_parts = []
        if row.get('candidate_educations_degree'):
            education_parts.append(row['candidate_educations_degree'])
        if row.get('candidate_education_major'):
            education_parts.append(row['candidate_education_major'])
        if row.get('candidate_education_school'):
            education_parts.append(f"- {row['candidate_education_school']}")
        if row.get('candidate_education_schoolEndDat'):
            education_parts.append(row['candidate_education_schoolEndDat'])

        education_text = ' '.join(education_parts) if education_parts else ''

        normalized_row = {
            'linkedin_url': row.get('linkedin_url', ''),
            'first_name': row.get('first_name', ''),
            'last_name': row.get('last_name', ''),
            'location': row.get('location', ''),
            'company_name': row.get('company_name', ''),
            'title': row.get('title', ''),
            'experience_text': '',  # Not available in this export
            'education_text': education_text,
            'summary': '',
            'skills': ''
        }
        normalized.append(normalized_row)

    # Write normalized CSV
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        fieldnames = ['linkedin_url', 'first_name', 'last_name', 'location',
                     'company_name', 'title', 'experience_text', 'education_text',
                     'summary', 'skills']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(normalized)

    print(f"Normalized {len(normalized)} candidates")
    print(f"Output: {output_file}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python normalize_csv.py <input.csv> <output.csv>")
        sys.exit(1)

    normalize_csv(sys.argv[1], sys.argv[2])
