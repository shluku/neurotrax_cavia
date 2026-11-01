# Top-15 interpretation and limitations draft

## Results interpretation

The frozen primary exploratory association was the change in afternoon (12:00–18:00) snapshot-derived inter-event interval and change in Executive Function. The association was positive in the discovery analysis (Spearman ρ=.593, n=28, q=.090) and remained positive after adjustment for age, sex, education, baseline Executive Function, recording-rate change, valid-interval-rate change, and device change where available (partial ρ=.508, p=.022, q=.133). The corrected first/last-thirds estimate was directionally consistent but imprecise (partial ρ=.496, p=.071, q=.836). This pattern supports the signal as a technically qualified hypothesis for future validation, not as a confirmed behavioral or clinical biomarker.

The other five prespecified longitudinal keyboard signals showed related exploratory associations with Executive Function or Attention and were retained as secondary analyses. Their value is comparative: they provide a coherent timing-feature panel with shared adjustment, leave-one-patient-out, permutation, reliability, and alternate-window outputs. Several attenuated after recording adjustment, and corrected-thirds intervals were generally wide. The panel therefore supports feasibility of patient-level longitudinal analysis more strongly than it supports a single stable cognitive mechanism.

The remaining nine top-15 findings are supplementary sensitivity analyses. They include restricted-window results, baseline word-completion associations, a morning inter-event-interval variability association, and legacy trimmed T1 rows. Focused recording-density adjustment did not uniformly eliminate these associations, but their small cohorts, post hoc window selection, incomplete reliability evidence, and reconstructed testing context limit interpretation. They should be presented as exploratory observations rather than independent confirmations.

The keyboard timing variables are derived from intervals between recorded text-state snapshots. They are not direct keypress timestamps and may reflect recording cadence, application behavior, synchronization, edits, pauses, and other features of data capture in addition to user behavior. A positive or negative association should therefore not be translated directly into faster or slower motor or cognitive performance. In particular, changes in active days or snapshot volume are recording-availability measures and should not be described as behavioral timing features.

The correlation analyses and the cross-validated Ridge/Elastic Net analyses answer different questions. Correlations quantify patient-level association between a feature and a cognitive measure; predictive models quantify out-of-sample performance relative to a fold-matched mean baseline. The two evidence types should be reported in separate sections and should not be combined into a single claim of predictive validity.

## Limitations

First, the study is exploratory and retrospective. The top-15 display is a selected evidence set assembled from a broader search history. Its q-values retain source-specific testing families or are explicitly reconstructed within a stated family; they do not provide project-wide false-discovery control.

Second, participant numbers are small for several candidate-specific analyses, particularly the restricted-window results. Confidence intervals and bootstrap intervals are consequently wide, and apparent effect-size differences may be unstable. The absence of an interval crossing zero is not, by itself, evidence of robustness.

Third, recording coverage varies across participants and time. Active days, snapshot counts, and valid interval counts can influence whether a feature is observed and how precisely it is estimated. Recording-density adjustment reduces but does not remove this concern. Device or application changes were not available in every reconstructed cohort, and the remaining technical confounding cannot be excluded.

Fourth, the longitudinal windows and restricted analyses are not interchangeable. Window selection, minimum-coverage thresholds, and availability of paired observations affect the estimand and the eligible participants. The restricted-window results should therefore not be interpreted as direct replications of the primary POC.

Fifth, the measurement semantics are limited. Snapshot-derived inter-event intervals do not establish keystroke timing, and word-completion timing has additional continuity, paste/prediction, edit-state, and boundary limitations. These variables are digital traces with incomplete behavioral interpretation, not validated laboratory measures.

Sixth, reliability evidence is uneven. The six prespecified signals have saved reliability and robustness outputs, but the remaining nine rows do not have the same leave-one-out, outlier, permutation, test–retest, or alternate-window evidence. No finding has an independent participant cohort, temporal holdout, or external replication.

Finally, the current predictive analyses remain exploratory. Some saved pipelines were not fully nested with respect to all preprocessing and feature-selection decisions, and the principal 10-day model window is concurrent with the cognitive assessment rather than a prospective prediction interval. A confirmatory study should freeze participants, features, windows, covariates, preprocessing, and evaluation metrics before examining outcomes, then test the hypothesis in independent participants.

## Reporting classification

For the main article, report the afternoon 12:00–18:00 IEI/Executive Function change association as the sole exploratory POC, show the six-signal forest as the secondary technical-evidence panel, and place the remaining nine findings in supplementary tables and figures. Use language such as “candidate association,” “exploratory signal,” and “snapshot-derived proxy.” Avoid “validated biomarker,” “direct typing speed,” “clinical diagnostic,” or causal language.
