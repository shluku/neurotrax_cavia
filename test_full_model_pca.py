"""Scientific invariants for window aggregation and frozen projection."""
import json
import unittest

import numpy as np
import pandas as pd

from full_model_pca import ID, TZ, aggregate_acc, availability, fit_panel, project_frozen
from unsupervised_phenotyping import _prepare_feature_matrix


class FullModelTests(unittest.TestCase):
    def test_boundaries_dst_and_multi_device(self):
        def ms(date):
            return pd.Timestamp(date, tz=TZ).timestamp()*1000
        windows = pd.DataFrame([{ID: '002', 'window_start_ms': ms('2025-03-27 12:00'),
                                 'window_end_ms': ms('2025-03-30 00:00')}]).set_index(ID)
        rows = []
        for day, device, value, minutes in [('2025-03-27', 'a', 900, 100),
                                             ('2025-03-28', 'a', 2, 50),
                                             ('2025-03-29', 'a', 4, 100),
                                             ('2025-03-29', 'b', 40, 20),
                                             ('2025-03-30', 'a', 900, 100)]:
            rows.append({'patient_id': '002', 'device_id': device, 'local_date': day, 'motion': value,
                         'accelerometer_valid_signal_minutes': minutes, 'accelerometer_valid_numeric_row_count': minutes*10,
                         'accelerometer_calendar_coverage_fraction': .1, 'accelerometer_raw_row_count': 1000,
                         'accelerometer_exact_duplicate_rows_removed': 10})
        days = pd.DataFrame(rows)
        main, audit = aggregate_acc(days, windows, ['motion'])
        self.assertEqual(main.loc['002', 'acc_median_motion'], 2)
        self.assertEqual(main.loc['002', 'acc_feature_days'], 1)
        dst_day = audit[audit.local_date.eq('2025-03-28')].iloc[0]
        self.assertEqual((dst_day.day_end-dst_day.day_start).total_seconds(), 23*3600)
        self.assertEqual((audit.reason == 'crosses_window_boundary').sum(), 1)
        self.assertEqual((audit.reason == 'multi_device_day_excluded').sum(), 2)
        other, _ = aggregate_acc(days, windows, ['motion'], policy='best_device')
        self.assertEqual(other.loc['002', 'acc_median_motion'], 3)
        self.assertEqual(other.loc['002', 'acc_duplicates_removed'], 20)

    def test_projection_roundtrip_batch_invariance_and_no_outcomes(self):
        rng = np.random.default_rng(43)
        raw = pd.DataFrame({'digital': rng.normal(5, 1, 9), 'acc_motion': np.arange(9.)**4,
                            'global_T1': np.arange(9.)}, index=pd.Index([str(i) for i in range(9)], name=ID))
        raw.loc['2', 'digital'] = np.nan
        fit = fit_panel(raw, ['digital'], ['acc_motion'])
        saved = json.dumps(fit['model'])
        model = json.loads(saved)
        scores = project_frozen(raw, model, validate=False)
        np.testing.assert_allclose(scores, fit['scores'])
        scaled, _, _ = _prepare_feature_matrix(raw[['digital','acc_motion']])
        direct = (scaled - np.array(model['pca_mean'])) @ np.array(model['components']).T
        np.testing.assert_allclose(direct, scores, atol=1e-9)
        subject = raw.iloc[[0]]
        np.testing.assert_allclose(project_frozen(subject, model), scores.iloc[[0]])
        changed = raw.copy()
        changed['global_T1'] *= -1000
        np.testing.assert_allclose(project_frozen(changed, model, validate=False), scores)
        self.assertEqual(json.dumps(model), saved)
        with self.assertRaises(ValueError):
            project_frozen(subject.drop(columns='acc_motion'), model)
        with self.assertRaises(ValueError):
            project_frozen(subject.assign(acc_motion=-1), model)
        with self.assertRaises(ValueError):
            project_frozen(subject.assign(digital=np.inf), model)

    def test_delta_missing_values_and_block_coverage(self):
        t1 = pd.DataFrame({'d1': [1], 'd2': [np.nan], 'a1': [1], 'a2': [2]})
        t2 = pd.DataFrame({'d1': [np.nan], 'd2': [2], 'a1': [3], 'a2': [4]})
        delta = t2 - t1
        self.assertTrue(delta[['d1', 'd2']].isna().all().all())
        self.assertFalse(availability(delta, ['d1', 'd2'], ['a1', 'a2']).eligible.iloc[0])


if __name__ == '__main__':
    unittest.main()
