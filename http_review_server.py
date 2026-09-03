"""Read-only, server-rendered HTTP view of selected project outputs.

This is a companion to Streamlit for reviewers whose environment cannot run
Streamlit's browser JavaScript/WebSocket client. It intentionally exposes only
an allowlisted set of de-identified analysis outputs and never connects to SQL.
"""

from __future__ import annotations

import argparse
import html
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pandas as pd


ROOT = Path(__file__).parent
OUTPUT_ROOT = ROOT / "output/analysis_candidates"
CLINICAL_ROOT = OUTPUT_ROOT / "phase11_t1_baseline/clinical_tables_baseline_severity"
EMPIRICAL_ROOT = OUTPUT_ROOT / "phase_exploratory_empirical_findings"

DATASETS: dict[str, Path] = {
    "phase11-clinical-table1.csv": CLINICAL_ROOT / "phase11_baseline_severity_clinical_table1.csv",
    "phase11-all-features.csv": CLINICAL_ROOT / "phase11_baseline_severity_all_features.csv",
    "phase11-group-assignments.csv": CLINICAL_ROOT / "phase11_baseline_severity_group_assignments.csv",
    "empirical-feature-config.csv": EMPIRICAL_ROOT / "exploratory_empirical_feature_config.csv",
    "empirical-metrics.csv": EMPIRICAL_ROOT / "exploratory_empirical_metrics.csv",
    "empirical-patient-predictions.csv": EMPIRICAL_ROOT / "exploratory_empirical_patient_predictions.csv",
    "empirical-coefficients.csv": EMPIRICAL_ROOT / "exploratory_empirical_coefficients.csv",
}
TEXT_FILES: dict[str, Path] = {
    "phase11-protocol.md": CLINICAL_ROOT / "README_phase11_baseline_severity_tables.md",
    "empirical-protocol.md": EMPIRICAL_ROOT / "README_exploratory_empirical_findings.md",
}


def _read_csv(name: str) -> pd.DataFrame:
    path = DATASETS[name]
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def _html_table(frame: pd.DataFrame, *, hide_patient_ids: bool = True) -> str:
    if frame.empty:
        return '<p class="empty">No output is available yet.</p>'
    display = frame.copy()
    if hide_patient_ids:
        display = display.drop(
            columns=[column for column in ["Subject_ID_D", "Subject_ID_N"] if column in display],
            errors="ignore",
        )
    return display.to_html(index=False, classes="data-table", border=0, escape=True)


def _download_links(names: list[str]) -> str:
    return "<ul>" + "".join(
        f'<li><a href="/download/{html.escape(name)}">Download {html.escape(name)}</a></li>' for name in names
    ) + "</ul>"


def _page(title: str, body: str) -> bytes:
    document = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} | NeuroTrax-SensorDB</title>
