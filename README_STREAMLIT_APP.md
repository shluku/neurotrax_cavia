# Streamlit Project Dashboard

Minimal local dashboard for the NeuroTrax-SensorDB dementia digital phenotyping project.

## What It Shows

- Project protocol summary
- Two main project outcomes
- Cohort-level NeuroTrax counts: total patients, T1 patients, T1+T2 patients, global-delta patients
- Cognitive patients with a mapped SensorDB device label
- Device numbers per patient
- General experiment time span from first T1 to last T2
- NeuroTrax main analysis columns and master headers
- Phase 1 phenotype profile table
- Phase 1 phenotype cards
- Phase 1 early-vs-late change profiles
- Rich Phase 1 wide table column explorer
- Phase 2 table tracking
- Phase 2 selected features source-of-truth table
- Phase 2 feature-analysis protocol
- Phase 2 table-review samples and JSON key summaries
- Phase 2 candidate feature plan, starting with `applications_foreground`
- Existing SQL table inventory
- Existing manual SQL sample summaries
- Key project file availability

The app reads existing CSV/Markdown outputs only. It does not query SQL and does not modify outputs.

## Run

Install Streamlit if needed:

```bash
.venv/bin/python3 -m pip install streamlit
```

Start the app:

```bash
.venv/bin/python3 -m streamlit run streamlit_app.py
```
