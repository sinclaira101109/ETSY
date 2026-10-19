# First local Codex pilot

The existing FastAPI Etsy analyzer in `app.py` is not changed by this workflow.

## Local run (Windows PowerShell)

```powershell
cd ETSY
py -m pip install -r requirements.txt
New-Item -ItemType Directory -Force data\inbox
# Copy a product CSV or XLSX into data\inbox (do not commit it)
py ops_workflow.py --input data/inbox --output output --shop HoryalfTowelFlowers
py -m unittest discover -s tests -v
```

Outputs are created in `output/YYYY-MM-DD/HoryalfTowelFlowers/`:
- `sku_audit.csv` — data quality and tag checks
- `buyer_segments.csv` — buyer-targeting search draft groups
- `outreach_drafts.md` — UNSENT sample outreach email
- `report.json` — run status and skipped sheets

No live Etsy data is fetched; no LeadPilot credits are spent; no mail is sent.
Unknown facts are flagged rather than filled in. Workflows are not scheduled by default.

## Next implementation stages
- Extend real SKU mappings after inspecting the actual workbook headers.
- Add eRank import and source-date-aware competition comparisons.
- Add image audit that examines actual uploaded photo files.
- Add a human-approved review UI before activating integrations.
- Only then add supervised scheduled reporting, operational logs and alerts.
