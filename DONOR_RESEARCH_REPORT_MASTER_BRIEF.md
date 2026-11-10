# Dementia Digital Phenotyping — Donor Research Report: Master Brief and Evidence Protocol

**Status:** Planning reference v1 — 2026-11-10  
**Audience:** research donors, scientific collaborators, project investigators  
**Purpose:** Create a comprehensive, evidence-traceable and accessible narrative of the full research program, from its earliest database work to the latest analyses. This document is the specification for the report, **not the report itself**.

## 1. What the user wants

Produce a complete but disciplined account of a substantial research effort: what question motivated it; how data were acquired and organized; how candidate smartphone features were conceived, extracted, screened, retained or rejected; which **published studies specifically motivated each feature**; what statistical and machine-learning analyses were conducted; what was learned and validated; what failed or was inconclusive; and what remains before any clinical claim.

The report should demonstrate the **scope, rigor, and cumulative value** of the work, and explain how an initially broad feature search progressively narrowed to a small set of interpretable candidates. It should be **objective, donor-readable, clinically accurate, and not padded with trivial debugging, dead-end commands, or unrelated experiments**. Significant findings must be described at the right evidence level.

We will build this through a staged, roughly one-month collaborative research-documentation effort. Do not assume work runs autonomously between sessions.

## 2. Non-negotiable editorial rules

1. **Never invent evidence.** Every result must trace to a saved output, code version, sample, and analytic specification. Every paper must be bibliographically verified and linked to the exact feature it supports.
2. **Distinguish:** published precedent; our original/modified feature definition; hypothesis; observed association; technical feasibility; adjusted sensitivity; independent validation; clinical utility.
3. **Literature provenance is feature-specific.** A generic digital-health paper is not sufficient proof that a particular metric was derived from it. If we cannot establish historical provenance, label it 'retrospective scientific support', not 'paper originally used to select the feature'. If no credible support exists, label 'novel exploratory definition / evidence gap'.
4. **No selective statistical narration.** Preserve original screening multiplicity, EF-only post-hoc FDR, sample sizes, direction, p/q, confidence intervals where saved, and sensitivity to recording/device effects. Do not claim the EF-only q<0.05 is independent confirmation.
5. **Do not interpret snapshots as physical keypresses, smartphone movement as gait/tremor, or incomplete logging as inactivity.** Cognitive score changes overlapping feature windows do not establish prospective prediction.
6. **Separate engineering accomplishments from clinical discoveries.** Large data volume, a large feature bank, many tests and working sensor joins do not themselves imply predictive success.
7. **Show substantial labor through meaningful workstreams and reproducible artifacts**, not through excessive chronological command logs or thousands of repetitive tables.
8. **Protect participants.** No row-level text, identifiers, raw message content, secrets, or individual case reconstruction in donor materials. Check permissions before sharing repository paths or exports.
9. **Avoid 'retrofit' certainty.** The literature audit may uncover papers now that were not used at original feature-selection time.
10. **Version the report and the evidence ledger.** Record the date of the frozen evidence snapshot; any later analysis belongs in an update.

## 3. Verified starting points in the local repository (initial reconnaissance only)

Repository folder: `/Users/ofirfizitsky/PycharmProjects/research_dbeaver`  
Git remote: `https://github.com/shluku/neurotrax_cavia.git`

**Important:** A reconnaissance of paths, not a complete file-by-file audit, has been performed as of this brief. Further validation is required.

- `README_PROJECT_HANDOFF.md`, `PROJECT_HANDOFF_20261101.md`, `README_CURRENT_PROJECT_STATUS.md`, and historical phase protocol files.
- `streamlit_app.py`, `README_STREAMLIT_APP.md`, and related feature dashboards: source for historical analytical presentation and potentially selection rationale. Streamlit is a **viewer**, not automatically the canonical evidence ledger. Verify which page, version, and source files support each statement.
- `manuscript/study_protocol.md`, `manuscript/draft_v01.md`, `manuscript/analysis_decisions.md`, `manuscript/evidence_register.csv`, `manuscript/references.md`, and `manuscript/tables/`.
- `manuscript/tables/complete_feature_dictionary_20261021_v1.csv`; `complete_feature_cognitive_associations_20261021_v1.csv`; source inventories and saved review chronology.
- `output/cognitive_master/`; `output/analysis_candidates/`; `output/research_summary_20261025/`; code scripts, tests, and checkpoint manifests.
- `output/analysis_candidates/keyboard_ef_only_fdr_v1/` and `statistical_multiplicity_audit_v1/`.
- Cross-modal, ACC, language/lexical, machine-learning, PCA and data-coverage workstreams.
- Historical Word documents in root, including `Dementia_Digital_Phenotyping_Project_Summary.docx` and `Executive_Function_Keyboard_FDR_Summary.docx`: secondary communication artifacts, not substitutes for original result tables.
- `manuscript/references.md` is explicitly a **working** references list; some entries are methodological analogies rather than origins of a specific feature. All citations require validation.

