"""Descriptive distribution of point outputs, never a forecast probability law."""
import math
import numpy as np


def point_output_profile(predictions, actuals=None):
    values = np.asarray(predictions, dtype=float)
    if values.ndim != 1:
        raise ValueError('one dimensional point outputs required')
    good = np.isfinite(values)
    finite = values[good]
    out = dict(output_rows=len(values), finite_outputs=int(good.sum()),
               unavailable_or_nonfinite_outputs=int((~good).sum()),
               zero_outputs=int((finite == 0).sum()), distinct_finite_outputs=len(np.unique(finite)),
               minimum=float(finite.min()) if len(finite) else None,
               maximum=float(finite.max()) if len(finite) else None,
               mean_point_output=float(finite.mean()) if len(finite) else None,
               point_output_frequency_not_forecast_law=True, diagnostic_not_automatic_defect=True)
    if actuals is not None:
        actual = np.asarray(actuals, dtype=float)
        if actual.shape != values.shape:
            raise ValueError('output/actual alignment required')
        admitted = good & np.isfinite(actual)
        error = values[admitted] - actual[admitted]
        out.update(paired_rows=int(admitted.sum()),
                   nonzero_actual_rows=int((actual[admitted] != 0).sum()),
                   mae=float(np.abs(error).mean()) if len(error) else None,
                   bias=float(error.mean()) if len(error) else None)
    return out
