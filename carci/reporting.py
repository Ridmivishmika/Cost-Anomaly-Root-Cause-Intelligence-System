from __future__ import annotations

import pandas as pd


def _usage_hint(usage_type: str) -> str:
    usage = usage_type.lower()
    if "boxusage" in usage or "cpu" in usage or "compute" in usage:
        return "heavy compute usage"
    if "datatransfer" in usage or "bandwidth" in usage:
        return "high network transfer activity"
    if "storage" in usage or "volume" in usage:
        return "increased storage consumption"
    if "request" in usage:
        return "elevated request activity"
    return f"heavy usage under {usage_type}"


def build_report_text(result: dict) -> str:
    feature_summary = ", ".join(result["top_ml_features"])
    return (
        f"A significant cost spike was detected on {result['anomaly_date']}.\n\n"
        f"The total cost increased by approximately {result['increase_pct']:.0f}% compared to the previous day.\n\n"
        f"The anomaly was primarily caused by increased {result['top_service']} usage in the {result['top_region']} region.\n\n"
        f"{result['top_service_share_pct']:.0f}% of the total cost was attributed to {result['top_service']} services.\n\n"
        f"The main contributing resource was {result['top_resource']}, indicating {_usage_hint(result['top_usage_type'])}.\n\n"
        f"The {result['ml_model']} model flagged this day as anomalous, and {result['explanation_method']} showed the strongest feature impacts from {feature_summary}."
    )


def build_report_dataframe(result: dict) -> pd.DataFrame:
    rows = [
        {"metric": "Anomaly Date", "value": result["anomaly_date"]},
        {"metric": "Anomaly Cost", "value": result["anomaly_cost"]},
        {"metric": "Previous Day Cost", "value": result["previous_day_cost"]},
        {"metric": "Increase Percentage", "value": result["increase_pct"]},
        {"metric": "Anomaly Score", "value": result["anomaly_score"]},
        {"metric": "ML Model", "value": result["ml_model"]},
        {"metric": "Explanation Method", "value": result["explanation_method"]},
        {"metric": "Top Service", "value": result["top_service"]},
        {"metric": "Top Region", "value": result["top_region"]},
        {"metric": "Top Resource", "value": result["top_resource"]},
        {"metric": "Top Usage Type", "value": result["top_usage_type"]},
        {"metric": "Top Service Share Percentage", "value": result["top_service_share_pct"]},
        {"metric": "Top ML Features", "value": ", ".join(result["top_ml_features"])},
    ]

    for contribution in result["feature_contributions"][:5]:
        rows.append(
            {
                "metric": f"Feature Contribution: {contribution['feature']}",
                "value": f"value={contribution['feature_value']}, shap={contribution['shap_value']}",
            }
        )

    for service in result.get("service_comparison", []):
        rows.append(
            {
                "metric": f"Service Comparison: {service['service_name']}",
                "value": (
                    f"anomaly={service['anomaly_value']}, "
                    f"normal={service['normal_value']}, "
                    f"percentage={service['percentage']}"
                ),
            }
        )

    return pd.DataFrame(rows)