## 4. Proposed donor report structure

### A. Executive narrative (1–2 pages)
Clinical/scientific opportunity, what we set out to learn, scale and diversity of passive data, what the team built, key candidate associations, rigorous negative/robustness findings, current evidence level, and next milestones. A donor should understand the journey without interpreting every statistical acronym.

### B. Clinical question, cohort and observational design
Population and enrollment, NeuroTrax T1/T2 domains, missingness, time alignment, index definitions, early/late windows, data collection setting, ethics/privacy context (only if documented), and limitations of inferred behavior. Resolve differing historical cohort counts using dated source files rather than choosing a convenient figure.

### C. Data architecture and engineering
MySQL SensorDB tables, device-to-patient mapping, timestamps, timezone, privacy exclusions, SQL extraction, checkpointing, archive/Parquet workflows, sensor/hardware audit, Streamlit tools, QC and reproducibility. Describe the data-volume claims only if measurable evidence exists.

### D. Feature development history — the main body
For each **feature family** and each retained/high-priority feature, answer:
- Clinical construct and research motivation
- Original publication used (if demonstrable), exact feature definition in paper, DOI and population
- What our specific raw tables can measure
- Algorithmic extraction, units, observation window, exclusions, minimum signal/event thresholds
- Changes between versions, technical limitations and missingness
- Selection/retention/defer/rejection reasoning and date
- Analyses and validation actually run, results, residual uncertainty

Organize by: keyboard cadence/intervals; correction/deletion/text growth and reconstructed word completion; lexical diversity/word-length-aware measures; screen and touch; foreground apps and switching; calls/messages/telephony; GPS/connectivity/social/communications; activity recognition and accelerometer/motion; and genuinely cross-table event-linked interactions. Only include families actually evidenced in repository.

### E. Statistical discovery and evidence hierarchy
All major analysis scopes, family sizes, p-values, BH-FDR, permutation/multiplicity audit, technical and demographic adjustments, bootstrap and sensitivity windows, subject retention, feature quality thresholds, differences between discovery and post-selection results. A clear table of a few flagship results with n, rho/effect, p, q, adjusted outcome, and interpretation.

### F. Unsupervised and predictive modeling
PCA/clusters, feature scaling and coverage confounding, Ridge/Elastic Net and baseline comparisons, correct CV and corrected historical alignment errors, optimism/certainty, why prediction is not clinically validated.

### G. Validation and alternative branches
Repeatability, days/thirds sensitivity, app/device sampling effects, missingness selection, MATTR-100 checks, cross-modal ACC/Touch/Apps/Keyboard pilots, sensor metadata, bounded query and rate QC, results that did not generalize. Group related versions into coherent lessons, not eleven repetitive paragraphs on phases 1–11.

### H. What has been established, what has not, and what comes next
Clearly separate reliable technical infrastructure, exploratory statistical observations, insufficiently validated digital biomarkers, future reproducibility/confirmation and clinically meaningful applications. Provide a feasible prioritized roadmap and decisions donors can understand.

### I. Appendices and source traceability
Concise chronology, full feature-to-paper-to-code-to-output matrix, primary statistical table, QA/multiplicity provenance, literature references, methods and reproducibility notes. The body remains readable and not overlong; appendices hold audit detail.

## 5. Mandatory master evidence registers

Build these intermediate machine-readable files **before** drafting outcome claims:

1. `SOURCE_INVENTORY.csv`: path, file class, version/date, role, scope, patient-level vs aggregate, status, authoritative/derived, sensitivity flags, last verified.
2. `RESEARCH_CHRONOLOGY.csv`: milestone/date, question, tools, outputs, result, lesson/decision, evidence paths.
3. `FEATURE_PROVENANCE_LEDGER.csv`: feature ID/version; exact formula; unit; raw source; window; eligibility; paper originally used (verified or unknown); supporting paper found later; DOI/PMID; published exact definition vs inspiration; implementation code; QC; status.
4. `LITERATURE_VERIFICATION.csv`: citation, publication year, DOI, verification status, study population, instruments/sensors, exact feature, actual result, scope of relevance, supported claim, limitations, linked feature IDs.
5. `ANALYSIS_EVIDENCE_LEDGER.csv`: analysis ID, hypothesis, patient n, cohort, original selection scope, feature, outcome, rho/effect, p, q/family, CI, adjustment, sensitivity, reproducibility, interpretation, source path.
6. `VALIDATION_AND_FAILURE_REGISTER.csv`: hypothesis/feature, test type, criteria, results, pass/fail/inconclusive, technical vs scientific explanation, future action.
7. `REPORT_CLAIM_AUDIT.csv`: paragraph/claim ID, exact supporting evidence path and citation, verification status, reviewer notes, approved wording.

