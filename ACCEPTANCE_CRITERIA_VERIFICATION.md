# Acceptance Criteria Verification Guide

**Purpose:** How Ralph verifies each acceptance criterion without human input

---

## Verification Methods Ralph Can Use

1. **Database Check:** Query SQLite to verify tables/records exist
2. **File Check:** Verify file exists at expected path
3. **API Test:** curl endpoint, check status code and response format
4. **Browser Test:** Use dev-browser skill to navigate and interact
5. **Code Check:** Verify function exists and has correct signature
6. **Unit Test:** Run pytest or similar automated test

---

## Story-by-Story Verification

### US-000A: Database Schema ✅

**How Ralph Verifies:**
1. Read tasks/us-000a-database-schema.md → Get SQL
2. Run SQL script → Create tables
3. Query: `SELECT name FROM sqlite_master WHERE type='table'` → Verify 7 tables
4. Query: `PRAGMA foreign_key_list(roles)` → Verify foreign keys
5. Try invalid enum: `INSERT INTO roles VALUES ('x', 'X', 'invalid_status', ...)`  → Should fail
6. Query: `PRAGMA index_list(roles)` → Verify indexes exist

**Pass condition:** All tables exist, constraints work, no SQL errors

---

### US-001A: Role CRUD Backend ✅

**How Ralph Verifies:**
```bash
# Start Flask
python webapp/main.py &

# Test POST
curl -X POST http://localhost:5000/api/roles \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","description":"Desc"}' | jq '.id'
# → Should return 201 with UUID

# Test GET list
curl http://localhost:5000/api/roles | jq 'length'
# → Should return array with ≥1 role

# Test GET single
curl http://localhost:5000/api/roles/{id} | jq '.name'
# → Should return "Test"

# Test PUT
curl -X PUT http://localhost:5000/api/roles/{id} \
  -d '{"name":"Updated"}' | jq '.name'
# → Should return "Updated"

# Test DELETE (soft)
curl -X DELETE http://localhost:5000/api/roles/{id}
sqlite3 data.db "SELECT status FROM roles WHERE id='{id}'"
# → Should return "archived"
```

**Pass condition:** All endpoints return expected status codes and data

---

### US-001B: Role Management UI ✅

**How Ralph Verifies (via dev-browser):**
```python
# 1. Navigate to /roles
browser.goto("http://localhost:5000/roles")
assert browser.text_content("h1") == "Roles"

# 2. Click Create Role
browser.click("button:has-text('Create Role')")
assert browser.is_visible("dialog")  # Modal appears

# 3. Fill form
browser.fill("input[name='name']", "Test Role")
browser.fill("textarea[name='description']", "Test Description")
browser.click("button:has-text('Save')")

# 4. Verify new role appears
assert browser.is_visible("text=Test Role")

# 5. Click Archive
browser.click("button:has-text('Archive')")
assert not browser.is_visible("text=Test Role")  # Role gone
```

**Pass condition:** All 5 steps execute without errors, assertions pass

---

### US-001C: Document Upload Backend ✅

**How Ralph Verifies:**
```bash
# Create test file
echo "test content" > /tmp/test.pdf

# Upload file
curl -X POST http://localhost:5000/api/roles/{id}/files \
  -F "file=@/tmp/test.pdf" \
  -F "file_type=jd" | jq '.filename'
# → Should return "test.pdf" with 201

# Verify file stored
ls /uploads/roles/{id}/test.pdf
# → File should exist

# Verify database
sqlite3 data.db "SELECT filename FROM uploaded_files WHERE role_id='{id}'"
# → Should return "test.pdf"

# Test invalid file type
curl -X POST http://localhost:5000/api/roles/{id}/files \
  -F "file=@/tmp/test.exe" \
  -F "file_type=jd"
# → Should return 400 Bad Request

# Delete file
curl -X DELETE http://localhost:5000/api/files/{file_id}
# → Should return 200
ls /uploads/roles/{id}/test.pdf
# → File should NOT exist
```

**Pass condition:** File upload/delete works, validation rejects invalid types

---

### US-001D: Document Upload UI ✅

