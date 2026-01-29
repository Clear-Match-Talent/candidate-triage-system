# PRD: AI-Driven Criteria Generation

## Overview

**Goal:** Build a feature that uses AI to generate clear, testable filtering criteria from a Job Description (JD), intake call transcript, and calibration candidates.

**Problem:** Current filtering criteria are hardcoded in `evaluate_v3.py` and not relevant to most roles. Criteria like "top 120 schools" or "50 miles of NYC" are arbitrary and not testable against available data for many positions.

**Solution:** An AI-powered criteria generation system that takes role-specific inputs and outputs simple, binary heuristics that can be tested against LinkedIn/public profile data.

---

## Scope

### In Scope
- Upload and parse JD (document or text)
- Upload and parse intake call transcript (Fireflies/Aircall)
- Input calibration candidates (LinkedIn URLs via CSV)
- AI generates 3 must-have criteria per role
- Human review and edit interface for generated criteria
- Store finalized criteria per role

### Out of Scope
- Candidate enrichment (LinkedIn scraping, Wrangle, etc.)
- Candidate evaluation/filtering against criteria
- Nice-to-have criteria (future enhancement)
- Integration with evaluation pipeline

---

## User Flow

```
1. User creates/selects a Role in webapp
2. User uploads:
   - JD (PDF/DOCX/text)
   - Intake call transcript (Fireflies/Aircall export)
   - Calibration candidates CSV (LinkedIn URLs)
3. User clicks "Generate Criteria"
4. AI processes inputs and generates 3 must-have criteria
5. User reviews criteria in editable interface
6. User can:
   - Edit criteria text
   - Adjust MET/NOT_MET/UNKNOWN rules
   - Add/remove criteria
7. User clicks "Save Criteria"
8. Criteria stored for the role (ready for future evaluation)
```

---

## Inputs

### 1. Job Description (JD)
- **Format:** PDF, DOCX, or pasted text
- **Contains:** Role title, responsibilities, requirements, qualifications
- **Used for:** Extracting what the role needs, required vs preferred language

### 2. Intake Call Transcript
- **Format:** Text export from Fireflies or Aircall
- **Contains:** Conversation with hiring manager about the role
- **Used for:** Understanding nuance, priorities, what "good" looks like beyond JD

### 3. Calibration Candidates
- **Format:** CSV with LinkedIn URLs
- **Contains:** 2-5 examples of "good fit" candidates
- **Used for:** Pattern recognition — what do good candidates have in common?

---

## Output: Generated Criteria

### Structure (per criterion)

```json
{
  "id": "criterion_1",
  "name": "E-Commerce Experience",
  "description": "5+ years of experience in e-commerce or DTC brands",
  "type": "must_have",
  "testable_via": ["LinkedIn titles", "tenure dates", "company names"],
  "met_rules": [
    "Title includes 'eCommerce', 'E-Commerce', 'DTC', 'Direct to Consumer'",
    "5+ years cumulative experience at e-commerce/DTC companies",
    "Current or recent title is Director/Sr. Manager level in e-commerce"
  ],
  "not_met_rules": [
    "No e-commerce or DTC experience in work history",
    "Only B2B SaaS or unrelated industry experience",
    "Less than 3 years total e-commerce experience"
  ],
  "unknown_rules": [
    "Work history not available or incomplete",
    "Company types unclear from available data"
  ]
}
```

### Criteria Quality Requirements

**Good criteria are:**
- Binary or near-binary (yes/no/unknown)
- Based on facts, not inference
- Testable against LinkedIn or public company data
- Simple enough that AI evaluation is reliable
- Specific to the role

**Avoid generating criteria for:**
- Culture fit (not testable)
- Soft skills like "strong communication" (not testable from data)
- Arbitrary school lists (not relevant to most roles)
- Highly subjective assessments

---

## AI Prompt Strategy

### Criteria Generation Prompt

The AI will receive:
1. JD text
2. Intake transcript text
3. Calibration candidate profiles (scraped or provided)

The prompt will instruct AI to:
1. Identify the 3 most critical requirements for the role
2. Convert each requirement into a testable heuristic
3. Define clear MET/NOT_MET/UNKNOWN rules
4. Ground rules in data that exists on LinkedIn profiles
5. Prioritize based on JD language ("required" = must-have, "preferred" = nice-to-have for future)

### Calibration Candidate Analysis

The AI will analyze calibration candidates to:
1. Identify common patterns (titles, companies, tenure, skills)
2. Validate that generated criteria would mark these candidates as MET
3. Refine criteria if calibration candidates would fail

---

## UI/UX Requirements

### New UI Components

#### 1. Role Setup Page (enhanced)
- Existing: Role name, description
- **New:** Document upload section
  - JD upload (drag-drop or file picker)
  - Intake transcript upload (drag-drop or file picker)
  - Calibration CSV upload (drag-drop or file picker)

