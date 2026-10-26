"""Live, read-only Streamlit view of compressed motion backup progress."""
import json
import time

import pandas as pd
import streamlit as st

from motion_backup_status import snapshot


@st.fragment(run_every="10s")
def render_motion_backup_status():
    snap = snapshot()
    if not snap["plan"]:
        st.warning("Backup plan unavailable. Check that SENSORDATA_MAIN is connected.")
        return
    service = snap["supervisor"]
    heartbeat_age = time.time() - service.get("heartbeat_unix", 0)
    if service and heartbeat_age < 120:
        status = service["status"].replace("_", " ").capitalize()
        if service["status"] == "running":
            st.success(f"Backup service running · heartbeat {heartbeat_age:.0f} seconds ago")
        elif service["status"] == "complete":
            st.success("All motion backups complete")
        else:
            st.warning(f"Backup service: {status}")
    elif service:
        st.warning("Supervisor heartbeat is stale. The last saved worker state may not reflect a running process.")
    else:
        st.info("Reading extraction checkpoints. Independent supervision is not yet reporting a heartbeat.")
    done, total = snap["completed_chunks"], snap["total_chunks"]
    st.progress(snap["fraction"], text=f"Overall verified progress: {100*snap['fraction']:.2f}% · {done:,} / {total:,} chunks")
    st.caption("Progress counts completed, verified ID-range chunks. It is not an exact percentage of rows, bytes, or remaining time. Refreshes every 10 seconds.")
    cols = st.columns(4)
    cols[0].metric("Verified compressed data", f"{snap['compressed_bytes']/1e9:.2f} GB")
    cols[1].metric("Current file written", f"{snap['active_bytes']/1e6:.1f} MB")
    cols[2].metric("Drive free", f"{snap['free_bytes']/1e9:,.0f} GB" if snap["free_bytes"] is not None else "Unavailable")
    cols[3].metric("Automatic retries", service.get("retries", 0))
    age = snap["active_write_age_seconds"]
    if age is not None:
        st.caption(f"Current file last changed {age:.0f} seconds ago. It counts toward verified progress only after export and integrity checks finish.")
    for row in snap["tables"]:
        st.progress(row["fraction"], text=f"{row['table'].replace('_', ' ').title()}: {100*row['fraction']:.2f}% · {row['completed']:,}/{row['total']:,} chunks · {row['status']}")
    eta = snap["estimated_remaining_seconds"]
    if eta is not None:
        st.caption(f"Provisional remaining time: {eta/86400:.1f} days, extrapolated from up to 20 recent completed chunks. Sensor types and ID ranges may have different rates.")
    else:
        st.caption("A measured time estimate will appear after at least three chunks complete.")
    for warning in snap["warnings"]:
        st.warning(warning)
    with st.expander("Backup details"):
        st.dataframe(pd.DataFrame(snap["tables"]), hide_index=True, use_container_width=True)
        st.json({"worker": snap["state"], "supervisor": service})
    st.download_button("Download backup status", json.dumps(snap, indent=2),
                       "motion_backup_status.json", "application/json", key="motion_backup_status_download")


def motion_backup_page():
    st.title("Raw Motion Backup")
    st.caption("Full raw archives: accelerometer → rotation → gyroscope → gravity. Source data is preserved for later Parquet conversion.")
    render_motion_backup_status()
