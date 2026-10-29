"""Future-version resource guards; frozen HGB v1 is not modified or rerun."""
from dataclasses import dataclass

NUMERIC_TARGETS = {"pass_yd","pass_td","pass_cmp","pass_att","pass_int","rush_yd","rush_att","rec","rec_yd","rush_rec_yd"}


def expected_output_views(queries, history_arms=3):
    if type(history_arms) is not int or history_arms < 1:
        raise ValueError("positive integer history arm count required")
    result = 0
    for query in queries:
        target = query["target"]
        if target in NUMERIC_TARGETS:
            result += 2*history_arms
        elif target == "anytime_td":
            result += history_arms
        else:
            raise ValueError("unsupported target cannot consume an invented product")
    return result


@dataclass
class OutputViewBudget:
    limit: int
    reserved: int = 0

    def __post_init__(self):
        if type(self.limit) is not int or self.limit < 1 or type(self.reserved) is not int or not 0 <= self.reserved <= self.limit:
            raise ValueError("invalid output allocation")

    def reserve(self, rows):
        """Charge every planned output, including abstentions, before its fit."""
        if type(rows) is not int or rows < 0:
            raise ValueError("nonnegative integer output row count required")
        if self.reserved + rows > self.limit:
            raise RuntimeError("FORECAST_ROW_BUDGET")
        self.reserved += rows

