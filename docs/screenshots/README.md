# Aegis UI Screenshots

This directory is designated for repository presentation screenshots showcasing the Aegis AI Quality & Security Platform.

### Recommended Showcase Screenshots

1. **`overview-dashboard.png`**:
   - **View**: Workspace Overview (`#overview`).
   - **Key Elements**: Aggregated evaluation statistics, average pass rate trend, security issue count, active models, recent test runs table with live pass rates and status badges, and deterministic security posture donut widget.

2. **`evaluation-runs-inspector.png`**:
   - **View**: Test Runs (`#runs`) with Run Inspector Drawer open.
   - **Key Elements**: Run execution metadata, pass rate cards, filterable case results (`passed`, `failed`, `error`), case latency in ms, prompt input/output snapshots, and evaluator metric chips.

3. **`security-dashboard.png`**:
   - **View**: Security Intelligence (`#security`).
   - **Key Elements**: Security evaluation totals, clean pass rate, 5-category breakdown cards (PII Protection, Canary Token Secrecy, Forbidden Words, Technical Safety, Policy Compliance), and recent findings table with diagnostic reasons.

4. **`version-comparison.png`**:
   - **View**: Version Compare (`#compare`).
   - **Key Elements**: Baseline vs Candidate run comparison selector, aggregate metric delta calculations, regression detection table, and latency distribution comparison.

5. **`release-quality-gate.png`**:
   - **View**: Release Quality Gate (`#quality-gate`).
   - **Key Elements**: Candidate evaluation status, automated PASS/FAIL decision banner, rule evaluation breakdown (minimum pass rate, regression drop threshold, zero-tolerance security checks, required metrics), and actionable decision reasons.

### Capture Instructions
Start the development environment:
```bash
# Terminal 1: Backend
cd backend && uvicorn app.main:app --reload

# Terminal 2: Frontend
cd frontend && npm run dev
```
Navigate to `http://localhost:5173` in a 1920x1080 browser window, capture each view using developer tools or standard screen capture, and save PNG files directly to this directory.