#### 2. Criteria Generation Section
- "Generate Criteria" button
- Loading state while AI processes
- Display generated criteria in editable cards

#### 3. Criteria Review/Edit Interface
- Each criterion displayed as a card with:
  - Name (editable)
  - Description (editable)
  - MET rules (editable list)
  - NOT_MET rules (editable list)
  - UNKNOWN rules (editable list)
- Add new criterion button
- Delete criterion button
- "Save Criteria" button

#### 4. Saved Criteria View
- Display finalized criteria for a role
- Edit button to modify
- Re-generate button to start fresh

---

## Data Model

### New Tables/Fields

```sql
-- Role documents
CREATE TABLE role_documents (
  id INTEGER PRIMARY KEY,
  role_id INTEGER REFERENCES roles(id),
  doc_type TEXT NOT NULL, -- 'jd', 'intake_transcript', 'calibration_csv'
  filename TEXT,
  content TEXT, -- extracted text content
  uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Generated/edited criteria
CREATE TABLE role_criteria (
  id INTEGER PRIMARY KEY,
  role_id INTEGER REFERENCES roles(id),
  name TEXT NOT NULL,
  description TEXT,
  type TEXT DEFAULT 'must_have', -- 'must_have', 'nice_to_have'
  testable_via TEXT, -- JSON array of data sources
  met_rules TEXT, -- JSON array of rules
  not_met_rules TEXT, -- JSON array of rules
  unknown_rules TEXT, -- JSON array of rules
  is_ai_generated BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Technical Implementation

### Document Processing
- **PDF parsing:** PyPDF2 or pdfplumber
- **DOCX parsing:** python-docx
- **Transcript parsing:** Plain text processing

### AI Integration
- **Model:** Claude Sonnet 4.5 (or configurable)
- **API:** Anthropic Python SDK
- **Prompt:** Structured prompt with JD + transcript + calibration data

### CSV Handling
- Parse calibration CSV for LinkedIn URLs
- Store URLs for reference (enrichment out of scope)
- For this PRD, just store the URLs — no scraping

---

## Success Criteria

### Functional
- [ ] Can upload JD (PDF/DOCX/text)
- [ ] Can upload intake transcript
- [ ] Can upload calibration candidates CSV
- [ ] AI generates 3 must-have criteria from inputs
- [ ] Generated criteria follow the quality requirements
- [ ] User can review and edit all criteria fields
- [ ] User can add/delete criteria
- [ ] Criteria are saved to database per role
- [ ] Saved criteria can be viewed and re-edited

### Quality
- [ ] Generated criteria are specific to the role (not generic)
- [ ] Generated criteria are testable against LinkedIn data
- [ ] Calibration candidates would pass the generated criteria
- [ ] Criteria use language from JD and intake transcript

---

## Story Breakdown

### Story 1: Document Upload Backend
- API endpoints for uploading JD, transcript, CSV
- Document parsing (PDF, DOCX, text)
- Store extracted text in database
- **Acceptance:** Upload a PDF JD → text extracted and stored

### Story 2: Document Upload UI
- File upload components on role page
- Drag-drop or file picker
- Upload progress indicator
- Display uploaded document names
- **Acceptance:** User can upload 3 document types via UI

### Story 3: Database Schema for Criteria
- Create role_documents table
- Create role_criteria table
- Migration script
- **Acceptance:** Tables created, can insert/query

### Story 4: Criteria Generation Prompt
- Design and test the AI prompt
- Input: JD text + transcript text + calibration URLs
- Output: 3 structured criteria (JSON)
- **Acceptance:** Prompt returns well-formed criteria for test inputs

### Story 5: Criteria Generation API
- Endpoint: POST /api/roles/{id}/generate-criteria
- Calls AI with uploaded documents
- Returns generated criteria
- **Acceptance:** API returns criteria JSON from uploaded docs

### Story 6: Criteria Review UI
- Display generated criteria as editable cards
- Edit name, description, rules
- Add/delete criteria
- **Acceptance:** User can view and modify all criteria fields

### Story 7: Save Criteria
- Save button persists criteria to database
- Update existing or insert new
- **Acceptance:** Saved criteria retrievable on page reload

### Story 8: View Saved Criteria
- Display saved criteria for a role
- Edit and re-generate buttons
- **Acceptance:** Returning to role shows saved criteria

---

## Future Enhancements (Out of Scope)

- Nice-to-have criteria support
- Candidate enrichment (LinkedIn scraping)
- Criteria-based candidate evaluation
- Bulk role criteria templates
- Criteria performance analytics

---

## Open Questions

1. Should we scrape calibration candidate LinkedIn profiles for better pattern analysis? (Currently out of scope — just storing URLs)

2. Should there be a "criteria library" of common heuristics that can be reused across roles?

3. How do we handle JDs that are vague or missing key requirements? (AI makes best attempt, human reviews)