Each ledger needs explicit `not_checked`, `missing`, `verified`, `uncertain` statuses; no blanks silently interpreted as favorable evidence.

## 6. Known preliminary quantitative anchors — VERIFY AGAINST ORIGINAL TABLES

- Historical cognitive cohort approximately 83 subjects; approximately 81 with T1 Global and up to approximately 61 paired T1/T2, varying by version/eligibility.
- Feature dictionary: 1,246 definition-version entries / 496 unique names, which are not 496 validated behavioral biomarkers.
- Comprehensive historical association register: 2,560 saved estimates, including repeated/post-hoc analyses rather than 2,560 independent hypotheses.
- Original keyboard discovery screen: 34 features × 6 outcomes × T1 and longitudinal scopes = 408 tests; 204 in the longitudinal scope.
- EF-specific exploratory post-hoc BH across the full set of 34 EF-change hypotheses yielded five q<0.05: correction recovery, afternoon IEI, IEI CV, evening IEI, morning IEI. Source: `keyboard_ef_only_fdr_v1/`.
- The original 204-test FDR did not confirm those findings at q<0.05; technical adjustment attenuated the afternoon IEI result. Preserve this distinction in comprehensive donor reporting.
- Lexical reconstruction / MATTR and word timing produced exploratory but coverage-sensitive signals.
- Ridge/Elastic Net models have not demonstrated dependable improvement over baseline with independent external validation.
- Cross-table synchronization and short-episode feature extraction were technically demonstrated, but ACC×Touch/keyboard longitudinal signals remain coverage-limited.

These are **starting checkpoints**, not a substitute for an audit of the underlying files.

## 7. Literature tracing methodology

1. Search internal protocols, Streamlit source/data, feature dictionaries, code comments, archived notes, literature files, commit history, and research discussions for citations and historical selection reasons.
2. For each candidate paper, verify title/authors/year/DOI and consult original methods/results; do not infer feature precedent from paper title alone.
3. Categorize paper-to-feature relationship: `direct operational reproduction`, `adapted methodology`, `conceptual support only`, `retrospective support`, `no validated supporting precedent`.
4. Differentiate disease/population specificity (dementia/MCI vs depression/healthy adults/mixed cohorts).
5. Cite a paper for a specific claim only when that claim is supported by it. Where a feature was newly invented, describe it as a hypothesis and retain novelty, rather than fabricating an origin.
6. If multiple studies justify one family, cite the strongest directly applicable publications and briefly explain limitations in transferring the methods.

## 8. Work plan for iterative sessions (approximately four weeks)

**Week 1: evidence inventory and historical reconstruction.** Audit repository and Streamlit page by page; discover hidden artifacts, data sources, feature dictionary, chronological decisions, outstanding missing files and sensitive material. Freeze version and produce inventory/chronology and open questions.

**Week 2: feature/provenance and literature verification.** Trace every retained or investigated major family to original code and known historical paper, conduct focused external literature search for unsupported families, assemble reproducible feature-to-paper mapping and a narrative selection funnel.

**Week 3: results, validation and statistics.** Reconcile cohort/sample counts, compute the final selected evidence table only from verified outputs, audit original FDR vs domain-only follow-up, summarize model validation, confounding tests and negative results. Identify what was technically validated versus statistically or clinically validated.

**Week 4: donor report and scientific review.** Draft accessible long-form report with concise executive summary, feature selection flow, source-linked findings and method figures if useful; internally fact-check claims against ledgers; refine language for clinical accuracy, ethics and donor audience. Prepare Word/PDF only when requested for the final report.

## 9. Acceptance criteria for final report

- Every quoted number can be located in an original source output and is labeled with its cohort, time window and analysis version.
- Every claimed literature-derived feature has verified feature-specific source support; gaps are stated.
- All major scientific workstreams and meaningful engineering/analysis achievements are represented without exhaustive irrelevant debugging.
- The story explicitly shows the evolution from many candidate ideas to a small set of promising, qualified signals, including reasons for non-retention.
- Negative experiments, QC failures and technical corrections are presented fairly, as evidence of rigor rather than hidden.
- Exploratory statistical significance is not misrepresented as validated clinical or predictive performance.
- Donor-facing prose is readable; detailed tables and full citation traceability remain in appendices.
- No participant-sensitive content is released.

## 10. Immediate next action

Perform a **read-only comprehensive repository/Streamlit inventory** and build the first three ledgers. In particular, locate any feature-by-feature citations or selection rules embedded in Streamlit or its backing tables, and explicitly mark original citations that cannot be recovered. Do not begin writing the final donor narrative until inventory completeness is assessed.

**Decision to remember:** This project needs an evidence-based research history and scientific provenance audit first, a polished donor summary second.
