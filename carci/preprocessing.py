from __future__ import annotations

import pandas as pd

from carci.schema import detect_columns


def preprocess_cur_data(df: pd.DataFrame) -> pd.DataFrame:
    cols = detect_columns(df)

    prepared = pd.DataFrame(
        {
            "date": pd.to_datetime(df[cols.date], errors="coerce").dt.date,
            "service": df[cols.service].fillna("Unknown Service").astype(str),
            "region": (
                df[cols.region].fillna("Unknown Region").astype(str)
                if cols.region
                else "Unknown Region"
            ),
            "resource": (
                df[cols.resource].fillna("Unknown Resource").astype(str)
                if cols.resource
                else "Unknown Resource"
            ),
            "usage_type": (
                df[cols.usage_type].fillna("Unknown Usage Type").astype(str)
                if cols.usage_type
                else "Unknown Usage Type"
            ),
            "cost": pd.to_numeric(df[cols.cost], errors="coerce").fillna(0.0),
        }
    )

    prepared = prepared.dropna(subset=["date"]).copy()
    prepared["date"] = pd.to_datetime(prepared["date"])
    prepared = prepared[prepared["cost"] >= 0].copy()

    if prepared.empty:
        raise ValueError("The uploaded CSV does not contain valid date/cost rows after preprocessing.")

    return prepared
