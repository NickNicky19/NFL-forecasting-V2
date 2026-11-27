"""Exact native-point tolerances for genuine chart medians on the0.02 grid.

This repairs scoring diagnostics. It never rounds means, fits a model, changes
forecasts or claims a predictive improvement.
"""
from decimal import Decimal,InvalidOperation


def coordinate(value):
    if value is None or isinstance(value,bool):raise ValueError('finite chart value required')
    try:x=Decimal(str(value))*50
    except (InvalidOperation,ValueError):raise ValueError('finite chart value required')from None
    if not x.is_finite() or x!=x.to_integral_value():raise ValueError('value is not on the exact chart grid; never round it')
    return int(x)


def chart_median_precision(predictions,actuals,*,product_id):
    if product_id!='lower_median':raise ValueError('only authenticated grid median products; do not round mean forecasts')
    predictions=list(predictions);actuals=list(actuals)
    if len(predictions)!=len(actuals):raise ValueError('paired lengths required')
    errors=[abs(coordinate(p)-coordinate(y))for p,y in zip(predictions,actuals)]
    n=len(errors);result={}
    for tolerance in (1,5,10):
        for inclusive in (False,True):
            name=f"abs_{'le'if inclusive else'lt'}_{tolerance}"
            hits=sum(e<=50*tolerance if inclusive else e<50*tolerance for e in errors)
            result[name]=dict(numerator=hits,denominator=n,rate=hits/n if n else None)
    return result
