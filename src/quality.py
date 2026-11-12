"""Data quality report: how complete the hourly table is."""

import pandas as pd

# Minimum completeness for each grade, best first.
GRADES = (("A", 0.98), ("B", 0.90), ("C", 0.75))


def grade_for(completeness: float) -> str:
    """Letter grade for a completeness fraction: A >= 98 %, B >= 90 %, C >= 75 %, else D."""
    for grade, minimum in GRADES:
        if completeness >= minimum:
            return grade
    return "D"


def _longest_run(flags: pd.Series) -> int:
    """Length of the longest run of True values."""
    if not flags.any():
        return 0
    run_id = (flags != flags.shift()).cumsum()
    return int(flags.groupby(run_id).sum().max())


def quality_report(df: pd.DataFrame) -> dict:
    """Summarise how complete the hourly power data is.

    An hour counts as present only if both IT power and total facility
    power have a value. Hours missing from the table entirely (between the first and
    last timestamp) count as missing too.

    Returns ``{completeness, missing_hours, longest_gap_h, grade}``.
    """
    if df.empty:
        return {"completeness": 0.0, "missing_hours": 0, "longest_gap_h": 0, "grade": "D"}

    present = df.set_index("ts")[["it_kw", "total_kw"]].notna().all(axis=1)
    present = present.groupby(level=0).any()  # guard against duplicate timestamps
    grid = pd.date_range(present.index.min(), present.index.max(), freq="h")
    missing = ~present.reindex(grid, fill_value=False)

    completeness = 1 - missing.mean()
    return {
        "completeness": float(completeness),
        "missing_hours": int(missing.sum()),
        "longest_gap_h": _longest_run(missing),
        "grade": grade_for(completeness),
    }
