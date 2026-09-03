from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SpanSpec:
    key: str
    description: str
    t1_rule: str
    t2_rule: str
    fallback_rule: str


SPAN_SPECS = {
    "phase4_24h": SpanSpec(
        key="phase4_24h",
        description="Phase 4 exploratory 24-hour T1/T2 span",
        t1_rule="reuse the documented Phase 4 selected T1 window",
        t2_rule="reuse the documented Phase 5 selected pre-T2 window",
        fallback_rule="preserve the source cohort's explicit fallback or missing status",
    ),
    "phase7_10day": SpanSpec(
        key="phase7_10day",
        description="Phase 7 availability-anchored 10-day span",
        t1_rule="first available anchor after T1 followed by 10 days",
        t2_rule="latest available anchor before T2 followed backward by 10 days",
        fallback_rule="preserve the Phase 7 30-day search and status labels",
    ),
    "phase11_12_midpoint": SpanSpec(
        key="phase11_12_midpoint",
        description="Patient-specific T1/T2 midpoint interval",
        t1_rule="[T1, patient midpoint)",
        t2_rule="[patient midpoint, T2)",
        fallback_rule="T1-only patients use [T1, T1+123 days) for the T1 side",
    ),
    "phase111_full_interval": SpanSpec(
        key="phase111_full_interval",
        description="Full T1-to-T2 interval",
        t1_rule="[T1, T2)",
        t2_rule="[T1, T2) when T2 exists",
        fallback_rule="T1-only patients use [T1, T1+123 days)",
    ),
}