**How Ralph Verifies (via dev-browser):**
```python
# 1. Navigate to role detail
browser.goto(f"http://localhost:5000/roles/{role_id}")

# 2. Drag file to dropzone (simulate upload)
browser.set_input_files("input[type='file'][data-type='jd']", "/tmp/test.pdf")

# 3. Verify file appears
assert browser.is_visible("text=test.pdf")
assert browser.is_visible("text=14 bytes")  # File size

# 4. Click delete
browser.click("button[data-file-id='{file_id}']")
assert not browser.is_visible("text=test.pdf")

# 5. Upload invalid file
browser.set_input_files("input[type='file'][data-type='jd']", "/tmp/test.exe")
assert browser.is_visible("text=Invalid file type")  # Error message
```

**Pass condition:** File upload UI works, shows files, deletes, validates types

---

### US-001E: AI Criteria Extraction ✅

**How Ralph Verifies:**
```bash
# Upload test JD file
curl -X POST http://localhost:5000/api/roles/{id}/files \
  -F "file=@test_jd.pdf" -F "file_type=jd"

# Trigger extraction
curl -X POST http://localhost:5000/api/roles/{id}/extract-criteria | jq

# Verify response format
{
  "must_haves": [{"id": "mh_1", "description": "...", "type": "..."}],
  "gating_parameters": [{"id": "gp_1", "rule": "...", ...}],
  "nice_to_haves": [{"id": "nth_1", "description": "..."}]
}

# Test error handling: call with no files uploaded
curl -X POST http://localhost:5000/api/roles/{new_id}/extract-criteria
# → Should return {"must_haves": [], "gating_parameters": [], "nice_to_haves": [], "error": "..."}
```

**Pass condition:** Returns structured JSON with arrays, handles missing files

---

### US-001F: Criteria Configuration Form ✅

**How Ralph Verifies (via dev-browser):**
```python
# 1. Load criteria page
browser.goto(f"http://localhost:5000/roles/{role_id}/criteria")

# 2. Verify 3 sections exist
assert browser.is_visible("h2:has-text('Must-Haves')")
assert browser.is_visible("h2:has-text('Gating Parameters')")
assert browser.is_visible("h2:has-text('Nice-to-Haves')")

# 3. Add must-have
browser.click("button:has-text('Add Must-Have')")
browser.fill("input[name='must_have_new']", "Python 5+ years")

# 4. Check gating param
browser.check("input[value='job_hopper']")

# 5. Save
browser.click("button:has-text('Save Criteria')")

# 6. Verify database
result = sqlite3("SELECT criteria_data FROM criteria_versions WHERE role_id='{id}'")
criteria = json.loads(result)
assert "Python 5+ years" in str(criteria['must_haves'])
assert any(g['rule'] == 'job_hopper' and g['enabled'] for g in criteria['gating_parameters'])
```

**Pass condition:** Form works, saves to database with correct structure

---

### US-005A: LinkedIn Profile Fetching ✅

**How Ralph Verifies:**
```python
# 1. Call function
from filtering.enrichment import fetch_linkedin_profile

result = fetch_linkedin_profile("https://www.linkedin.com/in/some-public-profile")

# 2. Verify return format
assert result['status'] == 'success'
assert 'html' in result
assert len(result['html']) > 1000  # Has content
assert 'fetched_at' in result

# 3. Verify database storage
record = sqlite3("SELECT raw_data FROM enriched_candidates WHERE linkedin_url='...'")
assert record is not None

# 4. Test error cases
result_404 = fetch_linkedin_profile("https://www.linkedin.com/in/nonexistent-profile-xyz")
assert result_404['status'] == 'not_found'

# 5. Test with real URL
result_real = fetch_linkedin_profile("https://www.linkedin.com/in/williamhgates")
assert 'William' in result_real['html'] or result_real['status'] in ['not_found', 'rate_limit', 'requires_login']
```

**Pass condition:** Function exists, returns correct format, handles errors

---

### US-005B: LinkedIn Data Extraction ✅

