import pandas as pd
import streamlit as st

from carci.analysis import build_analysis_result


st.set_page_config(
    page_title="Service Anomaly Table",
    page_icon="C",
    layout="wide",
)


def load_uploaded_csv(uploaded_file) -> pd.DataFrame:
    return pd.read_csv(uploaded_file, skipinitialspace=True)


def main() -> None:
    st.title("Service Anomaly Table")
    st.caption("Upload an AWS CUR CSV to view row-level anomaly value, normal value, percentage, date, and impact for every service.")

    uploaded_file = st.file_uploader("Upload AWS CUR CSV", type=["csv"])

    if not uploaded_file:
        st.info("Upload a CSV file to start the analysis.")
        return

    try:
        raw_df = load_uploaded_csv(uploaded_file)
        result = build_analysis_result(raw_df)
    except Exception as exc:
        st.error(f"Unable to analyze the uploaded file: {exc}")
        return

    service_table = pd.DataFrame(result["service_comparison"]).rename(
        columns={
            "service_name": "Service Name",
            "date": "Date",
            "anomaly_value": "Anomaly Value",
            "normal_value": "Normal Value",
            "percentage": "Percentage",
            "impact_value": "Impact Value",
        }
    )
    st.dataframe(service_table, use_container_width=True)

    st.subheader("Root Cause Analysis")
    for service_root_cause in result["service_root_causes"]:
        st.markdown(f"**{service_root_cause['service_name']}**")
        st.markdown(service_root_cause["root_cause_analysis"])


if __name__ == "__main__":
    main()
