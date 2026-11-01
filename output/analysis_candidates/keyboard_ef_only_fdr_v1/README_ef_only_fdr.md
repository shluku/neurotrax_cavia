# Executive Function-only FDR reanalysis — v1

## Status

This is a **post-hoc, domain-specific exploratory FDR** analysis. The original 204-test longitudinal BH-FDR remains the primary multiplicity analysis. These results do not establish confirmatory evidence because Executive Function was selected after review of the broader discovery results.

## Source and completeness

- Source: `output/analysis_candidates/keyboard_deep_dive_v1/signal_discovery/signal_feature_associations.csv`
- Complete original slice: 34 features tested against Executive Function change.
- Valid p-values: 34/34.
- Excluded for statistical significance: 0.
- No p-values, correlations, sample sizes, feature definitions, or historical outputs were changed.
- BH was independently recomputed and verified programmatically.

## Main result

Restricting BH to the 34 Executive Function hypotheses yields the following strongest rows:

                                 feature_name  spearman_rho  n  spearman_p    fdr_q  ef_only_bh_q
  keyboard_median_correction_recovery_time_ms     -0.588710 32    0.000394 0.080284      0.013381
keyboard_12_18_median_inter_event_interval_ms      0.592856 28    0.000885 0.090318      0.015053
             keyboard_inter_event_interval_cv     -0.513035 33    0.002265 0.154031      0.025672
keyboard_18_24_median_inter_event_interval_ms      0.523645 29    0.003554 0.181256      0.030209
keyboard_06_12_median_inter_event_interval_ms      0.484677 31    0.005723 0.194589      0.038918
      keyboard_median_inter_event_interval_ms      0.439840 33    0.010428 0.265909      0.050649
                         keyboard_active_days     -0.435368 35    0.008950 0.260822      0.050649
     keyboard_median_post_correction_pause_ms      0.416789 32    0.017642 0.399896      0.074980

The complete ordered table is `ef_only_fdr_all_34_tests.csv`. The three requested headline rows are in `ef_only_fdr_headline_comparison.csv`. The five Executive Function longitudinal rows represented in the research-summary selected signal set are in `research_summary_executive_function_rows.csv`.

Interpretation must retain the distinction between the original 204-test q-value and this post-hoc 34-test domain-specific q-value. The new q-values are useful for transparent sensitivity analysis, not for upgrading the discoveries to confirmatory findings.