<style>
body {{ margin: 0; background: #f5f7fa; color: #17202a; font: 16px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }}
main {{ max-width: 1480px; margin: 0 auto; padding: 28px 24px 64px; }}
h1 {{ margin: 0 0 6px; font-size: 30px; }} h2 {{ margin-top: 34px; font-size: 22px; }} h3 {{ margin-top: 24px; }}
p.note {{ color: #52606d; max-width: 1000px; }}
nav {{ display: flex; flex-wrap: wrap; gap: 12px; margin: 0 0 26px; }}
nav a, a.download {{ color: #075985; text-decoration: none; font-weight: 650; }}
nav a:hover, a.download:hover {{ text-decoration: underline; }}
.notice {{ background: #fff7ed; border-left: 4px solid #ea580c; padding: 12px 16px; margin: 18px 0; }}
.cards {{ display: flex; flex-wrap: wrap; gap: 12px; }}
.card {{ background: white; border: 1px solid #d9e2ec; padding: 14px 18px; min-width: 145px; }}
.card strong {{ display: block; font-size: 24px; }} .card span {{ color: #52606d; font-size: 13px; }}
.table-wrap {{ overflow-x: auto; background: white; border: 1px solid #d9e2ec; margin-top: 10px; }}
table.data-table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
table.data-table th {{ position: sticky; top: 0; background: #e8eef5; text-align: left; white-space: nowrap; }}
table.data-table th, table.data-table td {{ border-bottom: 1px solid #e5e7eb; padding: 8px 10px; vertical-align: top; }}
table.data-table tr:nth-child(even) {{ background: #f8fafc; }}
code {{ background: #e8eef5; padding: 2px 5px; }}
.empty {{ color: #7b8794; }}
</style>
</head>
<body><main>
<nav><a href="/">Home</a><a href="/phase11-clinical">Phase 11 Clinical Tables</a><a href="/exploratory-empirical">Exploratory Empirical Findings</a></nav>
{body}
</main></body></html>"""
    return document.encode("utf-8")


def _cards(items: list[tuple[str, object]]) -> str:
    return '<div class="cards">' + "".join(
        f'<div class="card"><strong>{html.escape(str(value))}</strong><span>{html.escape(label)}</span></div>'
        for label, value in items
    ) + "</div>"


def _home() -> bytes:
    body = """
<h1>NeuroTrax-SensorDB HTTP Review</h1>
<p class="note">Read-only server-rendered review pages over selected existing project outputs. This companion does not run SQL and does not replace the local Streamlit dashboard.</p>
<div class="notice"><strong>Privacy:</strong> this server is intended for de-identified outputs. Do not expose it through a public tunnel unless the cohort and files have been approved for external sharing.</div>
<h2>Available review pages</h2>
<ul>
<li><a class="download" href="/phase11-clinical">Phase 11 Clinical Tables: Baseline Cognitive Severity</a></li>
<li><a class="download" href="/exploratory-empirical">Exploratory Empirical Findings</a></li>
</ul>
<h2>Machine-readable access</h2>
<ul>
<li><a href="/api/phase11-clinical.json">Phase 11 clinical tables JSON</a></li>
<li><a href="/api/exploratory-empirical.json">Exploratory empirical outputs JSON</a></li>
</ul>
<p class="note">These pages use ordinary HTML tables, so a reviewer or automated reader does not need JavaScript, Streamlit, or WebSockets.</p>
"""
    return _page("HTTP Review", body)


def _phase11_clinical(*, hide_patient_ids: bool) -> bytes:
    clinical = _read_csv("phase11-clinical-table1.csv")
    features = _read_csv("phase11-all-features.csv")
    assignments = _read_csv("phase11-group-assignments.csv")
    cutoff = "n/a"
    lower = higher = "n/a"
    if not clinical.empty:
        cutoff_values = clinical["global_t1_median_cutoff"].dropna() if "global_t1_median_cutoff" in clinical else []
        cutoff = f"{float(cutoff_values.iloc[0]):.2f}" if len(cutoff_values) else "n/a"
        participants = clinical.loc[clinical["variable"].eq("Participants")]
        if not participants.empty:
            lower = int(participants.iloc[0]["n_lower"])
            higher = int(participants.iloc[0]["n_higher"])
    body = f"""
<h1>Phase 11 Clinical Tables: Baseline Cognitive Severity</h1>
<p class="note">Exploratory median split of observed global T1 in the Phase 11 midpoint-span cohort. This is not a validated clinical impairment classification.</p>
{_cards([("Participants", int(len(assignments)) if not assignments.empty else "n/a"), ("Lower observed T1", lower), ("Higher observed T1", higher), ("Median cutoff", cutoff), ("Digital features", int(features["feature_name"].nunique()) if not features.empty else "n/a")])}
<h2>Clinical Table 1</h2>
<p class="note">Continuous variables are shown as median (IQR); categorical variables as n (%). P-values are exploratory and FDR q-values are included for multiple-testing context.</p>
<div class="table-wrap">{_html_table(clinical, hide_patient_ids=hide_patient_ids)}</div>
<h2>All digital features</h2>
<p class="note">All measured Phase 11 digital features are included. Missing values are retained as missing and summarized with available counts.</p>
<div class="table-wrap">{_html_table(features, hide_patient_ids=hide_patient_ids)}</div>
<h2>Protocol</h2>
<pre>{html.escape(TEXT_FILES["phase11-protocol.md"].read_text(encoding="utf-8") if TEXT_FILES["phase11-protocol.md"].exists() else "No protocol available.")}</pre>
<h2>Downloads</h2>
{_download_links(["phase11-clinical-table1.csv", "phase11-all-features.csv", "phase11-group-assignments.csv"])}
"""
    return _page("Phase 11 Clinical Tables", body)


def _exploratory_empirical(*, hide_patient_ids: bool) -> bytes:
    config = _read_csv("empirical-feature-config.csv")
    metrics = _read_csv("empirical-metrics.csv")
    patients = _read_csv("empirical-patient-predictions.csv")
    coefficients = _read_csv("empirical-coefficients.csv")
    pooled = metrics.loc[metrics["analysis_scope"].astype(str).eq("pooled")] if not metrics.empty else metrics
    complete = int(patients["all_selected_features_observed"].sum()) if "all_selected_features_observed" in patients else "n/a"
    body = f"""
<h1>Exploratory Empirical Findings</h1>
<p class="note">Direction-preserving global T1 model using only the two selected keyboard-timing features. This is exploratory and hypothesis-generating.</p>
{_cards([("Patients", int(len(patients)) if not patients.empty else "n/a"), ("Selected features", int(config["feature_name"].nunique()) if not config.empty else "n/a"), ("Both features observed", complete)])}
<h2>Selected features and directions</h2>
<div class="table-wrap">{_html_table(config, hide_patient_ids=hide_patient_ids)}</div>
<h2>Pooled model comparison</h2>
<div class="table-wrap">{_html_table(pooled, hide_patient_ids=hide_patient_ids)}</div>
<h2>Patient-level predictions</h2>
<p class="note">Patient identifiers are hidden in this HTML view by default. The direct CSV download contains the stored output and should only be shared in an approved environment.</p>
<div class="table-wrap">{_html_table(patients, hide_patient_ids=hide_patient_ids)}</div>
<h2>Fold-level coefficients</h2>
<div class="table-wrap">{_html_table(coefficients, hide_patient_ids=hide_patient_ids)}</div>
<h2>Protocol</h2>
<pre>{html.escape(TEXT_FILES["empirical-protocol.md"].read_text(encoding="utf-8") if TEXT_FILES["empirical-protocol.md"].exists() else "No protocol available.")}</pre>
<h2>Downloads</h2>
{_download_links(["empirical-feature-config.csv", "empirical-metrics.csv", "empirical-patient-predictions.csv", "empirical-coefficients.csv"])}
"""
    return _page("Exploratory Empirical Findings", body)


def _json_payload(group: str) -> dict[str, object]:
    names = {
        "phase11": ["phase11-clinical-table1.csv", "phase11-all-features.csv", "phase11-group-assignments.csv"],
        "empirical": ["empirical-feature-config.csv", "empirical-metrics.csv", "empirical-patient-predictions.csv", "empirical-coefficients.csv"],
    }[group]
    return {
        name: _read_csv(name).where(lambda frame: frame.notna(), None).to_dict(orient="records") for name in names
    }


class ReviewHandler(BaseHTTPRequestHandler):
    server_version = "NeuroTraxHTTPReview/1.0"

    def _authorized(self) -> bool:
        expected = os.environ.get("HTTP_REVIEW_TOKEN", "")
        if not expected:
            return True
        supplied = self.headers.get("X-Review-Token", "")
        if supplied == expected:
            return True
        query_token = parse_qs(urlparse(self.path).query).get("token", [""])[0]
        return query_token == expected

    def _send(self, payload: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:  # noqa: N802
        if not self._authorized():
            self._send(b"Unauthorized", "text/plain; charset=utf-8", 401)
            return
        parsed = urlparse(self.path)
        route = parsed.path.rstrip("/") or "/"
        hide_patient_ids = os.environ.get("HTTP_REVIEW_SHOW_PATIENT_IDS", "0") != "1"
        if route == "/":
            self._send(_home(), "text/html; charset=utf-8")
        elif route == "/phase11-clinical":
            self._send(_phase11_clinical(hide_patient_ids=hide_patient_ids), "text/html; charset=utf-8")
        elif route == "/exploratory-empirical":
            self._send(_exploratory_empirical(hide_patient_ids=hide_patient_ids), "text/html; charset=utf-8")
        elif route == "/api/phase11-clinical.json":
            self._send(json.dumps(_json_payload("phase11"), allow_nan=False).encode("utf-8"), "application/json; charset=utf-8")
        elif route == "/api/exploratory-empirical.json":
            self._send(json.dumps(_json_payload("empirical"), allow_nan=False).encode("utf-8"), "application/json; charset=utf-8")
        elif route.startswith("/download/"):
            name = route.removeprefix("/download/")
            if name not in DATASETS or not DATASETS[name].exists():
                self._send(b"Not found", "text/plain; charset=utf-8", 404)
                return
            self._send(DATASETS[name].read_bytes(), "text/csv; charset=utf-8")
        else:
            self._send(b"Not found", "text/plain; charset=utf-8", 404)

    def log_message(self, format: str, *args: object) -> None:
        print(f"HTTP review: {format % args}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve read-only server-rendered project review pages.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address; keep 127.0.0.1 when using a tunnel.")
    parser.add_argument("--port", type=int, default=8506)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), ReviewHandler)
    print(f"HTTP review server: http://{args.host}:{args.port}")
    print("Streamlit is unchanged. Press Ctrl-C to stop this HTTP companion.")
    server.serve_forever()


if __name__ == "__main__":
    main()
