# CARCI

CARCI (Cost Anomaly Root Cause Intelligence) is a lightweight Streamlit application for:

- uploading AWS CUR-style CSV files,
- validating core billing columns,
- detecting unusual daily cost spikes,
- analyzing the main service, region, resource, and usage-type contributors,
- generating a structured plain-language explanation.

## Run locally

1. Install dependencies:

```powershell
pip install -r requirements.txt
```

2. Start the app:

```powershell
streamlit run app.py
```

## Expected logical columns

The app tries to match common AWS CUR column names to these logical fields:

- `date`
- `service`
- `region`
- `resource`
- `usage_type`
- `cost`

It also accepts common CUR-style aliases such as `line_item_usage_start_date`, `line_item_resource_id`, and `line_item_unblended_cost`.

## Output style

The explanation is designed to produce study-friendly text such as:

> A significant cost spike was detected on 15 April 2026.
>
> The total cost increased by approximately 210% compared to the previous day.
>
> The anomaly was primarily caused by increased Amazon EC2 usage in the ap-south-1 region.
>
> 78% of the total cost was attributed to EC2 services.
>
> The main contributing resource was instance i-0x9345, indicating heavy compute usage.