**How Ralph Verifies:**
```python
# 1. Create function
from filtering.enrichment import extract_linkedin_data

# 2. Test with sample HTML
sample_html = """<div class="profile">
  <h1>John Doe</h1>
  <div class="headline">Senior Engineer at Google</div>
  <div class="experience">
    <li>Software Engineer at Microsoft (2020-2022)</li>
  </div>
  <div class="education">Stanford University, BS Computer Science</div>
  <div class="skills">Python, JavaScript, React</div>
</div>"""

result = extract_linkedin_data(sample_html)

# 3. Verify extracted fields
assert result['current_title'] is not None and len(result['current_title']) > 0
assert result['current_company'] is not None
assert len(result['job_history']) >= 1
assert result['job_history'][0]['title'] is not None
assert result['job_history'][0]['company'] is not None
assert len(result['education']) >= 1
assert result['education'][0]['school'] is not None
assert len(result['skills']) > 0

# 4. Test missing fields
empty_html = "<html><body></body></html>"
result_empty = extract_linkedin_data(empty_html)
assert result_empty['current_title'] is None or result_empty['current_title'] == ""
assert result_empty['job_history'] == []
```

**Pass condition:** Extracts all fields, handles missing data gracefully

---

### US-005C: Enrichment Caching ✅

**How Ralph Verifies:**
```python
from filtering.enrichment import get_enriched_candidate
import time

url = "https://www.linkedin.com/in/test-profile"

# 1. First fetch (cache miss)
result1 = get_enriched_candidate(url)
assert result1['source'] == 'fresh'

# 2. Second fetch immediately (cache hit)
result2 = get_enriched_candidate(url)
assert result2['source'] == 'cache'
assert result2['data'] == result1['data']

# 3. Test stale cache
# Manually set fetched_at to 31 days ago
sqlite3(f"UPDATE enriched_candidates SET fetched_at=datetime('now', '-31 days') WHERE linkedin_url='{url}'")

result3 = get_enriched_candidate(url, max_age_days=30)
assert result3['source'] == 'fresh'  # Re-fetched because stale

# 4. Verify index exists
indexes = sqlite3("PRAGMA index_list(enriched_candidates)")
assert any('linkedin_url' in str(idx) for idx in indexes)
```

**Pass condition:** Caching works, respects max_age, uses index

---

### US-002A: Random Candidate Selection ✅

**How Ralph Verifies:**
```python
# 1. Upload test CSV with 100 candidates
csv_content = "name,email,linkedin\n" + "\n".join([f"Person{i},p{i}@test.com,url{i}" for i in range(100)])
with open('/tmp/test.csv', 'w') as f:
    f.write(csv_content)

# 2. Trigger test run
response = requests.post(f'http://localhost:5000/api/roles/{role_id}/test', 
                        files={'csv': open('/tmp/test.csv')})
test_run_id = response.json()['test_run_id']
selected = response.json()['selected_candidates']

# 3. Verify 50 selected
assert len(selected) == 50

# 4. Verify stored in database
record = sqlite3(f"SELECT candidate_ids FROM test_runs WHERE id='{test_run_id}'")
stored_ids = json.loads(record)
assert len(stored_ids) == 50

# 5. Second test run with same criteria_version_id
response2 = requests.post(f'http://localhost:5000/api/roles/{role_id}/test', 
                         files={'csv': open('/tmp/test.csv')})
selected2 = response2.json()['selected_candidates']

# Verify same test_run_id reused
assert response2.json()['test_run_id'] == test_run_id
assert selected2 == selected  # Same candidates
```

**Pass condition:** Selects 50, stores in DB, reuses same set on repeat

---

### US-002B: Test Run Processing ✅

**How Ralph Verifies:**
```python
# 1. Create test run (from US-002A)
# 2. Process candidates
response = requests.post(f'http://localhost:5000/api/runs/{test_run_id}/process')

# 3. Wait for completion
while True:
    status = requests.get(f'http://localhost:5000/api/runs/{test_run_id}/status').json()
    if status['status'] == 'completed':
        break
    time.sleep(2)

# 4. Verify results stored
results = sqlite3(f"SELECT * FROM filter_results WHERE run_id='{test_run_id}'")
assert len(results) == 50  # All candidates processed

# 5. Verify each result has required fields
for result in results:
    assert result['final_determination'] in ['Proceed', 'Human Review', 'Dismiss', 'Unable to Enrich']
    assert result['criteria_evaluations'] is not None
    evals = json.loads(result['criteria_evaluations'])
    for criteria_id, evaluation in evals.items():
        assert evaluation['result'] in ['Pass', 'Fail', 'Unsure']
        assert len(evaluation['reason']) > 10  # Has reasoning

# 6. Verify counts updated
run = sqlite3(f"SELECT * FROM filter_runs WHERE id='{test_run_id}'")
assert run['proceed_count'] + run['review_count'] + run['dismiss_count'] + run['unable_to_enrich_count'] == 50
```

