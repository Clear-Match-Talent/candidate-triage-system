# Testing Guide - Candidate Triage UI Phase 1

## Quick Test

### 1. Access the Application
Open in browser: **http://34.219.151.160:3000**

You should see:
- Navigation bar with "Candidate Triage" branding
- "Candidate Triage System" heading
- "Create New Role" button
- Recent Roles section (empty initially)

### 2. Create a New Role

Click **"Create New Role"**

You'll see:
- Role Name input field
- Drag & drop upload zone
- Back button

### 3. Upload CSV Files

**Option A: Drag & Drop**
1. Drag one or more CSV files into the upload zone
2. Files appear in the list below with:
   - Filename
   - File size (KB/MB)
   - Detected source (SeekOut, LinkedIn, etc.)
   - Remove button

**Option B: Click to Upload**
1. Click anywhere in the upload zone
2. Select CSV files from file picker
3. Files appear in the list

**Test with sample files from:**
- `~/clawd/candidate-triage-system/test-data/`
- Or create your own test CSVs

### 4. Submit for Processing

1. Enter a role name (e.g., "Test Role - Engineer")
2. Ensure at least one CSV is uploaded
3. Click **"Process & Standardize"**
4. You'll be redirected to the processing page

### 5. Monitor Progress

The role detail page shows:
- Role name and creation time
- Status badge (QUEUED → RUNNING → DONE/ERROR)
- Progress message
- Spinning loader during processing

The page auto-refreshes every 2 seconds while processing.

### 6. Download Results

When status changes to **DONE**, you'll see download buttons:
- ✅ **Proceed** - Candidates that passed filters
- ⚠️ **Human Review** - Candidates needing review
- ❌ **Dismiss** - Rejected candidates
- 📊 **All Results** - Complete evaluation output

Click any button to download the corresponding CSV.

### 7. View Recent Roles

Return to home page (`/`) to see:
- All processed roles
- Status indicators
- Click any role to view details

## Expected Behavior

### Valid Upload
- CSV files are accepted
- Non-CSV files are ignored
- Multiple files can be uploaded
- Files can be removed before submission

### Processing
- Backend runs: standardization → evaluation → bucketing
- Status updates every 2 seconds
- Message shows current step

### Completion
- Status becomes "DONE"
- Download buttons appear
- Results are downloadable as CSV files

## Common Issues

### "Failed to create role"
- Check backend is running: `curl http://localhost:8000/`
- Check logs: `tail -f /tmp/fastapi.log`

### "Run not found"
- Backend may have restarted (RUNS dict is in-memory)
- Check backend logs for errors

### Processing stuck in "RUNNING"
- Check backend logs for Python errors
- Ensure ANTHROPIC_API_KEY is set in environment
- Check if evaluation script has issues

### Downloads don't work
- Verify files exist in `~/clawd/candidate-triage-system/runs/{run_name}/output/`
- Check backend logs for file path errors

## Testing Checklist

- [ ] Home page loads
- [ ] "Create New Role" button works
- [ ] Role name can be entered
- [ ] CSV files can be uploaded (drag & drop)
- [ ] CSV files can be uploaded (click)
- [ ] Uploaded files display correctly
- [ ] Source detection works (if filename includes keywords)
- [ ] File size displays correctly
- [ ] Remove button works
- [ ] Validation prevents empty submission
- [ ] Form submits successfully
- [ ] Redirects to role detail page
- [ ] Status updates automatically
- [ ] Processing completes successfully
- [ ] Download buttons appear when done
- [ ] Downloads work correctly
- [ ] Home page shows recent roles
- [ ] Can navigate back to role details

## Sample Test Data

If you don't have CSV files, create a simple test:

```bash
cd ~/clawd/candidate-triage-system/test-data
cat > test-seekout.csv << 'EOF'
name,email,current_company,current_title,linkedin_url,location
John Doe,john@example.com,TechCorp,Senior Engineer,https://linkedin.com/in/johndoe,"San Francisco, CA"
Jane Smith,jane@example.com,StartupXYZ,Lead Developer,https://linkedin.com/in/janesmith,"New York, NY"
EOF
```

Then upload this file through the UI.

## Logs & Debugging

### Check Backend
```bash
tail -f /tmp/fastapi.log
curl http://localhost:8000/api/runs
```

### Check Frontend
```bash
tail -f /tmp/nextjs.log
```

### Browser Console
Open browser DevTools (F12) to see:
- Network requests
- JavaScript errors
- API responses

## Success Criteria

Phase 1 is successful if:
1. ✅ User can create a new role without touching terminal
2. ✅ Multiple CSVs can be uploaded via drag & drop
3. ✅ Files are displayed with source detection
4. ✅ Processing starts automatically after submission
5. ✅ Status updates in real-time
6. ✅ Results can be downloaded when complete
7. ✅ UI is clean and responsive

---

**Ready to test!** 🚀

Open http://34.219.151.160:3000 and start uploading candidates.
