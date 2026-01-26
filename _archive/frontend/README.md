# Candidate Triage UI - Phase 1

## Overview
Next.js-based frontend for the Candidate Triage System with drag-and-drop CSV upload, file display, and standardization pipeline integration.

## Services Running

### Backend (FastAPI)
- **URL:** http://localhost:8000
- **External:** http://34.219.151.160:8000
- **Log:** `/tmp/fastapi.log`

### Frontend (Next.js)
- **URL:** http://localhost:3000
- **External:** http://34.219.151.160:3000
- **Log:** `/tmp/nextjs.log`

## Features (Phase 1)

✅ **Implemented:**
- Role creation page
- Drag-and-drop CSV upload (multiple files)
- File display with source detection (SeekOut, Pin Wrangle, LinkedIn, etc.)
- File size display
- Remove uploaded files functionality
- Integration with FastAPI backend
- Real-time processing status updates
- Download results (proceed, human_review, dismiss, all)
- Clean, responsive UI with Tailwind CSS

## How to Access

1. **Open browser:** http://34.219.151.160:3000
2. **Click "Create New Role"**
3. **Enter role name** (e.g., "Mandrel - Founding Engineer")
4. **Drag & drop CSV files** or click to upload
5. **Click "Process & Standardize"**
6. **Monitor progress** on the role detail page
7. **Download results** when processing completes

## Technical Stack

- **Frontend:** Next.js 15, React 19, TypeScript, Tailwind CSS
- **Backend:** FastAPI, Python 3.10
- **Integration:** REST API with CORS support

## Development

### Start Services

```bash
# Backend
cd ~/clawd/candidate-triage-system
venv/bin/uvicorn webapp.main:app --host 0.0.0.0 --port 8000

# Frontend
cd ~/clawd/candidate-triage-system/frontend
npm run dev
```

### Stop Services

```bash
# Find and kill processes
pkill -f "uvicorn webapp.main:app"
pkill -f "next dev"
```

### View Logs

```bash
tail -f /tmp/fastapi.log
tail -f /tmp/nextjs.log
```

## API Endpoints

- `GET /` - Home page (HTML)
- `POST /run` - Create new run and upload CSVs
- `GET /runs/{run_id}` - Run detail page (HTML)
- `GET /api/runs/{run_id}` - Run status (JSON)
- `GET /api/runs` - List all runs (JSON)
- `GET /download/{run_id}/{kind}` - Download result files

## File Upload Flow

1. User selects role name and uploads CSV files
2. Frontend sends multipart form data to `/api/run`
3. Backend saves files, creates run, starts pipeline in background
4. Frontend redirects to `/role/{run_id}` to monitor progress
5. Page polls `/api/runs/{run_id}` every 2 seconds during processing
6. When complete, download buttons appear

## Next Steps (Phase 2+)

- [ ] Filter configuration UI
- [ ] Template save/load system
- [ ] Test run with random sampling
- [ ] Mark as wrong functionality
- [ ] Google Sheets integration
- [ ] Full evaluation workflow

## Deployment

Currently running as background processes. For production:

```bash
# Create systemd service files
sudo nano /etc/systemd/system/candidate-triage-backend.service
sudo nano /etc/systemd/system/candidate-triage-frontend.service

# Enable and start
sudo systemctl enable --now candidate-triage-backend
sudo systemctl enable --now candidate-triage-frontend
```

---

**Status:** Phase 1 Complete ✅
**Ready for testing!**
