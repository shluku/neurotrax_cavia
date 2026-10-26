import json

import pandas as pd

from keyboard_deep_dive import canonical_events, group_features


def raw_row(ts: int, before: str, current: str, device: str = "d1", package: str = "p"):
    return {
        "timestamp": ts,
        "device_id": device,
        "data": json.dumps({"before_text": before, "current_text": current, "package_name": package, "is_password": "false"}),
    }


def test_valid_intervals_never_exceed_canonical_observations():
    events, duplicates, parse_errors = canonical_events([
        raw_row(1_000, "", "a"),
        raw_row(2_000, "a", "ab"),
        raw_row(3_000, "ab", "abc"),
    ])
    features = group_features(events)
    assert duplicates == 0
    assert parse_errors == 0
    assert features["keyboard_distinct_observation_count"] == 3
    assert features["keyboard_valid_interval_count"] == 2
    assert features["keyboard_valid_interval_count"] <= features["keyboard_distinct_observation_count"]


def test_duplicates_are_removed_before_interval_counting():
    rows = [raw_row(1_000, "", "a"), raw_row(2_000, "a", "ab"), raw_row(2_000, "a", "ab"), raw_row(3_000, "ab", "abc")]
    events, duplicates, _ = canonical_events(rows)
    features = group_features(events)
    assert duplicates == 1
    assert features["keyboard_distinct_observation_count"] == 3
    assert features["keyboard_valid_interval_count"] == 2


def test_multiple_streams_still_cannot_create_more_intervals_than_events():
    rows = [
        raw_row(1_000, "", "a", device="d1", package="p1"),
        raw_row(2_000, "a", "ab", device="d1", package="p1"),
        raw_row(1_500, "", "x", device="d2", package="p2"),
        raw_row(2_500, "x", "xy", device="d2", package="p2"),
    ]
    events, _, _ = canonical_events(rows)
    features = group_features(events)
    assert features["keyboard_distinct_observation_count"] == 4
    assert features["keyboard_valid_interval_count"] == 2