**Pass condition:** All candidates processed, results have correct format, counts match

---

### US-002C: Test Results UI ✅

**How Ralph Verifies (via dev-browser):**
```python
# Prerequisites: US-002B completed, test results exist

# 1. Navigate to results page
browser.goto(f"http://localhost:5000/runs/{test_run_id}/results")
assert browser.text_content("h1") == "Test Results"

# 2. Verify table with 50 rows
rows = browser.query_selector_all("table tbody tr")
assert len(rows) == 50

# 3. Click on Pass cell, check tooltip
browser.hover("td.pass")
assert browser.is_visible(".tooltip")  # Tooltip with reasoning

# 4. Filter by Proceed
browser.click("button:has-text('Proceed')")
rows_filtered = browser.query_selector_all("table tbody tr")
assert len(rows_filtered) < 50  # Some filtered out
for row in rows_filtered:
    assert "Proceed" in browser.text_content(row)

# 5. Export CSV
browser.click("button:has-text('Export to CSV')")
downloads = browser.wait_for_download()
assert downloads['filename'].endswith('.csv')

# 6. Click Approve & Run
browser.click("button:has-text('Approve & Run')")
assert browser.url() == f"http://localhost:5000/roles/{role_id}/run-options"
```

**Pass condition:** All 5 browser checks pass

---

### US-003: Full/Subset Run ✅

**How Ralph Verifies (via dev-browser + API):**
```python
# 1. Navigate to run options
browser.goto(f"http://localhost:5000/roles/{role_id}/run-options")

# 2. Verify 2 options shown
assert browser.is_visible("input[value='full']")
assert browser.is_visible("input[value='subset']")

# 3. Select subset, enter 20
browser.check("input[value='subset']")
browser.fill("input[name='subset_count']", "20")

# 4. Start run
browser.click("button:has-text('Start Run')")

# 5. Verify progress indicator
assert browser.is_visible("text=/Processing \\d+\\/20/")

# 6. Poll database to verify incremental updates
for i in range(10):
    run_record = sqlite3(f"SELECT current_candidate FROM filter_runs WHERE id='{run_id}'")
    if run_record['current_candidate'] > 0:
        break  # Progress happening
    time.sleep(1)
assert run_record['current_candidate'] > 0

# 7. Wait for completion
browser.wait_for_url(f"**/runs/{run_id}/results")  # Redirects when done

# 8. Verify final state
final_run = sqlite3(f"SELECT * FROM filter_runs WHERE id='{run_id}'")
assert final_run['status'] == 'completed'
assert final_run['completed_at'] is not None
assert final_run['current_candidate'] == 20
```

**Pass condition:** Run completes, progress updates, redirects to results

---

### US-004A: Results Data Model & API ✅

**How Ralph Verifies:**
```bash
# 1. GET all results
curl "http://localhost:5000/api/runs/{run_id}/results" | jq

# 2. Filter by determination
curl "http://localhost:5000/api/runs/{run_id}/results?filter=Proceed" | jq 'length'
# → Only Proceed candidates

# 3. Sort by name
curl "http://localhost:5000/api/runs/{run_id}/results?sort=name" | jq '.[0].candidate_name'
# → Should be alphabetically first

# 4. Paginate
curl "http://localhost:5000/api/runs/{run_id}/results?offset=10&limit=5" | jq 'length'
# → Should return exactly 5 results

curl "http://localhost:5000/api/runs/{run_id}/results?offset=10&limit=5" | jq '.total'
# → Should return total count

# 5. Verify all fields present
curl "http://localhost:5000/api/runs/{run_id}/results" | jq '.[0] | keys'
# → Should include: name, email, linkedin, criteria_evaluations, final_determination

# 6. Performance test with 1000 candidates
# (If test CSV had 1000 candidates)
time curl "http://localhost:5000/api/runs/{run_id}/results?filter=Proceed"
# → Should complete in <1 second (indexes working)
```

