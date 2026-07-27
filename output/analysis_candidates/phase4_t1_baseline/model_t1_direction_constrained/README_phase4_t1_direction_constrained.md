# Phase 4 Direction-Constrained T1 Ridge

This is a separate exploratory model using the same fold-local eight-feature slope selection as the slope-selected model. Positive-slope features have coefficients constrained to be nonnegative; negative-slope features have coefficients constrained to be nonpositive. Missingness indicators are unconstrained. The ridge penalty is selected by inner cross-validation.

Pooled mean-baseline RMSE: `8.532`

Pooled direction-constrained ridge RMSE: `9.094`
