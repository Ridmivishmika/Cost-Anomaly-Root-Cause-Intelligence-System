from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional

import pandas as pd


@dataclass(frozen=True)
class NormalizedColumns:
    date: str
    service: str
    region: Optional[str]
    resource: Optional[str]
    usage_type: Optional[str]
    cost: str


COLUMN_ALIASES: Dict[str, Iterable[str]] = {
    "date": [
        "date",
        "usage_date",
        "usage start date",
        "billing period start date",
        "bill_billing_period_start_date",
        "bill_billingperiodstartdate",
        "identity_time_interval",
        "identity_timeinterval",
        "line_item_usage_start_date",
        "line_item_usage_end_date",
        "lineitemusagestartdate",
        "lineitemusageenddate",
        "usage_start_date",
        "time_interval",
    ],
    "service": [
        "service",
        "servicecode",
        "product_service_code",
        "product_servicecode",
        "product_product_name",
        "product_productname",
        "line_item_product_code",
        "lineitemproductcode",
    ],
    "region": [
        "region",
        "product_region_code",
        "product_region",
        "product_location",
        "availability_zone",
        "line_item_availability_zone",
    ],
    "resource": [
        "resource",
        "resource_id",
        "line_item_resource_id",
        "lineitemresourceid",
    ],
    "usage_type": [
        "usage_type",
        "line_item_usage_type",
        "lineitemusagetype",
        "usagetype",
    ],
    "cost": [
        "cost",
        "amount",
        "net_unblended_cost",
        "pricing_public_on_demand_cost",
        "line_item_unblended_cost",
        "line_item_blended_cost",
        "line_item_net_unblended_cost",
        "lineitemunblendedcost",
        "lineitemblendedcost",
        "lineitemnetunblendedcost",
        "unblended_cost",
    ],
}


def _normalize_name(name: str) -> str:
    return "".join(ch.lower() for ch in str(name).strip() if ch.isalnum() or ch == "_")


def _fallback_match(normalized_map: Dict[str, str], logical_name: str) -> Optional[str]:
    candidates = list(normalized_map.items())

    token_map = {
        "date": ("date", "timeinterval", "time_interval", "usagestart", "billingperiodstart"),
        "cost": ("cost", "unblended", "blended", "amount", "ondemand"),
        "service": ("service", "productcode", "productname"),
        "region": ("region", "location", "availabilityzone"),
        "resource": ("resource", "instance", "arn"),
        "usage_type": ("usagetype", "operation", "lineitemtype"),
    }

    for normalized, original in candidates:
        if any(token in normalized for token in token_map[logical_name]):
            return original

    return None


def detect_columns(df: pd.DataFrame) -> NormalizedColumns:
    normalized_map = {_normalize_name(col): col for col in df.columns}

    def find_column(logical_name: str, required: bool = True) -> Optional[str]:
        for alias in COLUMN_ALIASES[logical_name]:
            matched = normalized_map.get(_normalize_name(alias))
            if matched:
                return matched

        fallback = _fallback_match(normalized_map, logical_name)
        if fallback:
            return fallback

        if required:
            available_columns = ", ".join(str(col) for col in df.columns)
            raise ValueError(
                f"Required column for '{logical_name}' was not found in the uploaded CSV. "
                f"Available columns: {available_columns}"
            )
        return None

    return NormalizedColumns(
        date=find_column("date"),
        service=find_column("service"),
        region=find_column("region", required=False),
        resource=find_column("resource", required=False),
        usage_type=find_column("usage_type", required=False),
        cost=find_column("cost"),
    )