**Pass condition:** All query params work, pagination correct, fast queries

---

### US-004B: Results Display UI ✅

**How Ralph Verifies (via dev-browser):**
```python
# 1. Navigate to results
browser.goto(f"http://localhost:5000/runs/{run_id}/results")

# 2. Verify table displays
rows = browser.query_selector_all("table tbody tr")
assert len(rows) > 0
assert browser.is_visible("th:has-text('Name')")
assert browser.is_visible("th:has-text('Email')")

# 3. Expand row
browser.click("tr[data-candidate-id='0'] button.expand")
assert browser.is_visible(".criteria-detail")
assert browser.is_visible("text=Must-Have 1:")

# 4. Filter by Dismiss
browser.click("button[data-filter='Dismiss']")
filtered_rows = browser.query_selector_all("table tbody tr:visible")
for row in filtered_rows:
    assert "Dismiss" in browser.text_content(row)

# 5. Sort by name
browser.click("th:has-text('Name')")
first_name = browser.text_content("tbody tr:first-child td:nth-child(1)")
# Click again (reverse sort)
browser.click("th:has-text('Name')")
last_name = browser.text_content("tbody tr:first-child td:nth-child(1)")
assert first_name != last_name  # Sorting changed order

# 6. Check pagination (if >100 results)
if len(rows) > 100:
    assert browser.is_visible("button:has-text('Next')")
    browser.click("button:has-text('Next')")
    assert browser.url().endswith("?page=2")

# 7. Verify counts
count_text = browser.text_content(".result-summary")
assert "Proceed:" in count_text
assert "Human Review:" in count_text
```

**Pass condition:** All UI interactions work, data displays correctly

---

### US-004C: Results Export ✅

**How Ralph Verifies (via dev-browser):**
```python
# 1. Click export button
browser.goto(f"http://localhost:5000/runs/{run_id}/results")
browser.click("button:has-text('Export to CSV')")

# 2. Verify download
downloads = browser.wait_for_download()
csv_path = downloads['path']

# 3. Check filename format
assert downloads['filename'].startswith("results_")
assert downloads['filename'].endswith(".csv")
assert role_name.replace(' ', '_') in downloads['filename']

# 4. Parse CSV and verify structure
import csv
with open(csv_path) as f:
    reader = csv.DictReader(f)
    rows = list(reader)
    
    # Verify columns
    assert 'name' in reader.fieldnames
    assert 'email' in reader.fieldnames
    assert 'linkedin_url' in reader.fieldnames
    assert 'final_determination' in reader.fieldnames
    # Should have criteria columns like MustHave1_Result, MustHave1_Reason
    assert any('_Result' in f for f in reader.fieldnames)
    assert any('_Reason' in f for f in reader.fieldnames)
    
    # Verify data
    assert len(rows) > 0
    assert all(row['final_determination'] in ['Proceed', 'Human Review', 'Dismiss', 'Unable to Enrich'] for row in rows)

# 5. Test filtered export
browser.click("button[data-filter='Proceed']")  # Filter to Proceed only
browser.click("button:has-text('Export to CSV')")
downloads2 = browser.wait_for_download()
with open(downloads2['path']) as f:
    rows2 = list(csv.DictReader(f))
    assert all(row['final_determination'] == 'Proceed' for row in rows2)
```

**Pass condition:** CSV downloads, has all columns, respects filters

---

### US-006: Refine Criteria ✅

