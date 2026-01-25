# Web UI (MVP)

This is a minimal internal web app so an operator can:
- upload one or more CSV exports
- run the pipeline (standardize/dedupe -> evaluate -> bucket)
- download outputs

## Run locally

```bash
pip install -r requirements.txt
uvicorn webapp.main:app --reload --port 8000
```

Open: http://localhost:8000

## Notes
- Requires `ANTHROPIC_API_KEY` in the environment.
- Outputs are stored under `runs/<run_name>/output/`.
- This is an MVP. No auth. Intended for localhost/internal use.
