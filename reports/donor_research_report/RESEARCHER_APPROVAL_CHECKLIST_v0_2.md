# Researcher Review Queue — Donor Report v0.2

**Date:** 2026-11-10  
**Purpose:** Ask only questions that require the principal researcher's historical knowledge or scientific judgment. All other computable tasks should be handled from repository evidence first.

## A. Literature used during feature selection

The repository already contains a cross-modal literature register and a lexical literature file. We verified that the two ABOARD abstracts with DOI `10.1002/alz.071350` (N=16, 2023) and `10.1002/alz.086452` (N=40, 2024 supplement/first online 2025) are both first-authored by **Keijzer** (Twose is a coauthor of the earlier article).

For each family below, mark `approved_original_basis`, `not_used`, or `needs_discussion` in the CSV approval worksheet. An approved paper will be cited straightforwardly as a study used in constructing the feature rationale; no 'retrospective' description will appear in the donor report.

1. **Keyboard timing / irregularity:** Did the original feature selection draw on Keijzer 2023, Keijzer 2024/25, Ning 2023, other papers, or a combination? Which ones correspond to IEI, CV, correction recovery and circadian windows?
2. **Word completion and lexical richness:** Which papers motivated word-timing, MATTR, MTLD and word-length-adjusted metrics? Candidates recorded in the repo include Covington & McFall 2010, McCarthy & Jarvis 2010, the 2020 MCI touchscreen/language study.
3. **Touch, screen, applications, calls and social context:** Which papers were read and retained for each original feature family? This mapping is not yet recovered for the complete bank.
4. **Activity recognition, accelerometers and multimodal coupling:** Which papers informed basic physical-activity features versus later session-aligned motion/keyboard or motion/touch interactions?

Do not collapse a conceptual inspiration into 'exact metric copied from paper'. The report can still cite the paper as a foundation while documenting our different implementation.

## B. Cohort and scope decisions

5. **Population definition:** Confirm the study population (diagnostic composition, inclusion/exclusion criteria, site, recruitment period and ethics/consent). The technical record alone does not establish these clinical facts.
6. **Priority manuscript:** Choose the first paper's principal question: (i) methods/feasibility of an auditable digital phenotype, (ii) longitudinal keyboard change and Executive Function, or another primary focus. A methods report for donors may cover all branches even if future manuscripts separate them.
7. **Results narrative:** For publication-grade interpretation, confirm whether EF is a primary endpoint in a **new prespecified study**. Its post-hoc selection in the completed exploratory screen cannot be rewritten as prospective.

## C. Release and figures

8. **Data governance and sharing:** Decide what can be included in public donor materials versus private scientific supplements (patient-level data are not copied into this report).
9. **Clinical emphasis:** Decide which prospective clinical use case is most meaningful: cognitive-change monitoring, quality-of-life/functional change, or early identification of impairment. No current tool is externally validated.

## D. Tasks for the research assistant without further approval

- Complete exact source and definition mapping for all 42 Deep Dive rows.
- Construct subject/device/window eligibility and data-exposure audit without patient data release.
- Verify remaining paper titles and exact methods from the source literature; present candidate mappings for approval.
- Harmonize original and post-hoc FDR without silently replacing either.
- Reproduce historical predictive performance and uncertainty only from validated fold-level files.
- Propose and stage additional plots and targeted calculation protocols; execute only scientifically specified analyses with versioned outputs.

## Next editorial gate

**No need to answer every question at once.** The first actionable review session should cover A1–A2 (keyboard and language literature), plus B5 (clinical cohort description). These affect the strongest current donor narrative and its scientific validity.