**How Ralph Verifies (via dev-browser):**
```python
# 1. Navigate to role detail
browser.goto(f"http://localhost:5000/roles/{role_id}")
assert browser.is_visible("button:has-text('Edit Criteria')")

# 2. Click Edit Criteria
browser.click("button:has-text('Edit Criteria')")
assert browser.url().endswith("/criteria")

# 3. Verify form pre-populated with current criteria
current_criteria = sqlite3(f"SELECT criteria_data FROM criteria_versions WHERE role_id='{role_id}' ORDER BY created_at DESC LIMIT 1")
criteria_json = json.loads(current_criteria['criteria_data'])
first_must_have = criteria_json['must_haves'][0]['description']
assert browser.input_value("input[name='must_have_0']") == first_must_have

# 4. Modify a must-have
browser.fill("input[name='must_have_0']", "Updated: " + first_must_have)
browser.click("button:has-text('Save Criteria')")

# 5. Verify new version created
versions = sqlite3(f"SELECT version, criteria_data FROM criteria_versions WHERE role_id='{role_id}' ORDER BY version DESC")
assert len(versions) >= 2  # Old + new
assert versions[0]['version'] == versions[1]['version'] + 1  # Incremented

# 6. Verify old version still exists (not deleted)
old_version = json.loads(versions[1]['criteria_data'])
assert old_version['must_haves'][0]['description'] == first_must_have

# 7. Verify new version has update
new_version = json.loads(versions[0]['criteria_data'])
assert "Updated:" in new_version['must_haves'][0]['description']
```

**Pass condition:** Form loads, saves new version, old version retained

---

### US-007: View Run History ✅

**How Ralph Verifies (via dev-browser):**
```python
# Prerequisites: At least 2 runs completed for this role

# 1. Navigate to role detail
browser.goto(f"http://localhost:5000/roles/{role_id}")
assert browser.is_visible("h2:has-text('Run History')")

# 2. Verify list shows runs
runs_list = browser.query_selector_all(".run-history-item")
assert len(runs_list) >= 2

# 3. Verify sorted by date (newest first)
dates = [browser.text_content(f".run-history-item:nth-child({i}) .date") for i in range(1, len(runs_list)+1)]
# Dates should be in descending order
from datetime import datetime
parsed_dates = [datetime.fromisoformat(d) for d in dates]
assert parsed_dates == sorted(parsed_dates, reverse=True)

# 4. Verify run details shown
first_run = browser.query_selector(".run-history-item:first-child")
assert browser.is_visible(".run-type", scope=first_run)  # test/full/subset
assert browser.is_visible(".criteria-version", scope=first_run)
assert browser.is_visible(".candidate-count", scope=first_run)
assert browser.is_visible(".result-breakdown", scope=first_run)  # X Proceed, Y Review, etc.

# 5. Click on run
run_id_to_check = browser.get_attribute(".run-history-item:first-child", "data-run-id")
browser.click(".run-history-item:first-child")

# 6. Verify navigates to results page for that run
browser.wait_for_url(f"**/runs/{run_id_to_check}/results")
assert browser.text_content("h1") == "Results"

# 7. Go back, test export from historical run
browser.go_back()
browser.click(".run-history-item:nth-child(2) button:has-text('Export')")
downloads = browser.wait_for_download()
assert downloads['filename'].endswith('.csv')
```

**Pass condition:** History displays, sorted correctly, navigation works, export works

---

## Summary: How Ralph Knows It's Done

**For each story, Ralph can verify success by:**
1. Running the explicit commands/tests in acceptance criteria
2. Checking database state matches expected
3. Verifying API endpoints respond correctly
4. Using dev-browser to confirm UI behavior
5. Testing error conditions work as expected

**Ralph does NOT rely on:**
- ❌ Human judgment ("looks good")
- ❌ Vague terms ("works properly")
- ❌ External references ("per FR-3")
- ❌ Ambiguous success ("gracefully", "accurate")

**Every acceptance criterion now has:**
- ✅ Concrete verification method
- ✅ Expected output specified
- ✅ Testable without human input
- ✅ Clear pass/fail condition

---

## If Ralph Gets Stuck

**Symptom:** Story keeps failing after multiple iterations

**Diagnosis:**
1. Check `scripts/ralph/progress.txt` for what it tried
2. Look at git commits on `ralph/ai-filtering` branch
3. See which acceptance criterion it can't satisfy

**Fix:**
- Criterion genuinely impossible? Update prd.json to be more realistic
- Criterion unclear? Add more specific verification steps
- Environment issue? Check Flask is running, database exists, etc.

**Then restart Ralph** - it will resume from the failed story.
