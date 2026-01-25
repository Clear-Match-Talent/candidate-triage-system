# Candidate Triage System - Deployment Status

**Date:** 2025-01-25  
**Phase:** Phase 1 - Upload & Display  
**Status:** ✅ **DEPLOYED & READY FOR TESTING**

---

## What's Live

### Frontend (Next.js)
- **URL:** http://34.219.151.160:3000
- **Status:** Running ✅
- **Port:** 3000
- **Process:** Background (nohup)
- **Log:** `/tmp/nextjs.log`

### Backend (FastAPI)
- **URL:** http://34.219.151.160:8000
- **Status:** Running ✅
- **Port:** 8000
- **Process:** Background (nohup)
- **Log:** `/tmp/fastapi.log`

---

## Phase 1 Features Completed

### ✅ Role Creation
- Clean form with role name input
- Navigation between pages
- Validation before submission

### ✅ CSV Upload Interface
- **Drag & drop** multiple files
- **Click to upload** file picker
- **File validation** (CSV only)
- **File list display** with:
  - Filename
  - File size (formatted: KB/MB)
  - Source detection (SeekOut, Pin Wrangle, LinkedIn, GitHub)
  - Remove individual files

### ✅ Backend Integration
- FastAPI with CORS support
- JSON API endpoints
- File upload handling
- Background processing

### ✅ Processing Pipeline
- Standardization (ingestion)
- AI evaluation (Claude Sonnet 4)
- Results bucketing
- Status tracking

### ✅ Results Display
- Real-time status updates (polls every 2s)
- Progress messages
- Download buttons for:
  - ✅ Proceed
  - ⚠️ Human Review
  - ❌ Dismiss
  - 📊 All Results

### ✅ UI/UX
- Modern, clean design with Tailwind CSS
- Responsive layout
- Loading states
- Error handling
- Status indicators with color coding

---

## How to Test

1. **Open:** http://34.219.151.160:3000
2. **Click:** "Create New Role"
3. **Enter:** Role name (e.g., "Test - Software Engineer")
4. **Upload:** Drag CSV files or click to select
5. **Submit:** Click "Process & Standardize"
6. **Monitor:** Watch real-time status updates
7. **Download:** Get results when processing completes

See `TEST_GUIDE.md` for detailed testing instructions.

---

## Services Management

### Check Status
```bash
# Backend
curl http://localhost:8000/ | head -20

# Frontend
curl http://localhost:3000/ | head -20

# Processes
ps aux | grep -E 'uvicorn|next' | grep -v grep
```

### View Logs
```bash
tail -f /tmp/fastapi.log    # Backend logs
tail -f /tmp/nextjs.log     # Frontend logs
```

### Restart Services

#### Backend
```bash
pkill -f "uvicorn webapp.main:app"
cd ~/clawd/candidate-triage-system
nohup venv/bin/uvicorn webapp.main:app --host 0.0.0.0 --port 8000 > /tmp/fastapi.log 2>&1 &
```

#### Frontend
```bash
pkill -f "next dev"
cd ~/clawd/candidate-triage-system/frontend
nohup npm run dev > /tmp/nextjs.log 2>&1 &
```

---

## File Locations

```
~/clawd/candidate-triage-system/
├── frontend/              # Next.js application
│   ├── app/               # Pages and layouts
│   │   ├── page.tsx       # Home page
│   │   ├── layout.tsx     # Root layout
│   │   └── role/
│   │       ├── new/
│   │       │   └── page.tsx  # Create role page
│   │       └── [id]/
│   │           └── page.tsx  # Role detail page
│   ├── components/        # React components
│   │   └── FileUpload.tsx # Drag & drop component
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.ts
│   ├── tailwind.config.ts
│   └── README.md
├── webapp/                # FastAPI backend
│   ├── main.py            # API routes
│   ├── templates/         # HTML templates (legacy)
│   └── static/            # Static files (legacy)
├── venv/                  # Python virtual environment
├── runs/                  # Processing runs output
└── requirements.txt       # Python dependencies
```

---

## Dependencies

### Frontend
- Next.js 15.5
- React 19
- TypeScript 5
- Tailwind CSS 3.4
- react-dropzone 14

### Backend
- FastAPI 0.128
- Uvicorn 0.40
- Anthropic SDK 0.76
- Python 3.10

---

## Known Limitations

### Phase 1 Scope
- ❌ No filter configuration UI (uses existing evaluate_v3.py logic)
- ❌ No template save/load
- ❌ No test run with sampling
- ❌ No Google Sheets integration
- ❌ No authentication/user management

### Technical
- RUNS state stored in-memory (lost on backend restart)
- No database persistence yet
- Background processing via threads (not production-grade)
- Logs to /tmp (cleared on reboot)

These will be addressed in future phases.

---

## Next Phases

### Phase 2: Filter Configuration (Planned)
- Structured filter form
- Paste & parse from intake form
- Template system (save/load)
- Validation

### Phase 3: Test Run (Planned)
- Random sampling (50 candidates)
- Preview results
- Mark as wrong functionality
- Approve/revise workflow

### Phase 4: Final Run & Export (Planned)
- Full evaluation
- Google Sheets integration
- Bulk downloads

### Phase 5: Production Polish (Planned)
- Systemd services
- Nginx reverse proxy
- Database persistence (SQLite)
- Error recovery
- Domain + HTTPS

---

## Production Deployment (Future)

To make this production-ready:

1. **Systemd Services**
   ```bash
   sudo systemctl enable candidate-triage-backend
   sudo systemctl enable candidate-triage-frontend
   ```

2. **Nginx Reverse Proxy**
   - Frontend on port 80/443
   - Backend proxied to /api

3. **Process Management**
   - PM2 or supervisor for Node.js
   - Systemd for Python

4. **Monitoring**
   - Health checks
   - Log rotation
   - Alerts

5. **Security**
   - HTTPS/SSL
   - Rate limiting
   - Input validation

---

## Contact & Support

**Logs:** `/tmp/fastapi.log` and `/tmp/nextjs.log`  
**Test Guide:** See `TEST_GUIDE.md`  
**Frontend README:** See `frontend/README.md`

---

**Status:** 🟢 **READY FOR TESTING**  
**URL:** http://34.219.151.160:3000

Upload some candidates and let's see it in action! 🚀
