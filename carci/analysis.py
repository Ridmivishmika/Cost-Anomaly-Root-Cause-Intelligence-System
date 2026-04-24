from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import shap
from sklearn.ensemble import IsolationForest

from carci.preprocessing import preprocess_cur_data


def _safe_pct_change(current_value: float, previous_value: float) -> float:
    if previous_value <= 0 and current_value > 0:
        return 100.0
    if previous_value <= 0:
        return 0.0
    return ((current_value - previous_value) / previous_value) * 100.0


def _to_breakdown(df: pd.DataFrame, column: str) -> List[Dict]:
    total_cost = float(df["cost"].sum())
    grouped = (
        df.groupby(column, dropna=False)["cost"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
        .rename(columns={column: "name"})
    )
    grouped["share_pct"] = np.where(total_cost > 0, (grouped["cost"] / total_cost) * 100.0, 0.0)
    grouped["cost"] = grouped["cost"].round(2)
    grouped["share_pct"] = grouped["share_pct"].round(2)
    return grouped.to_dict(orient="records")


def _build_service_root_cause_text(service_record: Dict) -> str:
    change_direction = "increased" if service_record["percentage"] >= 0 else "decreased"
    change_pct = abs(service_record["percentage"])
    return (
        f"A significant cost spike was detected on {service_record['display_date']}.\n\n"
        f"The total cost {change_direction} by approximately {change_pct:.0f}% compared to the normal value.\n\n"
        f"The anomaly was primarily caused by increased {service_record['service_name']} usage "
        f"in the {service_record['region']} region."
    )


def _build_service_comparison(df: pd.DataFrame) -> List[Dict]:
    all_services = sorted(df["service"].dropna().astype(str).unique().tolist())

    feature_columns = [
        "cost",
        "previous_cost",
        "pct_change",
        "rolling_mean_3",
        "rolling_std_3",
        "cost_delta",
        "z_score",
        "day_of_week",
    ]

    rows: List[Dict] = []
    for service_name in all_services:
        service_rows = (
            df.loc[df["service"] == service_name, ["date", "cost", "region", "resource", "usage_type"]]
            .sort_values(["date", "cost"], ascending=[True, False])
            .reset_index(drop=True)
        )
        service_series = _build_daily_features(service_rows[["date", "cost"]], aggregate_by_date=False)

        if len(service_series) >= 2 and service_series["cost"].nunique() > 1:
            scored_rows = _run_isolation_forest(service_series, feature_columns)
            scored_rows = scored_rows.copy()
            scored_rows["impact_value"] = (scored_rows["cost"] - scored_rows["rolling_mean_3"]).abs()
            scored_rows["priority_score"] = scored_rows["anomaly_score"] * scored_rows["impact_value"].clip(lower=1.0)
            anomaly_row = scored_rows.sort_values(
                ["priority_score", "impact_value", "cost"],
                ascending=[False, False, False],
            ).iloc[0]
            anomaly_value = float(anomaly_row["cost"])
            anomaly_date = pd.Timestamp(anomaly_row["date"])
        else:
            anomaly_row = service_series.sort_values(["cost", "date"], ascending=[False, False]).iloc[0]
            anomaly_value = float(anomaly_row["cost"])
            anomaly_date = pd.Timestamp(anomaly_row["date"])

        anomaly_source_row = service_rows.iloc[int(anomaly_row.name)]
        normal_series = service_series.drop(index=anomaly_row.name)["cost"]
        normal_value = float(normal_series.mean()) if not normal_series.empty else 0.0
        impact_value = float(anomaly_value - normal_value)
        percentage = round(_safe_pct_change(anomaly_value, normal_value), 2)
        region_name = str(anomaly_source_row.get("region", "Unknown Region"))
        display_date = anomaly_date.strftime("%d %B %Y")

        service_record = {
            "service_name": service_name,
            "date": anomaly_date.strftime("%Y-%m-%d"),
            "display_date": display_date,
            "region": region_name,
            "resource": str(anomaly_source_row.get("resource", "Unknown Resource")),
            "usage_type": str(anomaly_source_row.get("usage_type", "Unknown Usage Type")),
            "anomaly_value": round(anomaly_value, 2),
            "normal_value": round(normal_value, 2),
            "percentage": percentage,
            "impact_value": round(impact_value, 2),
        }
        service_record["root_cause_analysis"] = _build_service_root_cause_text(service_record)
        rows.append(service_record)

    comparison = pd.DataFrame(rows)
    comparison = comparison.sort_values(
        ["impact_value", "anomaly_value", "percentage", "service_name"],
        ascending=[False, False, False, True],
    )
    return comparison.to_dict(orient="records")


def _build_daily_features(df: pd.DataFrame, aggregate_by_date: bool = True) -> pd.DataFrame:
    if aggregate_by_date:
        daily = df.groupby("date", as_index=False)["cost"].sum().sort_values("date").reset_index(drop=True)
    else:
        daily = df[["date", "cost"]].copy().sort_values(["date", "cost"], ascending=[True, False]).reset_index(drop=True)
    daily["previous_cost"] = daily["cost"].shift(1).fillna(0.0)
    daily["pct_change"] = [
        _safe_pct_change(curr, prev) for curr, prev in zip(daily["cost"], daily["previous_cost"])
    ]
    daily["rolling_mean_3"] = daily["cost"].rolling(window=3, min_periods=1).mean()
    daily["rolling_std_3"] = daily["cost"].rolling(window=3, min_periods=1).std(ddof=0).fillna(0.0)
    daily["cost_delta"] = daily["cost"] - daily["previous_cost"]
    daily["day_of_week"] = pd.to_datetime(daily["date"]).dt.dayofweek.astype(float)

    mean_cost = float(daily["cost"].mean())
    std_cost = float(daily["cost"].std(ddof=0))
    daily["z_score"] = 0.0 if std_cost == 0 else (daily["cost"] - mean_cost) / std_cost

    return daily


def _select_contamination(num_rows: int) -> float:
    if num_rows <= 5:
        return 0.34
    if num_rows <= 10:
        return 0.25
    return 0.15


def _run_isolation_forest(daily: pd.DataFrame, feature_columns: List[str]) -> pd.DataFrame:
    model_input = daily[feature_columns].astype(float)
    contamination = _select_contamination(len(daily))

    model = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=42,
    )
    model.fit(model_input)

    daily = daily.copy()
    daily["if_prediction"] = model.predict(model_input)
    daily["if_decision_score"] = model.decision_function(model_input)
    daily["anomaly_score"] = -daily["if_decision_score"]

    try:
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(model_input)
        shap_frame = pd.DataFrame(shap_values, columns=feature_columns, index=daily.index)
    except Exception:
        centered = model_input - model_input.mean()
        centered = centered.replace([np.inf, -np.inf], 0.0).fillna(0.0)
        shap_frame = centered.copy()
        total_abs = shap_frame.abs().sum(axis=1).replace(0.0, 1.0)
        shap_frame = shap_frame.div(total_abs, axis=0).mul(daily["anomaly_score"].abs(), axis=0)

    for column in feature_columns:
        daily[f"shap_{column}"] = shap_frame[column]

    return daily


def _get_feature_contributions(row: pd.Series, feature_columns: List[str]) -> Tuple[List[Dict], List[str]]:
    feature_rows = []
    for column in feature_columns:
        shap_value = float(row.get(f"shap_{column}", 0.0))
        feature_rows.append(
            {
                "feature": column,
                "feature_value": round(float(row[column]), 4),
                "shap_value": round(shap_value, 4),
                "impact_strength": round(abs(shap_value), 4),
            }
        )

    feature_rows.sort(key=lambda item: item["impact_strength"], reverse=True)
    top_features = [item["feature"] for item in feature_rows[:3]]
    return feature_rows, top_features


def build_analysis_result(raw_df: pd.DataFrame) -> Dict:
    df = preprocess_cur_data(raw_df)
    service_comparison = _build_service_comparison(df)
    return {
        "service_comparison": service_comparison,
        "service_root_causes": [
            {
                "service_name": row["service_name"],
                "root_cause_analysis": row["root_cause_analysis"],
            }
            for row in service_comparison
        ],
    }
