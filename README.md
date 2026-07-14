# IS 6533 Steel Chimney Design Tool — Web Edition

Veda Engineering internal tool. Ported from the Excel/VBA tool, carrying
forward every fix validated against the Kurkumbh 32m chimney (14 Jul 2026):
shell geometry length-order & taper-per-length fixes, and the per-zone
ladder/platform projected-width fix in wind loads.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Opens at http://localhost:8501

## Deploy for free (Streamlit Community Cloud)

1. Push this folder to a GitHub repo (can be private)
2. Go to https://share.streamlit.io, sign in with GitHub
3. Click "New app", pick the repo, set the main file to `app.py`
4. Deploy — you'll get a public `*.streamlit.app` URL in ~2 minutes

## Current scope (v1)

- ✅ Inputs, editable zone table
- ✅ Shell Geometry
- ✅ Static Wind Loads
- ⬜ Natural Frequency, Gust Factor, Dynamic Analysis, Seismic,
  Combined Stress, Base Foundation/Chair, Flange Design — not yet ported

## Validated against

Kurkumbh 32m chimney (Dynastac report, 08/01/2025) — shell weight matches
to <0.03%, wind loads match to <0.1% per zone.
