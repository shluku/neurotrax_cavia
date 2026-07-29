# Phase 7 Comparison: 24-Hour Versus 10-Day Windows

This is a data-quality and coverage audit only. No models are run here.

## T1

Common selected features compared: `50`.
Mean feature missingness: 24-hour `38.5%`; 10-day `33.5%`.
Mean change in available features per patient: `2.53`.

## T2

Common selected features compared: `61`.
Mean feature missingness: 24-hour `76.2%`; 10-day `76.0%`.
Mean change in available features per patient: `0.16`.

## Interpretation

A wider window can improve the number of observations used to calculate a feature without increasing the number of patients who have any data in that table. Table availability and feature-level missingness must therefore be reported separately.
